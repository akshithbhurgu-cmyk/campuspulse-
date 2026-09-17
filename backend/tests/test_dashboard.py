import asyncio
import json
import os
import unittest
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.db.models import (
    AcademicCalendarEvent, Assessment, Assignment, AvailabilityBlock, ChangeHistory,
    Course, PersonalEvent, Semester, Student, StudyPlan, StudyProgress, StudySession,
)
from app.db.models.enums import (
    AvailabilityBlockType, CalendarEventType, StudyPlanStatus, StudySessionStatus,
)
from app.engines.planner import Planner, StudyTask
from app.engines.time_blocks import TimeBlock
from app.main import app
from app.schemas.dashboard import DashboardOut
from app.seed import seed_synthetic_semester
from app.services.dashboard import dashboard_service

NOW = datetime(2026, 9, 16, 0, tzinfo=UTC)
ZONE = ZoneInfo("Asia/Kolkata")


async def request(path, query=b""):
    """Exercise the ASGI application without an optional HTTP-client dependency."""
    sent = []
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    async def send(message):
        sent.append(message)
    await app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": query, "root_path": "", "headers": [],
        "client": ("127.0.0.1", 1), "server": ("test", 80),
    }, receive, send)
    status = next(item["status"] for item in sent if item["type"] == "http.response.start")
    body = b"".join(item.get("body", b"") for item in sent if item["type"] == "http.response.body")
    return status, json.loads(body)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        with patch("app.seed.date") as seed_date:
            seed_date.today.return_value = date(2026, 9, 16)
            seed_synthetic_semester(self.db)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def dashboard(self, student_id=1, now=NOW):
        result = dashboard_service.get_dashboard(self.db, student_id, now=now)
        DashboardOut.model_validate(result)
        return result

    def test_seeded_contract_and_read_only(self):
        counts = lambda: {
            name: self.db.scalar(select(func.count()).select_from(table))
            for name, table in Base.metadata.tables.items()
        }
        before = counts()
        result = self.dashboard()
        self.assertEqual(result["next_class"]["course_name"], "Full Stack Development using Java")
        self.assertEqual(result["plan_source"], "preview")
        self.assertTrue(result["today_plan"])
        self.assertEqual(len(result["top_priorities"]), 5)
        fos = self.db.scalar(select(Course.id).where(Course.code == "FOS"))
        self.assertTrue(any(r["risk_type"] == "ATTENDANCE" and r["course_id"] == fos
                            for r in result["risks"]))
        self.assertEqual(counts(), before)
        self.assertFalse(self.db.new)
        self.assertFalse(self.db.dirty)
        self.assertEqual(self.dashboard(), result)

    def test_exact_assessment_topic_readiness(self):
        slip = self.db.scalar(select(Assessment).where(
            Assessment.title == "CNN Architecture Slip Test"
        ))
        item = next(p for p in self.dashboard()["top_priorities"]
                    if p["task_key"] == f"assessment:{slip.id}")
        self.assertEqual(item["preparation_percentage"], 53.75)
        self.assertEqual(item["required_minutes"], 111)
        for link in slip.topic_links:
            progress = self.db.scalar(select(StudyProgress).where(
                StudyProgress.topic_id == link.topic_id, StudyProgress.student_id == 1
            ))
            progress.completion_percentage = 100
        self.db.commit()
        changed = next(p for p in self.dashboard()["top_priorities"]
                       if p["task_key"] == f"assessment:{slip.id}")
        self.assertEqual(changed["required_minutes"], 0)
        self.assertLess(changed["score"], item["score"])

    def test_saved_locked_plan_and_real_history(self):
        plan = StudyPlan(student_id=1, plan_date=date(2026, 9, 16),
                         status=StudyPlanStatus.ACTIVE)
        plan.sessions.append(StudySession(
            title="Locked revision", starts_at=NOW + timedelta(hours=9),
            ends_at=NOW + timedelta(hours=10), is_locked=True,
            status=StudySessionStatus.PLANNED,
        ))
        self.db.add_all([plan, ChangeHistory(
            student_id=1, entity_type="topic", entity_id="1", action="updated",
            before_state={"percentage": 20}, after_state={"percentage": 50},
            created_at=NOW,
        )])
        self.db.commit()
        result = self.dashboard()
        self.assertEqual(result["plan_source"], "saved")
        self.assertEqual(len(result["today_plan"]), 1)
        self.assertTrue(result["today_plan"][0]["is_locked"])
        self.assertEqual(result["recent_changes"][0]["after_state"], {"percentage": 50})
        self.assertEqual(result["unscheduled_minutes"], {})

    def test_empty_saved_plan_is_not_replaced(self):
        self.db.add(StudyPlan(student_id=1, plan_date=date(2026, 9, 16)))
        self.db.commit()
        result = self.dashboard()
        self.assertEqual(result["plan_source"], "saved")
        self.assertEqual(result["today_plan"], [])

    def test_holiday_suppresses_classes(self):
        semester = self.db.scalar(select(Semester))
        self.db.add(AcademicCalendarEvent(
            semester_id=semester.id, title="Holiday", event_type=CalendarEventType.HOLIDAY,
            starts_at=datetime(2026, 9, 16, 0, tzinfo=ZONE).astimezone(UTC),
            ends_at=datetime(2026, 9, 17, 0, tzinfo=ZONE).astimezone(UTC), is_all_day=True,
        ))
        self.db.commit()
        self.assertEqual(self.dashboard()["next_class"]["starts_at"].date(), date(2026, 9, 17))

    def test_no_availability_does_not_invent_time(self):
        self.db.execute(delete(AvailabilityBlock))
        self.db.commit()
        result = self.dashboard()
        self.assertEqual(result["today_plan"], [])
        self.assertTrue(result["unscheduled_minutes"])
        self.assertTrue(any(r["risk_type"] == "WORKLOAD" and r["score"] == 100
                            for r in result["risks"]))

    def test_overlapping_windows_do_not_double_book(self):
        self.db.add(AvailabilityBlock(
            student_id=1, block_type=AvailabilityBlockType.AVAILABLE,
            block_date=date(2026, 9, 16), start_time=time(21), end_time=time(23),
        ))
        self.db.commit()
        plan = self.dashboard()["today_plan"]
        minutes = sum((s["ends_at"] - s["starts_at"]).total_seconds() / 60 for s in plan)
        self.assertLessEqual(minutes, 120)
        for left, right in zip(plan, plan[1:]):
            self.assertLessEqual(left["ends_at"], right["starts_at"])

    def test_other_student_has_no_leaked_data(self):
        other = Student(full_name="Other", email="other@example.test")
        self.db.add(other)
        self.db.commit()
        result = self.dashboard(other.id)
        self.assertIsNone(result["next_class"])
        for key in ("today_plan", "top_priorities", "risks", "recent_changes"):
            self.assertEqual(result[key], [])

    def test_overdue_assignments_stay_visible_but_are_not_scheduled(self):
        assignment = self.db.scalar(select(Assignment))
        assignment.due_at = NOW - timedelta(hours=1)
        self.db.commit()
        result = self.dashboard()
        key = f"assignment:{assignment.id}"
        item = next(p for p in result["top_priorities"] if p["task_key"] == key)
        self.assertEqual(item["factors"]["deadline_urgency"], 100)
        self.assertFalse(any(s["title"] == assignment.title for s in result["today_plan"]))

    def test_local_midnight_selects_local_plan_date(self):
        self.db.add(StudyPlan(student_id=1, plan_date=date(2026, 9, 17)))
        self.db.commit()
        result = self.dashboard(now=datetime(2026, 9, 16, 20, tzinfo=UTC))
        self.assertEqual(result["generated_at"].date(), date(2026, 9, 17))
        self.assertEqual(result["plan_source"], "saved")

    def test_locked_saved_conflict_is_reported_without_moving(self):
        plan = StudyPlan(student_id=1, plan_date=date(2026, 9, 16))
        plan.sessions.append(StudySession(
            title="Locked study", starts_at=NOW + timedelta(hours=15),
            ends_at=NOW + timedelta(hours=16), is_locked=True,
        ))
        self.db.add_all([plan, PersonalEvent(
            student_id=1, title="Appointment", event_type="PERSONAL",
            starts_at=NOW + timedelta(hours=15), ends_at=NOW + timedelta(hours=16),
        )])
        self.db.commit()
        result = self.dashboard()
        self.assertTrue(any(r["risk_type"] == "CONFLICT" for r in result["risks"]))
        self.assertEqual(result["today_plan"][0]["starts_at"],
                         (NOW + timedelta(hours=15)).astimezone(ZONE))

    def test_completed_and_submitted_work_is_excluded(self):
        for assessment in self.db.scalars(select(Assessment)).all():
            assessment.status = "COMPLETED"
        for assignment in self.db.scalars(select(Assignment)).all():
            assignment.is_submitted = True
        self.db.commit()
        self.assertEqual(self.dashboard()["top_priorities"], [])

    def test_expired_semester_has_no_upcoming_classes(self):
        semester = self.db.scalar(select(Semester))
        semester.ends_on = date(2026, 9, 15)
        self.db.commit()
        self.assertIsNone(self.dashboard()["next_class"])

    def test_personal_commitment_reduces_study_capacity(self):
        self.db.add(PersonalEvent(
            student_id=1, title="Appointment", event_type="PERSONAL",
            starts_at=datetime(2026, 9, 16, 21, tzinfo=ZONE).astimezone(UTC),
            ends_at=datetime(2026, 9, 16, 22, tzinfo=ZONE).astimezone(UTC),
        ))
        self.db.commit()
        result = self.dashboard()
        self.assertLessEqual(sum((s["ends_at"] - s["starts_at"]).total_seconds() / 60
                                 for s in result["today_plan"]), 60)

    def test_http_contract_errors_and_validation(self):
        def override():
            with Session(self.engine) as session:
                yield session
        app.dependency_overrides[get_db] = override
        with patch("app.services.dashboard.datetime") as clock:
            clock.now.return_value = NOW
            clock.combine.side_effect = datetime.combine
            status, data = asyncio.run(request("/dashboard"))
        self.assertEqual(status, 200)
        DashboardOut.model_validate(data)
        status, _ = asyncio.run(request("/dashboard", b"student_id=999"))
        self.assertEqual(status, 404)
        status, _ = asyncio.run(request("/dashboard", b"student_id=0"))
        self.assertEqual(status, 422)


class PlannerCapacityRegressionTests(unittest.TestCase):
    def test_long_single_slot_is_fully_used(self):
        plan = Planner.generate(
            [StudyTask("dl", "DL", 120, 90)],
            [TimeBlock(NOW, NOW + timedelta(hours=2))],
        )
        self.assertEqual(sum(s.duration_minutes for s in plan.sessions), 120)
        self.assertEqual(plan.unresolved_minutes, {})


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from datetime import UTC, date, datetime, time
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.tools import build_read_tools
from app.db.base import Base
from app.db.models import AvailabilityBlock, PersonalEvent, StudyProgress, Topic
from app.seed import seed_synthetic_semester
from app.tools.campuspulse import (
    AssessmentListInput, AssignmentListInput, AvailabilityInput, CampusPulseTools, CourseInput,
    PersonalEventInput, StudentInput, TopicProgressInput,
)


class CampusPulseToolsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        with patch("app.seed.date") as seed_date:
            seed_date.today.return_value = date(2026, 9, 16)
            seed_synthetic_semester(self.db)
        self.db.commit()
        self.tools = CampusPulseTools(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_read_tools_return_seeded_student_scope(self):
        self.assertEqual(len(self.tools.courses(StudentInput())), 9)
        self.assertEqual(self.tools.course(CourseInput(course_id=1))["code"], "DL")
        self.assertEqual(len(self.tools.attendance(StudentInput())), 9)
        self.assertIn("safe_skips", self.tools.attendance_impact(CourseInput(course_id=1)))
        self.assertTrue(self.tools.assessments(AssessmentListInput()))
        self.assertEqual(len(self.tools.assignments(AssignmentListInput(pending_only=True))), 3)
        self.assertIn("academic_events", self.tools.calendar(StudentInput()))
        self.assertEqual(len(self.tools.preparation(StudentInput())), 9)
        self.assertIn("top_priorities", self.tools.dashboard(StudentInput()))

    def test_write_tools_persist_and_validate(self):
        topic = self.db.scalar(select(Topic).where(Topic.id == 1))
        updated = self.tools.update_topic_progress(TopicProgressInput(topic_id=topic.id, completion_percentage=65))
        self.assertEqual(updated["completion_percentage"], 65)
        self.assertEqual(self.db.scalar(select(StudyProgress.completion_percentage).where(StudyProgress.topic_id == topic.id)), 65)
        event = self.tools.create_personal_event(PersonalEventInput(
            title="Tool test", event_type="PERSONAL", starts_at=datetime(2026, 9, 20, 10, tzinfo=UTC),
            ends_at=datetime(2026, 9, 20, 11, tzinfo=UTC),
        ))
        self.assertEqual(event["title"], "Tool test")
        block = self.tools.create_availability(AvailabilityInput(
            block_type="AVAILABLE", block_date=datetime(2026, 9, 20).date(),
            start_time=time(18), end_time=time(19), label="Tool test",
        ))
        self.assertEqual(block["label"], "Tool test")
        self.assertEqual(self.db.scalar(select(PersonalEvent).where(PersonalEvent.title == "Tool test")).title, "Tool test")
        self.assertEqual(self.db.scalar(select(AvailabilityBlock).where(AvailabilityBlock.label == "Tool test")).label, "Tool test")
        with self.assertRaises(ValueError):
            TopicProgressInput(topic_id=1, completion_percentage=101)
        with self.assertRaises(ValueError):
            AvailabilityInput(block_type="AVAILABLE", start_time=time(19), end_time=time(18))

    def test_invalid_course_is_not_invented(self):
        with self.assertRaises(LookupError):
            self.tools.course(CourseInput(course_id=999))
        with self.assertRaises(LookupError):
            self.tools.attendance_impact(CourseInput(course_id=999))

    def test_phase_ten_exposes_only_read_tools(self):
        names = {item.name for item in build_read_tools(self.tools, student_id=1)}
        self.assertEqual(names, {
            "get_courses", "get_course_detail", "get_attendance", "get_attendance_impact",
            "get_upcoming_assessments", "get_pending_assignments", "get_calendar",
            "get_preparation", "get_dashboard",
        })

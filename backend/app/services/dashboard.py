"""Read-only aggregation of academic state and deterministic engine output."""
from dataclasses import asdict
from datetime import UTC, datetime, time, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Assessment, AssessmentTopic, ChangeHistory, Course, Semester, StudyPlan
from app.engines.conflict import ConflictEngine
from app.engines.planner import Planner, StudyTask
from app.engines.priority import PriorityEngine, PriorityFactors
from app.engines.risk import RiskEngine, RiskInputs
from app.engines.time_blocks import TimeBlock
from app.services.assessments import assessment_service
from app.services.attendance import attendance_service
from app.services.common import require_student
from app.services.courses import course_service
from app.services.scheduling import aware, scheduling_service


class DashboardService:
    def get_dashboard(
        self, session: Session, student_id: int, *, now: datetime | None = None,
        timezone: str = "Asia/Kolkata",
    ) -> dict:
        require_student(session, student_id)
        zone = ZoneInfo(timezone)
        now = aware(now or datetime.now(UTC), zone)
        tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min, zone)
        horizon = now + timedelta(days=14)
        schedule = scheduling_service.build(session, student_id, now, horizon, zone)
        preparation = course_service.get_preparation(session, student_id)
        attendance = {
            row["course_id"]: row
            for row in attendance_service.list_attendance(session, student_id)
        }
        assessments = assessment_service.list_assessments(session, student_id)
        assignments = assessment_service.list_assignments(session, student_id, pending_only=True)
        coverage = session.scalars(
            select(Assessment).join(Course).join(Semester)
            .where(Semester.student_id == student_id)
            .options(selectinload(Assessment.topic_links).selectinload(AssessmentTopic.topic))
        ).all()
        linked_topics = {
            item.id: [link.topic for link in item.topic_links] for item in coverage
        }
        topic_progress = {
            topic["id"]: topic["completion_percentage"]
            for course in preparation for unit in course["units"] for topic in unit["topics"]
        }
        course_preparation = {
            course["course_id"]: (
                course["completion_percentage"]
                if any(unit["topics"] for unit in course["units"]) else None
            )
            for course in preparation
        }
        performance = {}
        for course_id in course_preparation:
            marked = [
                item for item in assessments
                if item["course_id"] == course_id and item["status"] == "COMPLETED"
                and item["earned_marks"] is not None and item["maximum_marks"]
            ]
            performance[course_id] = (
                sum(item["earned_marks"] for item in marked) * 100
                / sum(item["maximum_marks"] for item in marked) if marked else None
            )

        risks = []
        for course_id, row in attendance.items():
            score = RiskEngine.attendance_risk(
                row["attendance_percentage"], row["target_percentage"]
            )
            if score >= 45:
                risks.append(self._risk(
                    "ATTENDANCE", score,
                    f'{row["course_name"]}: {row["attendance_percentage"]}% attendance; '
                    f'target {row["target_percentage"]}%.', course_id,
                ))

        priorities, tasks = [], []
        candidates = [
            ("assessment", item, item["scheduled_at"])
            for item in assessments if item["status"] == "PLANNED"
        ] + [("assignment", item, item["due_at"]) for item in assignments]
        for kind, item, raw_deadline in candidates:
            deadline = aware(raw_deadline, zone) if raw_deadline else None
            if deadline and deadline > horizon:
                continue
            course_id = item["course_id"]
            prep = course_preparation.get(course_id)
            topics = linked_topics.get(item["id"], []) if kind == "assessment" else []
            if topics:
                prep = sum(topic_progress.get(topic.id, 0) for topic in topics) / len(topics)
                required = ceil(sum(
                    (topic.estimated_minutes or 60) * (1 - topic_progress.get(topic.id, 0) / 100)
                    for topic in topics
                ))
                estimate_source = "topic estimates; 60-minute fallback per topic"
            elif kind == "assignment":
                required, estimate_source = 120, "120-minute assignment fallback"
            else:
                required = ceil(240 * (1 - prep / 100)) if prep is not None else 240
                estimate_source = "240-minute assessment fallback scaled by preparation"
            row = attendance.get(course_id)
            available = sum(
                max(0, int((min(slot.ends_at, deadline or horizon) - slot.starts_at)
                           .total_seconds() // 60))
                for slot in schedule.free_slots if slot.starts_at < (deadline or horizon)
            )
            scores = RiskEngine.calculate(RiskInputs(
                now=now, deadline_at=deadline,
                preparation_percentage=prep if prep is not None else 100,
                performance_percentage=performance.get(course_id)
                if performance.get(course_id) is not None else 100,
                attendance_percentage=row["attendance_percentage"] if row else 100,
                attendance_target=row["target_percentage"] if row else 75,
                required_minutes=required, available_minutes=available,
            ))
            # Weightage is a percentage of the grade, used directly as importance.
            importance = item.get("weightage") if kind == "assessment" else None
            importance = float(importance) if importance is not None else 50.0
            factors = PriorityFactors(
                scores.deadline, importance, scores.preparation, scores.performance,
                scores.attendance, scores.workload, scores.conflict,
            )
            priority = PriorityEngine.calculate(factors)
            key = f'{kind}:{item["id"]}'
            priorities.append({
                "task_key": key, "entity_type": kind, "entity_id": item["id"],
                "course_id": course_id, "title": item["title"], "deadline_at": deadline,
                "score": priority.score, "level": priority.level,
                "preparation_percentage": round(prep, 2) if prep is not None else None,
                "required_minutes": required, "estimate_source": estimate_source,
                "factors": asdict(factors),
            })
            for risk_type, score in asdict(scores).items():
                if risk_type == "attendance" or score < 45:
                    continue
                summary = (
                    f'{item["title"]}: overall academic risk {score}%.'
                    if risk_type == "overall"
                    else f'{item["title"]}: {risk_type} risk {score}%.'
                )
                risks.append(self._risk(
                    risk_type.upper(), score, summary,
                    course_id, key,
                ))
            if required > 0 and (deadline is None or deadline > now):
                tasks.append(StudyTask(key, item["title"], required, priority.score,
                                       deadline, course_id))

        saved = [
            item for item in schedule.stored_sessions
            if item.study_plan.plan_date == now.date()
        ]
        saved_plan = session.scalar(select(StudyPlan).where(
            StudyPlan.student_id == student_id, StudyPlan.plan_date == now.date(),
            StudyPlan.status != "ARCHIVED",
        ))
        plan_source = "saved" if saved_plan is not None else "preview"
        unresolved = {}
        if plan_source == "saved":
            today_plan = [{
                "id": item.id, "title": item.title, "course_id": item.course_id,
                "topic_id": item.topic_id, "starts_at": aware(item.starts_at, zone),
                "ends_at": aware(item.ends_at, zone), "status": item.status.value,
                "is_locked": item.is_locked, "source": "saved", "management_kind": "study_session",
            } for item in saved]
            for item in saved:
                if item.status.value != "PLANNED":
                    continue
                conflicts = ConflictEngine.find_conflicts(
                    TimeBlock(aware(item.starts_at, zone), aware(item.ends_at, zone), item.title),
                    schedule.busy,
                )
                if conflicts:
                    risks.append(self._risk(
                        "CONFLICT", min(100, len(conflicts) * 50),
                        f'{item.title} conflicts with an existing commitment.', item.course_id,
                    ))
        else:
            today_slots = [
                TimeBlock(slot.starts_at, min(slot.ends_at, tomorrow))
                for slot in schedule.free_slots if slot.starts_at < tomorrow
            ]
            plan = Planner.generate(tasks, today_slots)
            unresolved = plan.unresolved_minutes
            today_plan = [{
                "title": item.title, "course_id": item.course_id, "topic_id": item.topic_id,
                "starts_at": item.starts_at, "ends_at": item.ends_at,
                "status": "PLANNED", "source": "preview", "management_kind": "preview",
            } for item in plan.sessions]
        locked_today = [
            {
                "id": item.source_id, "title": item.label or "Locked study block",
                "course_id": None, "topic_id": None,
                "starts_at": item.starts_at, "ends_at": item.ends_at,
                "status": "LOCKED", "is_locked": True, "source": "preview",
                "management_kind": "availability_block",
            }
            for item in schedule.locked_blocks
            if item.starts_at.date() == now.date()
        ]
        changes = session.scalars(
            select(ChangeHistory).where(ChangeHistory.student_id == student_id)
            .order_by(ChangeHistory.created_at.desc(), ChangeHistory.id.desc()).limit(10)
        ).all()
        return {
            "student_id": student_id, "generated_at": now, "timezone": timezone,
            "next_class": schedule.classes[0] if schedule.classes else None,
            "today_plan": sorted([*today_plan, *locked_today], key=lambda item: item["starts_at"]),
            "plan_source": plan_source,
            "top_priorities": sorted(priorities, key=lambda item: (-item["score"], item["task_key"]))[:5],
            "risks": sorted(risks, key=lambda item: (-item["score"], item["summary"]))[:15],
            "recent_changes": [{
                "id": item.id, "entity_type": item.entity_type, "entity_id": item.entity_id,
                "action": item.action, "before_state": item.before_state,
                "after_state": item.after_state, "created_at": aware(item.created_at, zone),
            } for item in changes],
            "unscheduled_minutes": unresolved,
        }

    @staticmethod
    def _risk(kind, score, summary, course_id=None, task_key=None):
        level = "CRITICAL" if score >= 85 else "HIGH" if score >= 70 else "MEDIUM"
        return {"risk_type": kind, "score": score, "severity": level, "summary": summary,
                "course_id": course_id, "task_key": task_key}


dashboard_service = DashboardService()

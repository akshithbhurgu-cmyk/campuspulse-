from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.db.models import StudyPlan, StudySession
from app.db.models import ChangeHistory
from app.db.models.enums import StudyPlanStatus, StudySessionStatus
from app.engines.planner import PlannedStudySession
from app.engines.replanner import Replanner
from app.engines.time_blocks import TimeBlock
from app.services.scheduling import scheduling_service, aware

class ReplanningService:
    def preview(self, session: Session, student_id: int, starts_at: datetime, ends_at: datetime, *, timezone: str) -> dict:
        zone = ZoneInfo(timezone)
        start, end = aware(starts_at, zone), aware(ends_at, zone)
        saved = session.scalars(select(StudySession).join(StudyPlan).where(StudyPlan.student_id == student_id, StudyPlan.status != StudyPlanStatus.ARCHIVED, StudySession.status == StudySessionStatus.PLANNED).options(selectinload(StudySession.study_plan))).all()
        existing = [PlannedStudySession(str(x.id), x.title, aware(x.starts_at, zone), aware(x.ends_at, zone), 0, None, x.course_id, x.topic_id, x.is_locked) for x in saved]
        context = scheduling_service.build(session, student_id, start, max(end, start + timedelta(days=1)), zone)
        result = Replanner.replan(existing, [TimeBlock(start, end, "Approved academic change")], context.free_slots)
        return {"kept_session_ids": [int(x.task_key) for x in result.kept], "rescheduled": [{"session_id": int(x.task_key), "starts_at": x.starts_at, "ends_at": x.ends_at} for x in result.rescheduled], "locked_conflict_ids": [int(x.task_key) for x in result.locked_conflicts], "unresolved_session_ids": [int(x) for x in result.unresolved_task_keys]}
    def confirm(self, session: Session, student_id: int, changes: list[dict]) -> dict:
        moved = 0
        for change in changes:
            item = session.scalar(select(StudySession).join(StudyPlan).where(StudySession.id == change["session_id"], StudyPlan.student_id == student_id))
            if item is None: raise LookupError("Study session was not found.")
            if item.is_locked: raise ValueError("Locked sessions cannot be moved.")
            before = {"starts_at": item.starts_at.isoformat(), "ends_at": item.ends_at.isoformat()}
            item.starts_at, item.ends_at = change["starts_at"], change["ends_at"]
            session.add(ChangeHistory(student_id=student_id, entity_type="STUDY_SESSION", entity_id=str(item.id), action="SESSION_RESCHEDULED", before_state=before, after_state={"starts_at": item.starts_at.isoformat(), "ends_at": item.ends_at.isoformat()})); moved += 1
        session.commit(); return {"moved_sessions": moved}
replanning_service = ReplanningService()

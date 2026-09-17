from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.db.models import ChangeHistory, StudyPlan, StudySession
from app.db.models.enums import StudyPlanStatus
from app.services.dashboard import dashboard_service

class PlanService:
    def save_today_preview(self, session: Session, student_id: int, *, timezone: str) -> dict:
        snapshot = dashboard_service.get_dashboard(session, student_id, timezone=timezone)
        if snapshot["plan_source"] == "saved": raise ValueError("Today's plan is already saved.")
        date = datetime.now(UTC).astimezone(ZoneInfo(timezone)).date()
        plan = StudyPlan(student_id=student_id, plan_date=date, status=StudyPlanStatus.ACTIVE)
        for item in snapshot["today_plan"]:
            plan.sessions.append(StudySession(title=item["title"], starts_at=item["starts_at"], ends_at=item["ends_at"], is_locked=False))
        session.add(plan); session.flush()
        session.add(ChangeHistory(student_id=student_id, entity_type="STUDY_PLAN", entity_id=str(plan.id), action="PLAN_SAVED", before_state=None, after_state={"session_count": len(plan.sessions)}))
        session.commit()
        return {"plan_id": plan.id, "session_count": len(plan.sessions)}
    def set_lock(self, session: Session, student_id: int, session_id: int, locked: bool) -> dict:
        item = session.query(StudySession).join(StudyPlan).filter(StudySession.id == session_id, StudyPlan.student_id == student_id).one_or_none()
        if item is None: raise LookupError("Study session was not found.")
        item.is_locked = locked
        session.add(ChangeHistory(student_id=student_id, entity_type="STUDY_SESSION", entity_id=str(item.id), action="SESSION_LOCKED" if locked else "SESSION_UNLOCKED", before_state=None, after_state={"is_locked": locked}))
        session.commit()
        return {"id": item.id, "is_locked": item.is_locked}
plan_service = PlanService()

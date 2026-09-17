from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
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

    def update_session(
        self, session: Session, student_id: int, session_id: int, *, title: str,
        starts_at: datetime, ends_at: datetime, timezone: str,
    ) -> dict:
        if ends_at <= starts_at:
            raise ValueError("The session end must be after its start.")
        item = session.query(StudySession).join(StudyPlan).filter(
            StudySession.id == session_id, StudyPlan.student_id == student_id,
            StudyPlan.status != StudyPlanStatus.ARCHIVED,
        ).one_or_none()
        if item is None:
            raise LookupError("Study session was not found.")
        zone = ZoneInfo(timezone)
        start_local = (starts_at if starts_at.tzinfo else starts_at.replace(tzinfo=zone)).astimezone(zone)
        end_local = (ends_at if ends_at.tzinfo else ends_at.replace(tzinfo=zone)).astimezone(zone)
        if start_local.date() != item.study_plan.plan_date or end_local.date() != item.study_plan.plan_date:
            raise ValueError("A today-plan session must stay on its plan date.")
        siblings = session.scalars(
            select(StudySession).where(
                StudySession.study_plan_id == item.study_plan_id,
                StudySession.id != item.id,
            )
        ).all()
        def local(value: datetime) -> datetime:
            return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(zone)
        if any(start_local < local(sibling.ends_at) and end_local > local(sibling.starts_at) for sibling in siblings):
            raise ValueError("This edit overlaps another study session.")
        before = {"title": item.title, "starts_at": item.starts_at.isoformat(), "ends_at": item.ends_at.isoformat()}
        item.title, item.starts_at, item.ends_at = title.strip(), starts_at, ends_at
        session.add(ChangeHistory(
            student_id=student_id, entity_type="STUDY_SESSION", entity_id=str(item.id),
            action="SESSION_EDITED", before_state=before,
            after_state={"title": item.title, "starts_at": item.starts_at.isoformat(), "ends_at": item.ends_at.isoformat()},
        ))
        session.commit()
        return {"id": item.id, "title": item.title, "starts_at": item.starts_at, "ends_at": item.ends_at}
plan_service = PlanService()

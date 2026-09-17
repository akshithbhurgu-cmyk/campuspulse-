"""Student-facing explanation layer over immutable change-history records."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChangeHistory
from app.services.common import require_student


class ChangeService:
    _labels = {
        "INGESTION_APPLIED": ("New academic update applied", "You reviewed and approved an imported academic message."),
        "PLAN_SAVED": ("Study plan saved", "You chose to save the deterministic plan preview."),
        "SESSION_LOCKED": ("Study session locked", "Locked sessions are protected from replanning."),
        "SESSION_UNLOCKED": ("Study session unlocked", "This session can be moved by a confirmed replan."),
        "SESSION_RESCHEDULED": ("Study plan updated", "You confirmed the proposed replanning change."),
    }

    def list(self, session: Session, student_id: int, limit: int = 50) -> list[dict]:
        require_student(session, student_id)
        rows = session.scalars(select(ChangeHistory).where(ChangeHistory.student_id == student_id).order_by(ChangeHistory.created_at.desc(), ChangeHistory.id.desc()).limit(limit)).all()
        return [self.present(row) for row in rows]

    def present(self, row: ChangeHistory) -> dict:
        title, reason = self._labels.get(row.action, (f"{row.entity_type.replace('_', ' ').title()} updated", "CampusPulse recorded a change to your academic workspace."))
        before, after = row.before_state or {}, row.after_state or {}
        changes = [
            {"field": key.replace("_", " ").title(), "before": before.get(key), "after": after.get(key)}
            for key in after if before.get(key) != after.get(key)
        ]
        return {"id": row.id, "title": title, "reason": reason, "entity_type": row.entity_type, "entity_id": row.entity_id, "action": row.action, "changes": changes, "created_at": row.created_at}


change_service = ChangeService()

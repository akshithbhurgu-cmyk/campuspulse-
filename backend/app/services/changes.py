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
        "SESSION_EDITED": ("Study session edited", "You changed a saved study session in today’s plan."),
    }

    def list(self, session: Session, student_id: int, limit: int = 50) -> list[dict]:
        require_student(session, student_id)
        rows = session.scalars(select(ChangeHistory).where(ChangeHistory.student_id == student_id).order_by(ChangeHistory.created_at.desc(), ChangeHistory.id.desc()).limit(limit)).all()
        return [self.present(row) for row in rows]

    def present(self, row: ChangeHistory) -> dict:
        before, after = row.before_state or {}, row.after_state or {}
        title, reason = self._labels.get(row.action, (f"{row.entity_type.replace('_', ' ').title()} updated", "CampusPulse recorded a change to your academic workspace."))
        if row.action == "INGESTION_APPLIED":
            record_type = after.get("created_record_type")
            if record_type:
                label = str(record_type).replace("_", " ").lower()
                article = "an" if label[:1] in "aeiou" else "a"
                title, reason = (f"New {label} added", f"An approved academic notice added {article} {label} to your semester.")
            else:
                title, reason = ("Academic announcement saved", "You approved an academic notice; it did not create a dated task or event.")
        elif row.action == "PLAN_SAVED":
            count = after.get("session_count")
            if isinstance(count, int):
                reason = f"Created today’s study plan with {count} session{'s' if count != 1 else ''}."
        changes = [
            {"field": key.replace("_", " ").title(), "before": before.get(key), "after": after.get(key)}
            for key in after
            if before.get(key) != after.get(key) and not key.endswith("_id")
        ]
        return {"id": row.id, "title": title, "reason": reason, "entity_type": row.entity_type, "entity_id": row.entity_id, "action": row.action, "changes": changes, "created_at": row.created_at}


change_service = ChangeService()

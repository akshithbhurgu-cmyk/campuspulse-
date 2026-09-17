"""Review-first ingestion. Source text never mutates academic state before Apply."""
from datetime import UTC, datetime, timedelta
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AcademicCalendarEvent, Announcement, Assessment, Assignment, ChangeHistory, Course, IngestionItem, Semester
from app.db.models.enums import AnnouncementSource, AssessmentStatus, AssessmentType, CalendarEventType
from app.ingestion.extractor import AcademicExtraction, Extractor
from app.services.common import require_student


class IngestionService:
    def _course(self, session: Session, student_id: int, text: str) -> Course | None:
        courses = session.scalars(select(Course).join(Semester).where(Semester.student_id == student_id)).all()
        haystack = text.casefold()
        compact_haystack = re.sub(r"[^a-z0-9]", "", haystack)
        return next(
            (
                course for course in courses
                if re.search(r"(?<![a-z0-9])" + re.escape(course.code.casefold()) + r"(?![a-z0-9])", haystack)
                or course.name.casefold() in haystack
                or re.sub(r"[^a-z0-9]", "", course.name.casefold()) in compact_haystack
            ),
            None,
        )

    def preview_text(
        self, session: Session, student_id: int, text: str, extractor: Extractor,
        *, source: str = "PASTE", filename: str | None = None, external_id: str | None = None,
    ) -> IngestionItem:
        require_student(session, student_id)
        if external_id:
            existing = session.scalar(select(IngestionItem).where(IngestionItem.external_id == external_id))
            if existing is not None:
                return existing
        normalized = re.sub(r"\s+", " ", text).strip()
        # Pre-external-id Gmail previews can be adopted by their unchanged body.
        # This preserves their review state while preventing a one-time duplicate.
        if external_id:
            legacy = session.scalar(
                select(IngestionItem)
                .where(
                    IngestionItem.student_id == student_id,
                    IngestionItem.source == source,
                    IngestionItem.raw_text == text,
                )
                .order_by(IngestionItem.id)
            )
            if legacy is not None:
                legacy.external_id = external_id
                session.commit()
                session.refresh(legacy)
                return legacy
        extraction = extractor.extract(normalized)
        course = self._course(session, student_id, f"{extraction.course_name or ''} {normalized}")
        item = IngestionItem(
            student_id=student_id, course_id=course.id if course else None, source=source, filename=filename, external_id=external_id,
            raw_text=text, normalized_text=normalized,
            extraction={**extraction.model_dump(mode="json"), "course_match": course.code if course else None, "requires_review": True},
            status="PREVIEW",
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    def get(self, session: Session, student_id: int, item_id: int) -> IngestionItem:
        item = session.scalar(select(IngestionItem).where(IngestionItem.id == item_id, IngestionItem.student_id == student_id))
        if item is None:
            raise LookupError(f"Ingestion item {item_id} was not found.")
        return item

    def ignore(self, session: Session, student_id: int, item_id: int) -> IngestionItem:
        item = self.get(session, student_id, item_id)
        if item.status != "PREVIEW":
            raise ValueError("Only a preview item can be ignored.")
        item.status, item.processed_at = "IGNORED", datetime.now(UTC)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def _scheduled_at(extraction: dict | None) -> datetime | None:
        value = (extraction or {}).get("scheduled_at")
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None

    def apply(self, session: Session, student_id: int, item_id: int) -> tuple[IngestionItem, Announcement, str | None, int | None]:
        item = self.get(session, student_id, item_id)
        if item.status != "PREVIEW":
            raise ValueError("Only a preview item can be applied.")
        semester = session.scalar(select(Semester).where(Semester.student_id == student_id).order_by(Semester.id.desc()))
        if semester is None:
            raise LookupError("No semester exists for this student.")
        announcement = Announcement(
            semester_id=semester.id, course_id=item.course_id, source=AnnouncementSource.OTHER,
            title=(item.normalized_text[:177] + "...") if len(item.normalized_text) > 180 else item.normalized_text,
            body=item.raw_text, is_processed=True,
        )
        extraction = item.extraction or {}
        event_type = extraction.get("event_type")
        title = extraction.get("title") if isinstance(extraction.get("title"), str) else item.normalized_text[:180]
        scheduled_at = self._scheduled_at(extraction)
        created: Assessment | Assignment | AcademicCalendarEvent | None = None
        created_type: str | None = None

        # Structured records require the fields that make them unambiguous.
        if event_type == "ASSESSMENT" and item.course_id and scheduled_at:
            created = Assessment(
                course_id=item.course_id, title=title, assessment_type=AssessmentType.SLIP_TEST,
                status=AssessmentStatus.PLANNED, scheduled_at=scheduled_at,
                notes=f"Approved from ingestion item {item.id}: {extraction.get('summary') or item.normalized_text}",
            )
            created_type = "ASSESSMENT"
        elif event_type == "ASSIGNMENT" and item.course_id and scheduled_at:
            created = Assignment(
                course_id=item.course_id, title=title, due_at=scheduled_at,
                description=f"Approved from ingestion item {item.id}: {extraction.get('summary') or item.normalized_text}",
            )
            created_type = "ASSIGNMENT"
        elif event_type in {"DEADLINE", "HOLIDAY", "EVENT"} and scheduled_at:
            calendar_type = CalendarEventType.DEADLINE if event_type == "DEADLINE" else (CalendarEventType.HOLIDAY if event_type == "HOLIDAY" else CalendarEventType.EVENT)
            created = AcademicCalendarEvent(
                semester_id=semester.id, title=title, event_type=calendar_type,
                starts_at=scheduled_at, ends_at=scheduled_at + timedelta(days=1), is_all_day=True,
                description=f"Approved from ingestion item {item.id}: {extraction.get('summary') or item.normalized_text}",
            )
            created_type = "ACADEMIC_CALENDAR_EVENT"
        item.status, item.processed_at = "APPLIED", datetime.now(UTC)
        session.add(announcement)
        if created is not None:
            session.add(created)
        session.commit()
        session.refresh(item)
        session.refresh(announcement)
        created_id = created.id if created is not None else None
        session.add(ChangeHistory(
            student_id=student_id, entity_type=created_type or "ANNOUNCEMENT",
            entity_id=str(created_id or announcement.id), action="INGESTION_APPLIED",
            before_state=None,
            after_state={"ingestion_item_id": item.id, "announcement_id": announcement.id, "created_record_type": created_type, "created_record_id": created_id},
        ))
        session.commit()
        return item, announcement, created_type, created_id


ingestion_service = IngestionService()

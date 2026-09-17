"""Review-first ingestion. Source text never mutates academic state before Apply."""
from datetime import UTC, datetime
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Announcement, Course, IngestionItem, Semester
from app.db.models.enums import AnnouncementSource
from app.ingestion.extractor import AcademicExtraction, Extractor
from app.services.common import require_student


class IngestionService:
    def _course(self, session: Session, student_id: int, text: str) -> Course | None:
        courses = session.scalars(select(Course).join(Semester).where(Semester.student_id == student_id)).all()
        haystack = text.casefold()
        return next((course for course in courses if course.code.casefold() in haystack or course.name.casefold() in haystack), None)

    def preview_text(
        self, session: Session, student_id: int, text: str, extractor: Extractor,
        *, source: str = "PASTE", filename: str | None = None,
    ) -> IngestionItem:
        require_student(session, student_id)
        normalized = re.sub(r"\s+", " ", text).strip()
        extraction = extractor.extract(normalized)
        course = self._course(session, student_id, f"{extraction.course_name or ''} {normalized}")
        item = IngestionItem(
            student_id=student_id, course_id=course.id if course else None, source=source, filename=filename,
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

    def apply(self, session: Session, student_id: int, item_id: int) -> tuple[IngestionItem, Announcement]:
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
        item.status, item.processed_at = "APPLIED", datetime.now(UTC)
        session.add(announcement)
        session.commit()
        session.refresh(item)
        session.refresh(announcement)
        return item, announcement


ingestion_service = IngestionService()

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AcademicCalendarEvent,
    AvailabilityBlock,
    PersonalEvent,
    Semester,
    TimetableEntry,
)
from app.schemas.academic import AvailabilityBlockCreate, PersonalEventCreate
from app.services.common import require_student


class CalendarService:
    def get_calendar(self, session: Session, student_id: int) -> dict:
        require_student(session, student_id)
        semester_ids = select(Semester.id).where(Semester.student_id == student_id)

        academic_events = session.scalars(
            select(AcademicCalendarEvent)
            .where(AcademicCalendarEvent.semester_id.in_(semester_ids))
            .order_by(AcademicCalendarEvent.starts_at)
        ).all()
        personal_events = session.scalars(
            select(PersonalEvent)
            .where(PersonalEvent.student_id == student_id)
            .order_by(PersonalEvent.starts_at)
        ).all()
        timetable_entries = session.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.semester_id.in_(semester_ids))
            .options(selectinload(TimetableEntry.course))
            .order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
        ).all()

        return {
            "academic_events": [
                {
                    "id": event.id,
                    "title": event.title,
                    "event_type": event.event_type.value,
                    "starts_at": event.starts_at,
                    "ends_at": event.ends_at,
                    "is_all_day": event.is_all_day,
                    "description": event.description,
                }
                for event in academic_events
            ],
            "personal_events": [
                {
                    "id": event.id,
                    "title": event.title,
                    "event_type": event.event_type.value,
                    "starts_at": event.starts_at,
                    "ends_at": event.ends_at,
                    "notes": event.notes,
                }
                for event in personal_events
            ],
            "timetable_entries": [
                {
                    "id": entry.id,
                    "course_id": entry.course_id,
                    "course_code": entry.course.code if entry.course else None,
                    "course_name": entry.course.name if entry.course else None,
                    "day_of_week": entry.day_of_week,
                    "start_time": entry.start_time,
                    "end_time": entry.end_time,
                    "session_kind": entry.session_kind.value,
                    "location": entry.location,
                }
                for entry in timetable_entries
            ],
        }

    def create_personal_event(
        self, session: Session, student_id: int, payload: PersonalEventCreate
    ) -> dict:
        require_student(session, student_id)
        if payload.ends_at <= payload.starts_at:
            raise ValueError("The event end must be after its start.")
        event = PersonalEvent(student_id=student_id, **payload.model_dump())
        session.add(event)
        session.commit()
        session.refresh(event)
        return {
            "id": event.id,
            "title": event.title,
            "event_type": event.event_type.value,
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
            "notes": event.notes,
        }

    def create_availability_block(
        self, session: Session, student_id: int, payload: AvailabilityBlockCreate
    ) -> AvailabilityBlock:
        require_student(session, student_id)
        if payload.block_date is None and payload.day_of_week is None:
            raise ValueError("Provide either block_date or day_of_week.")
        if payload.end_time <= payload.start_time:
            raise ValueError("The availability block end must be after its start.")
        block = AvailabilityBlock(student_id=student_id, **payload.model_dump())
        session.add(block)
        session.commit()
        session.refresh(block)
        return block


calendar_service = CalendarService()


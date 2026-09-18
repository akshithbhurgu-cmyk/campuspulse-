"""Translate stored calendars into timezone-aware scheduling inputs."""
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AcademicCalendarEvent, AvailabilityBlock, PersonalEvent, Semester,
    StudyPlan, StudySession, TimetableEntry,
)
from app.db.models.enums import (
    AvailabilityBlockType, CalendarEventType, StudyPlanStatus, StudySessionStatus,
)
from app.engines.availability import AvailabilityEngine
from app.engines.time_blocks import TimeBlock


def aware(value: datetime, zone: ZoneInfo) -> datetime:
    # PostgreSQL preserves offsets; SQLite test timestamps are stored as naive UTC.
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(zone)


@dataclass
class ScheduleContext:
    classes: list[dict]
    busy: list[TimeBlock]
    free_slots: list[TimeBlock]
    stored_sessions: list[StudySession]
    locked_blocks: list[TimeBlock]


class SchedulingService:
    def build(
        self, session: Session, student_id: int, start: datetime, end: datetime,
        zone: ZoneInfo,
    ) -> ScheduleContext:
        semester_ids = select(Semester.id).where(Semester.student_id == student_id)
        entries = session.scalars(
            select(TimetableEntry).where(TimetableEntry.semester_id.in_(semester_ids))
            .options(selectinload(TimetableEntry.course), selectinload(TimetableEntry.semester))
        ).all()
        events = session.scalars(
            select(AcademicCalendarEvent).where(
                AcademicCalendarEvent.semester_id.in_(semester_ids)
            )
        ).all()
        personal = session.scalars(
            select(PersonalEvent).where(PersonalEvent.student_id == student_id)
        ).all()
        blocks = session.scalars(
            select(AvailabilityBlock).where(AvailabilityBlock.student_id == student_id)
        ).all()
        stored = session.scalars(
            select(StudySession).join(StudyPlan).where(
                StudyPlan.student_id == student_id,
                StudyPlan.status != StudyPlanStatus.ARCHIVED,
            ).options(selectinload(StudySession.study_plan))
        ).all()
        busy = [
            TimeBlock(aware(event.starts_at, zone), aware(event.ends_at, zone), event.title)
            for event in personal
        ]
        # Timed exams are commitments; instruction spells and holidays are not busy blocks.
        for event in events:
            if event.event_type == CalendarEventType.EXAM and not event.is_all_day:
                busy.append(TimeBlock(
                    aware(event.starts_at, zone), aware(event.ends_at, zone), event.title
                ))
        classes, windows, locked_blocks = [], [], []
        day = start.date()
        while day <= end.date():
            day_start = datetime.combine(day, time.min, zone)
            day_end = datetime.combine(day + timedelta(days=1), time.min, zone)
            for entry in entries:
                semester = entry.semester
                if ((semester.starts_on and day < semester.starts_on)
                        or (semester.ends_on and day > semester.ends_on)):
                    continue
                holiday = any(
                    event.semester_id == entry.semester_id
                    and event.event_type == CalendarEventType.HOLIDAY
                    and aware(event.starts_at, zone) < day_end
                    and aware(event.ends_at, zone) > day_start
                    for event in events
                )
                if holiday or entry.day_of_week != day.weekday():
                    continue
                begins = datetime.combine(day, entry.start_time, zone)
                finishes = datetime.combine(day, entry.end_time, zone)
                busy.append(TimeBlock(begins, finishes, "College class"))
                if start <= begins < end:
                    classes.append({
                        "timetable_entry_id": entry.id,
                        "course_id": entry.course_id,
                        "course_name": entry.course.name if entry.course else None,
                        "starts_at": begins, "ends_at": finishes,
                        "session_kind": entry.session_kind.value, "location": entry.location,
                    })
            for block in blocks:
                matches = (
                    block.block_date == day if block.block_date is not None
                    else block.is_recurring and block.day_of_week == day.weekday()
                )
                if not matches:
                    continue
                begins = datetime.combine(day, block.start_time, zone)
                finishes = datetime.combine(day, block.end_time, zone)
                window = TimeBlock(begins, finishes, block.label or "Availability")
                if block.block_type == AvailabilityBlockType.AVAILABLE:
                    if begins < end and finishes > start:
                        windows.append(TimeBlock(max(start, begins), min(end, finishes)))
                else:
                    busy.append(window)
                    if block.block_type == AvailabilityBlockType.LOCKED:
                        locked_blocks.append(window)
            day += timedelta(days=1)

        # Merge overlapping availability declarations to avoid double-counting capacity.
        merged = []
        for window in sorted(windows, key=lambda item: item.starts_at):
            if merged and window.starts_at <= merged[-1].ends_at:
                previous = merged.pop()
                merged.append(TimeBlock(previous.starts_at, max(previous.ends_at, window.ends_at)))
            else:
                merged.append(window)
        stored_busy = [
            TimeBlock(aware(item.starts_at, zone), aware(item.ends_at, zone), item.title)
            for item in stored if item.status == StudySessionStatus.PLANNED
        ]
        free = [
            slot for window in merged
            for slot in AvailabilityEngine.find_free_slots(
                window.starts_at, window.ends_at, busy + stored_busy
            )
        ]
        return ScheduleContext(
            sorted(classes, key=lambda item: item["starts_at"]), busy, free, list(stored),
            locked_blocks,
        )


scheduling_service = SchedulingService()

"""Phase 9 tools: a thin validated boundary over CampusPulse services.

These functions deliberately have no LLM, HTTP, or agent-framework dependency.
They can later be adapted by an orchestration layer without duplicating business
rules or exposing a database session directly to that layer.
"""
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.schemas.academic import AvailabilityBlockCreate, AvailabilityBlockOut, PersonalEventCreate
from app.services.assessments import assessment_service
from app.services.attendance import attendance_service
from app.services.calendar import calendar_service
from app.services.courses import course_service
from app.services.dashboard import dashboard_service


class StudentInput(BaseModel):
    student_id: int = Field(default=1, ge=1)


class CourseInput(StudentInput):
    course_id: int = Field(ge=1)


class TopicProgressInput(StudentInput):
    topic_id: int = Field(ge=1)
    completion_percentage: float = Field(ge=0, le=100)


class AssessmentListInput(StudentInput):
    upcoming_only: bool = False


class AssignmentListInput(StudentInput):
    pending_only: bool = False


class PersonalEventInput(StudentInput):
    title: str = Field(min_length=1, max_length=180)
    event_type: Literal["FIXED", "PERSONAL", "TRAVEL", "HEALTH", "OTHER"]
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def ordered_times(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("The event end must be after its start.")
        return self


class AvailabilityInput(StudentInput):
    block_type: Literal["AVAILABLE", "UNAVAILABLE", "LOCKED"]
    block_date: date | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time
    end_time: time
    is_recurring: bool = False
    label: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def valid_schedule(self):
        if self.block_date is None and self.day_of_week is None:
            raise ValueError("Provide either block_date or day_of_week.")
        if self.end_time <= self.start_time:
            raise ValueError("The availability block end must be after its start.")
        return self


class CampusPulseTools:
    """The Phase 9 tool catalogue, bound to one request/session scope."""

    def __init__(self, session: Session, *, timezone: str = "Asia/Kolkata"):
        self.session = session
        self.timezone = timezone

    def courses(self, payload: StudentInput) -> list[dict]:
        return course_service.list_courses(self.session, payload.student_id)

    def course(self, payload: CourseInput) -> dict:
        return course_service.get_course(self.session, payload.student_id, payload.course_id)

    def attendance(self, payload: StudentInput) -> list[dict]:
        return attendance_service.list_attendance(self.session, payload.student_id)

    def attendance_impact(self, payload: CourseInput) -> dict:
        return attendance_service.get_impact(self.session, payload.student_id, payload.course_id)

    def assessments(self, payload: AssessmentListInput) -> list[dict]:
        return assessment_service.list_assessments(
            self.session, payload.student_id, upcoming_only=payload.upcoming_only
        )

    def assignments(self, payload: AssignmentListInput) -> list[dict]:
        return assessment_service.list_assignments(
            self.session, payload.student_id, pending_only=payload.pending_only
        )

    def calendar(self, payload: StudentInput) -> dict:
        return calendar_service.get_calendar(self.session, payload.student_id)

    def preparation(self, payload: StudentInput) -> list[dict]:
        return course_service.get_preparation(self.session, payload.student_id)

    def dashboard(self, payload: StudentInput) -> dict:
        return dashboard_service.get_dashboard(
            self.session, payload.student_id, timezone=self.timezone
        )

    def update_topic_progress(self, payload: TopicProgressInput) -> dict:
        return course_service.update_topic_progress(
            self.session, payload.student_id, payload.topic_id, payload.completion_percentage
        )

    def create_personal_event(self, payload: PersonalEventInput) -> dict:
        event = PersonalEventCreate(**payload.model_dump(exclude={"student_id"}))
        return calendar_service.create_personal_event(self.session, payload.student_id, event)

    def create_availability(self, payload: AvailabilityInput) -> dict:
        block = AvailabilityBlockCreate(**payload.model_dump(exclude={"student_id"}))
        created = calendar_service.create_availability_block(
            self.session, payload.student_id, block
        )
        return AvailabilityBlockOut.model_validate(created).model_dump()

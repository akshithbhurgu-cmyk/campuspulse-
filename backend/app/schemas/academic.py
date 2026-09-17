from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import (
    AvailabilityBlockType,
    PersonalEventType,
)


class TopicProgressOut(BaseModel):
    id: int
    title: str
    completion_percentage: float


class CourseUnitOut(BaseModel):
    id: int
    sequence: int
    title: str
    topics: list[TopicProgressOut]


class CourseSummaryOut(BaseModel):
    id: int
    code: str
    name: str
    kind: str
    credits: float | None
    faculty_name: str | None
    attendance_percentage: float | None
    preparation_percentage: float


class CourseDetailOut(CourseSummaryOut):
    units: list[CourseUnitOut]


class AttendanceOut(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    attended_classes: int
    conducted_classes: int
    target_percentage: float
    attendance_percentage: float


class AttendanceImpactOut(AttendanceOut):
    if_next_attended_percentage: float
    if_next_missed_percentage: float
    safe_skips: int
    recovery_classes: int | None


class AssessmentOut(BaseModel):
    id: int
    course_id: int
    course_code: str
    course_name: str
    title: str
    assessment_type: str
    status: str
    scheduled_at: datetime | None
    maximum_marks: float | None
    earned_marks: float | None
    weightage: float | None
    topics: list[str]


class AssignmentOut(BaseModel):
    id: int
    course_id: int
    course_code: str
    course_name: str
    title: str
    description: str | None
    due_at: datetime | None
    submitted_at: datetime | None
    maximum_marks: float | None
    earned_marks: float | None
    is_submitted: bool


class AcademicCalendarEventOut(BaseModel):
    id: int
    title: str
    event_type: str
    starts_at: datetime
    ends_at: datetime
    is_all_day: bool
    description: str | None


class PersonalEventOut(BaseModel):
    id: int
    title: str
    event_type: str
    starts_at: datetime
    ends_at: datetime
    notes: str | None


class TimetableEntryOut(BaseModel):
    id: int
    course_id: int | None
    course_code: str | None
    course_name: str | None
    day_of_week: int
    start_time: time
    end_time: time
    session_kind: str
    location: str | None


class CalendarOut(BaseModel):
    academic_events: list[AcademicCalendarEventOut]
    personal_events: list[PersonalEventOut]
    timetable_entries: list[TimetableEntryOut]
    availability_blocks: list["AvailabilityBlockOut"]


class PreparationCourseOut(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    completion_percentage: float
    units: list[CourseUnitOut]


class TopicProgressUpdate(BaseModel):
    completion_percentage: float = Field(ge=0, le=100)


class PersonalEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    event_type: PersonalEventType
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None


class AvailabilityBlockCreate(BaseModel):
    block_type: AvailabilityBlockType
    block_date: date | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time
    end_time: time
    is_recurring: bool = False
    label: str | None = Field(default=None, max_length=120)


class AvailabilityBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    block_type: AvailabilityBlockType
    block_date: date | None
    day_of_week: int | None
    start_time: time
    end_time: time
    is_recurring: bool
    label: str | None

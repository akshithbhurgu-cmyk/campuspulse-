from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import (
    AnnouncementSource,
    AssessmentStatus,
    AssessmentType,
    AvailabilityBlockType,
    CalendarEventType,
    CourseKind,
    PersonalEventType,
    TimetableSessionKind,
)

if TYPE_CHECKING:
    from app.db.models.planning import (
        ChangeHistory,
        Priority,
        Risk,
        StudyProgress,
        StudySession,
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    roll_number: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    semesters: Mapped[list[Semester]] = relationship(back_populates="student", cascade="all, delete-orphan")
    personal_events: Mapped[list[PersonalEvent]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    availability_blocks: Mapped[list[AvailabilityBlock]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    study_progress: Mapped[list[StudyProgress]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    risks: Mapped[list[Risk]] = relationship(back_populates="student", cascade="all, delete-orphan")
    priorities: Mapped[list[Priority]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    study_plans: Mapped[list[StudyPlan]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    change_history: Mapped[list[ChangeHistory]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("student_id", "number", "academic_year", name="uq_semester_student_number_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    academic_year: Mapped[str] = mapped_column(String(32))
    term: Mapped[str | None] = mapped_column(String(32))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped[Student] = relationship(back_populates="semesters")
    courses: Mapped[list[Course]] = relationship(back_populates="semester", cascade="all, delete-orphan")
    timetable_entries: Mapped[list[TimetableEntry]] = relationship(
        back_populates="semester", cascade="all, delete-orphan"
    )
    calendar_events: Mapped[list[AcademicCalendarEvent]] = relationship(
        back_populates="semester", cascade="all, delete-orphan"
    )
    announcements: Mapped[list[Announcement]] = relationship(
        back_populates="semester", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("semester_id", "code", name="uq_course_semester_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(180))
    kind: Mapped[CourseKind] = mapped_column(Enum(CourseKind, name="course_kind"))
    credits: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    faculty_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    semester: Mapped[Semester] = relationship(back_populates="courses")
    units: Mapped[list[CourseUnit]] = relationship(back_populates="course", cascade="all, delete-orphan")
    timetable_entries: Mapped[list[TimetableEntry]] = relationship(back_populates="course")
    attendance: Mapped[Attendance | None] = relationship(
        back_populates="course", cascade="all, delete-orphan", uselist=False
    )
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    announcements: Mapped[list[Announcement]] = relationship(back_populates="course")
    risks: Mapped[list[Risk]] = relationship(back_populates="course")
    priorities: Mapped[list[Priority]] = relationship(back_populates="course")
    study_sessions: Mapped[list[StudySession]] = relationship(back_populates="course")


class CourseUnit(Base):
    __tablename__ = "course_units"
    __table_args__ = (
        UniqueConstraint("course_id", "sequence", name="uq_course_unit_sequence"),
        CheckConstraint("sequence > 0", name="ck_course_unit_sequence_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)

    course: Mapped[Course] = relationship(back_populates="units")
    topics: Mapped[list[Topic]] = relationship(back_populates="unit", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("unit_id", "sequence", name="uq_topic_unit_sequence"),
        CheckConstraint("sequence > 0", name="ck_topic_sequence_positive"),
        CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes > 0",
            name="ck_topic_estimated_minutes_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("course_units.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)

    unit: Mapped[CourseUnit] = relationship(back_populates="topics")
    assessment_links: Mapped[list[AssessmentTopic]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )
    study_progress: Mapped[list[StudyProgress]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[list[StudySession]] = relationship(back_populates="topic")


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_timetable_day_of_week"),
        CheckConstraint("end_time > start_time", name="ck_timetable_times_ordered"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    session_kind: Mapped[TimetableSessionKind] = mapped_column(
        Enum(TimetableSessionKind, name="timetable_session_kind")
    )
    location: Mapped[str | None] = mapped_column(String(120))

    semester: Mapped[Semester] = relationship(back_populates="timetable_entries")
    course: Mapped[Course | None] = relationship(back_populates="timetable_entries")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("attended_classes >= 0", name="ck_attendance_attended_nonnegative"),
        CheckConstraint("conducted_classes >= 0", name="ck_attendance_conducted_nonnegative"),
        CheckConstraint(
            "attended_classes <= conducted_classes", name="ck_attendance_attended_not_over_conducted"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), unique=True, index=True
    )
    attended_classes: Mapped[int] = mapped_column(Integer, default=0)
    conducted_classes: Mapped[int] = mapped_column(Integer, default=0)
    target_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("75.00"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped[Course] = relationship(back_populates="attendance")


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "maximum_marks IS NULL OR maximum_marks > 0", name="ck_assessment_maximum_marks_positive"
        ),
        CheckConstraint(
            "earned_marks IS NULL OR earned_marks >= 0", name="ck_assessment_earned_marks_nonnegative"
        ),
        CheckConstraint(
            "maximum_marks IS NULL OR earned_marks IS NULL OR earned_marks <= maximum_marks",
            name="ck_assessment_earned_within_maximum",
        ),
        CheckConstraint(
            "weightage IS NULL OR (weightage >= 0 AND weightage <= 100)",
            name="ck_assessment_weightage_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessment_type")
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status"), default=AssessmentStatus.PLANNED
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    maximum_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    earned_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    weightage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    course: Mapped[Course] = relationship(back_populates="assessments")
    topic_links: Mapped[list[AssessmentTopic]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    risks: Mapped[list[Risk]] = relationship(back_populates="assessment")
    priorities: Mapped[list[Priority]] = relationship(back_populates="assessment")


class AssessmentTopic(Base):
    __tablename__ = "assessment_topics"

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )

    assessment: Mapped[Assessment] = relationship(back_populates="topic_links")
    topic: Mapped[Topic] = relationship(back_populates="assessment_links")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "maximum_marks IS NULL OR maximum_marks > 0", name="ck_assignment_maximum_marks_positive"
        ),
        CheckConstraint(
            "earned_marks IS NULL OR earned_marks >= 0", name="ck_assignment_earned_marks_nonnegative"
        ),
        CheckConstraint(
            "maximum_marks IS NULL OR earned_marks IS NULL OR earned_marks <= maximum_marks",
            name="ck_assignment_earned_within_maximum",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    maximum_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    earned_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    course: Mapped[Course] = relationship(back_populates="assignments")
    priorities: Mapped[list[Priority]] = relationship(back_populates="assignment")


class AcademicCalendarEvent(Base):
    __tablename__ = "academic_calendar_events"
    __table_args__ = (CheckConstraint("ends_at >= starts_at", name="ck_calendar_event_times_ordered"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    event_type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType, name="calendar_event_type")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)

    semester: Mapped[Semester] = relationship(back_populates="calendar_events")


class PersonalEvent(Base):
    __tablename__ = "personal_events"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ck_personal_event_times_ordered"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    event_type: Mapped[PersonalEventType] = mapped_column(
        Enum(PersonalEventType, name="personal_event_type")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="personal_events")


class AvailabilityBlock(Base):
    __tablename__ = "availability_blocks"
    __table_args__ = (
        CheckConstraint("day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6", name="ck_availability_day"),
        CheckConstraint("end_time > start_time", name="ck_availability_times_ordered"),
        CheckConstraint(
            "block_date IS NOT NULL OR day_of_week IS NOT NULL", name="ck_availability_has_schedule"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    block_type: Mapped[AvailabilityBlockType] = mapped_column(
        Enum(AvailabilityBlockType, name="availability_block_type")
    )
    block_date: Mapped[date | None] = mapped_column(Date)
    day_of_week: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    label: Mapped[str | None] = mapped_column(String(120))

    student: Mapped[Student] = relationship(back_populates="availability_blocks")


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    source: Mapped[AnnouncementSource] = mapped_column(
        Enum(AnnouncementSource, name="announcement_source")
    )
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    semester: Mapped[Semester] = relationship(back_populates="announcements")
    course: Mapped[Course | None] = relationship(back_populates="announcements")

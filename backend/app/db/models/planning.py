from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import (
    PriorityType,
    RiskType,
    Severity,
    StudyPlanStatus,
    StudySessionStatus,
)


class StudyProgress(Base):
    __tablename__ = "study_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_study_progress_student_topic"),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_study_progress_percentage_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    completion_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student: Mapped["Student"] = relationship(back_populates="study_progress")
    topic: Mapped["Topic"] = relationship(back_populates="study_progress")


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_risk_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), index=True
    )
    risk_type: Mapped[RiskType] = mapped_column(Enum(RiskType, name="risk_type"))
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    summary: Mapped[str] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    student: Mapped["Student"] = relationship(back_populates="risks")
    course: Mapped["Course | None"] = relationship(back_populates="risks")
    assessment: Mapped["Assessment | None"] = relationship(back_populates="risks")


class Priority(Base):
    __tablename__ = "priorities"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_priority_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"), index=True
    )
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="SET NULL"), index=True
    )
    priority_type: Mapped[PriorityType] = mapped_column(Enum(PriorityType, name="priority_type"))
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    rank: Mapped[int | None] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    student: Mapped["Student"] = relationship(back_populates="priorities")
    course: Mapped["Course | None"] = relationship(back_populates="priorities")
    assessment: Mapped["Assessment | None"] = relationship(back_populates="priorities")
    assignment: Mapped["Assignment | None"] = relationship(back_populates="priorities")


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (UniqueConstraint("student_id", "plan_date", name="uq_study_plan_student_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[StudyPlanStatus] = mapped_column(
        Enum(StudyPlanStatus, name="study_plan_status"), default=StudyPlanStatus.DRAFT
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="study_plans")
    sessions: Mapped[list["StudySession"]] = relationship(
        back_populates="study_plan", cascade="all, delete-orphan"
    )


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_study_session_times_ordered"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[StudySessionStatus] = mapped_column(
        Enum(StudySessionStatus, name="study_session_status"), default=StudySessionStatus.PLANNED
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    study_plan: Mapped[StudyPlan] = relationship(back_populates="sessions")
    course: Mapped["Course | None"] = relationship(back_populates="study_sessions")
    topic: Mapped["Topic | None"] = relationship(back_populates="study_sessions")


class ChangeHistory(Base):
    __tablename__ = "change_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64))
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["Student"] = relationship(back_populates="change_history")


from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class NextClassOut(BaseModel):
    timetable_entry_id: int
    course_id: int | None
    course_name: str | None
    starts_at: datetime
    ends_at: datetime
    session_kind: str
    location: str | None


class DashboardSessionOut(BaseModel):
    id: int | None = None
    title: str
    course_id: int | None
    topic_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    status: str
    is_locked: bool = False
    source: Literal["saved", "preview"]


class DashboardPriorityOut(BaseModel):
    task_key: str
    entity_type: str
    entity_id: int
    course_id: int
    title: str
    deadline_at: datetime | None
    score: float = Field(ge=0, le=100)
    level: str
    preparation_percentage: float | None
    required_minutes: int
    estimate_source: str
    factors: dict[str, float]


class DashboardRiskOut(BaseModel):
    risk_type: str
    course_id: int | None = None
    task_key: str | None = None
    score: float = Field(ge=0, le=100)
    severity: str
    summary: str


class RecentChangeOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    action: str
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    created_at: datetime


class ChangeFieldOut(BaseModel):
    field: str
    before: Any | None = None
    after: Any | None = None


class ChangeOut(BaseModel):
    id: int
    title: str
    reason: str
    entity_type: str
    entity_id: str
    action: str
    changes: list[ChangeFieldOut]
    created_at: datetime


class DashboardOut(BaseModel):
    student_id: int
    generated_at: datetime
    timezone: str
    next_class: NextClassOut | None
    today_plan: list[DashboardSessionOut]
    plan_source: Literal["saved", "preview"]
    top_priorities: list[DashboardPriorityOut]
    risks: list[DashboardRiskOut]
    recent_changes: list[RecentChangeOut]
    unscheduled_minutes: dict[str, int]

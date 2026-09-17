from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from math import inf

from app.engines.time_blocks import TimeBlock


@dataclass(frozen=True, slots=True)
class StudyTask:
    key: str
    title: str
    required_minutes: int
    priority_score: float
    deadline_at: datetime | None = None
    course_id: int | None = None
    topic_id: int | None = None

    def __post_init__(self) -> None:
        if self.required_minutes <= 0:
            raise ValueError("Study task duration must be positive.")


@dataclass(frozen=True, slots=True)
class PlannedStudySession:
    task_key: str
    title: str
    starts_at: datetime
    ends_at: datetime
    priority_score: float
    deadline_at: datetime | None
    course_id: int | None = None
    topic_id: int | None = None
    locked: bool = False

    @property
    def duration_minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    def as_time_block(self) -> TimeBlock:
        return TimeBlock(self.starts_at, self.ends_at, self.title, self.locked)


@dataclass(frozen=True, slots=True)
class PlanResult:
    sessions: tuple[PlannedStudySession, ...]
    unresolved_minutes: dict[str, int]


class Planner:
    @staticmethod
    def generate(
        tasks: list[StudyTask],
        available_slots: list[TimeBlock],
        *,
        maximum_session_minutes: int = 90,
        minimum_session_minutes: int = 30,
    ) -> PlanResult:
        if maximum_session_minutes < minimum_session_minutes or minimum_session_minutes <= 0:
            raise ValueError("Session limits are invalid.")

        slots = sorted(available_slots, key=lambda slot: slot.starts_at)
        tasks_by_priority = sorted(
            tasks,
            key=lambda task: (
                -task.priority_score,
                task.deadline_at.timestamp() if task.deadline_at else inf,
            ),
        )
        sessions: list[PlannedStudySession] = []
        unresolved: dict[str, int] = {}

        for task in tasks_by_priority:
            remaining = task.required_minutes
            slot_index = 0
            while remaining > 0 and slot_index < len(slots):
                slot = slots[slot_index]
                usable_end = min(slot.ends_at, task.deadline_at) if task.deadline_at else slot.ends_at
                usable_minutes = int((usable_end - slot.starts_at).total_seconds() // 60)
                minimum_needed = min(minimum_session_minutes, remaining)
                if usable_minutes < minimum_needed:
                    slot_index += 1
                    continue

                allocation = min(remaining, maximum_session_minutes, usable_minutes)
                session_end = slot.starts_at + timedelta(minutes=allocation)
                sessions.append(
                    PlannedStudySession(
                        task_key=task.key,
                        title=task.title,
                        starts_at=slot.starts_at,
                        ends_at=session_end,
                        priority_score=task.priority_score,
                        deadline_at=task.deadline_at,
                        course_id=task.course_id,
                        topic_id=task.topic_id,
                    )
                )
                remaining -= allocation
                if session_end < slot.ends_at:
                    slots[slot_index] = replace(slot, starts_at=session_end)
                else:
                    slots.pop(slot_index)

            if remaining:
                unresolved[task.key] = remaining

        return PlanResult(
            sessions=tuple(sorted(sessions, key=lambda item: item.starts_at)),
            unresolved_minutes=unresolved,
        )

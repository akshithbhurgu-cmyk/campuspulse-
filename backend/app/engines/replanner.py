from __future__ import annotations

from dataclasses import dataclass
from app.engines.availability import AvailabilityEngine
from app.engines.conflict import ConflictEngine
from app.engines.planner import PlannedStudySession, Planner, StudyTask
from app.engines.time_blocks import TimeBlock


@dataclass(frozen=True, slots=True)
class ReplanResult:
    kept: tuple[PlannedStudySession, ...]
    rescheduled: tuple[PlannedStudySession, ...]
    unresolved_task_keys: tuple[str, ...]
    locked_conflicts: tuple[PlannedStudySession, ...]


class Replanner:
    @staticmethod
    def replan(
        existing_sessions: list[PlannedStudySession],
        new_busy_blocks: list[TimeBlock],
        replacement_windows: list[TimeBlock],
    ) -> ReplanResult:
        kept: list[PlannedStudySession] = []
        affected: list[PlannedStudySession] = []
        locked_conflicts: list[PlannedStudySession] = []

        for session in existing_sessions:
            if not ConflictEngine.has_conflict(session.as_time_block(), new_busy_blocks):
                kept.append(session)
            elif session.locked:
                kept.append(session)
                locked_conflicts.append(session)
            else:
                affected.append(session)

        occupied = [session.as_time_block() for session in kept] + new_busy_blocks
        replacement_slots: list[TimeBlock] = []
        for window in replacement_windows:
            replacement_slots.extend(
                AvailabilityEngine.find_free_slots(
                    window.starts_at,
                    window.ends_at,
                    occupied,
                    minimum_minutes=1,
                )
            )

        tasks = [
            StudyTask(
                key=session.task_key,
                title=session.title,
                required_minutes=session.duration_minutes,
                priority_score=session.priority_score,
                deadline_at=session.deadline_at,
                course_id=session.course_id,
                topic_id=session.topic_id,
            )
            for session in affected
        ]
        plan = Planner.generate(
            tasks,
            replacement_slots,
            minimum_session_minutes=1,
            maximum_session_minutes=max(
                (task.required_minutes for task in tasks), default=90
            ),
        )
        unresolved = tuple(plan.unresolved_minutes)
        return ReplanResult(
            kept=tuple(sorted(kept, key=lambda item: item.starts_at)),
            rescheduled=plan.sessions,
            unresolved_task_keys=unresolved,
            locked_conflicts=tuple(locked_conflicts),
        )

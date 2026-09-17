from dataclasses import dataclass

from app.engines.time_blocks import TimeBlock


@dataclass(frozen=True, slots=True)
class Conflict:
    candidate: TimeBlock
    existing: TimeBlock
    overlap_minutes: int


class ConflictEngine:
    @staticmethod
    def find_conflicts(candidate: TimeBlock, existing_blocks: list[TimeBlock]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for existing in existing_blocks:
            if not candidate.overlaps(existing):
                continue
            overlap_start = max(candidate.starts_at, existing.starts_at)
            overlap_end = min(candidate.ends_at, existing.ends_at)
            conflicts.append(
                Conflict(
                    candidate=candidate,
                    existing=existing,
                    overlap_minutes=int((overlap_end - overlap_start).total_seconds() // 60),
                )
            )
        return conflicts

    @staticmethod
    def has_conflict(candidate: TimeBlock, existing_blocks: list[TimeBlock]) -> bool:
        return any(candidate.overlaps(existing) for existing in existing_blocks)


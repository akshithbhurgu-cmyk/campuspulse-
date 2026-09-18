from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TimeBlock:
    starts_at: datetime
    ends_at: datetime
    label: str = ""
    locked: bool = False
    source_id: int | None = None

    def __post_init__(self) -> None:
        if self.ends_at <= self.starts_at:
            raise ValueError("A time block must end after it starts.")

    @property
    def duration_minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)

    def overlaps(self, other: TimeBlock) -> bool:
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at

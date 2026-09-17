from __future__ import annotations

from datetime import datetime, timedelta

from app.engines.time_blocks import TimeBlock


class AvailabilityEngine:
    @staticmethod
    def find_free_slots(
        window_start: datetime,
        window_end: datetime,
        busy_blocks: list[TimeBlock],
        *,
        minimum_minutes: int = 30,
    ) -> list[TimeBlock]:
        if window_end <= window_start:
            raise ValueError("Availability window must end after it starts.")
        if minimum_minutes <= 0:
            raise ValueError("Minimum slot length must be positive.")

        clipped = sorted(
            (
                TimeBlock(
                    starts_at=max(block.starts_at, window_start),
                    ends_at=min(block.ends_at, window_end),
                    label=block.label,
                    locked=block.locked,
                )
                for block in busy_blocks
                if block.starts_at < window_end and window_start < block.ends_at
            ),
            key=lambda block: block.starts_at,
        )
        merged: list[TimeBlock] = []
        for block in clipped:
            if merged and block.starts_at <= merged[-1].ends_at:
                previous = merged[-1]
                merged[-1] = TimeBlock(
                    starts_at=previous.starts_at,
                    ends_at=max(previous.ends_at, block.ends_at),
                    label="busy",
                    locked=previous.locked or block.locked,
                )
            else:
                merged.append(block)

        free: list[TimeBlock] = []
        cursor = window_start
        for block in merged:
            if block.starts_at > cursor:
                AvailabilityEngine._append_if_long_enough(
                    free, cursor, block.starts_at, minimum_minutes
                )
            cursor = max(cursor, block.ends_at)
        if cursor < window_end:
            AvailabilityEngine._append_if_long_enough(free, cursor, window_end, minimum_minutes)
        return free

    @staticmethod
    def split_slot(slot: TimeBlock, minutes: int) -> tuple[TimeBlock, TimeBlock | None]:
        if minutes <= 0 or minutes > slot.duration_minutes:
            raise ValueError("Split length must fit inside the slot.")
        split_at = slot.starts_at + timedelta(minutes=minutes)
        used = TimeBlock(slot.starts_at, split_at, slot.label, slot.locked)
        remainder = (
            TimeBlock(split_at, slot.ends_at, slot.label, slot.locked)
            if split_at < slot.ends_at
            else None
        )
        return used, remainder

    @staticmethod
    def _append_if_long_enough(
        slots: list[TimeBlock], starts_at: datetime, ends_at: datetime, minimum_minutes: int
    ) -> None:
        if (ends_at - starts_at).total_seconds() >= minimum_minutes * 60:
            slots.append(TimeBlock(starts_at, ends_at, label="available"))


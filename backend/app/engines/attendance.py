from dataclasses import dataclass
from math import ceil, floor


@dataclass(frozen=True, slots=True)
class AttendanceImpact:
    current_percentage: float
    if_next_attended_percentage: float
    if_next_missed_percentage: float
    safe_skips: int
    recovery_classes: int | None


class AttendanceEngine:
    @staticmethod
    def calculate(attended: int, conducted: int, target_percentage: float = 75.0) -> AttendanceImpact:
        if attended < 0 or conducted < 0:
            raise ValueError("Attendance counts cannot be negative.")
        if attended > conducted:
            raise ValueError("Attended classes cannot exceed conducted classes.")
        if not 0 < target_percentage <= 100:
            raise ValueError("Target percentage must be between 0 and 100.")

        current = AttendanceEngine._percentage(attended, conducted)
        if_attended = AttendanceEngine._percentage(attended + 1, conducted + 1)
        if_missed = AttendanceEngine._percentage(attended, conducted + 1)
        target = target_percentage / 100

        safe_skips = max(0, floor(attended / target - conducted))
        if conducted == 0:
            recovery_classes: int | None = 1
        elif current >= target_percentage:
            recovery_classes: int | None = 0
        elif target >= 1:
            recovery_classes = None
        else:
            recovery_classes = max(0, ceil((target * conducted - attended) / (1 - target)))

        return AttendanceImpact(
            current_percentage=current,
            if_next_attended_percentage=if_attended,
            if_next_missed_percentage=if_missed,
            safe_skips=safe_skips,
            recovery_classes=recovery_classes,
        )

    @staticmethod
    def _percentage(attended: int, conducted: int) -> float:
        return round(attended * 100 / conducted, 2) if conducted else 0.0

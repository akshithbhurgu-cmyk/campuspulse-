from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RiskInputs:
    now: datetime
    deadline_at: datetime | None = None
    preparation_percentage: float = 100.0
    performance_percentage: float = 100.0
    performance_target: float = 75.0
    attendance_percentage: float = 100.0
    attendance_target: float = 75.0
    required_minutes: int = 0
    available_minutes: int = 0
    conflict_count: int = 0


@dataclass(frozen=True, slots=True)
class RiskScores:
    attendance: float
    deadline: float
    preparation: float
    performance: float
    workload: float
    conflict: float
    overall: float


class RiskEngine:
    @staticmethod
    def calculate(inputs: RiskInputs) -> RiskScores:
        attendance = RiskEngine.attendance_risk(
            inputs.attendance_percentage, inputs.attendance_target
        )
        deadline = RiskEngine.deadline_risk(inputs.now, inputs.deadline_at)
        preparation = RiskEngine._clamp(100 - inputs.preparation_percentage)
        performance = RiskEngine.performance_risk(
            inputs.performance_percentage, inputs.performance_target
        )
        workload = RiskEngine.workload_risk(inputs.required_minutes, inputs.available_minutes)
        conflict = RiskEngine._clamp(inputs.conflict_count * 50)
        overall = round(
            attendance * 0.20
            + deadline * 0.25
            + preparation * 0.20
            + performance * 0.15
            + workload * 0.15
            + conflict * 0.05,
            2,
        )
        return RiskScores(
            attendance=attendance,
            deadline=deadline,
            preparation=preparation,
            performance=performance,
            workload=workload,
            conflict=conflict,
            overall=overall,
        )

    @staticmethod
    def attendance_risk(current: float, target: float) -> float:
        if current < target:
            return RiskEngine._clamp(70 + (target - current) * 3)
        buffer = current - target
        return RiskEngine._clamp(40 - buffer * 4)

    @staticmethod
    def deadline_risk(now: datetime, deadline_at: datetime | None) -> float:
        if deadline_at is None:
            return 0.0
        hours = (deadline_at - now).total_seconds() / 3600
        if hours <= 0:
            return 100.0
        if hours <= 24:
            return 95.0
        if hours <= 48:
            return 85.0
        if hours <= 72:
            return 70.0
        if hours <= 168:
            return 50.0
        if hours <= 336:
            return 25.0
        return 10.0

    @staticmethod
    def performance_risk(current: float, target: float) -> float:
        if target <= 0:
            return 0.0
        return RiskEngine._clamp((target - current) * 100 / target)

    @staticmethod
    def workload_risk(required_minutes: int, available_minutes: int) -> float:
        if required_minutes <= 0:
            return 0.0
        if available_minutes <= 0:
            return 100.0
        return RiskEngine._clamp(required_minutes * 100 / available_minutes)

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)


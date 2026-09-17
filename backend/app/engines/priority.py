from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriorityFactors:
    deadline_urgency: float
    assessment_importance: float
    preparation_gap: float
    performance_gap: float
    attendance_risk: float
    workload_risk: float
    conflict_risk: float


@dataclass(frozen=True, slots=True)
class PriorityResult:
    score: float
    level: str


class PriorityEngine:
    WEIGHTS = {
        "deadline_urgency": 0.25,
        "assessment_importance": 0.20,
        "preparation_gap": 0.20,
        "performance_gap": 0.15,
        "attendance_risk": 0.10,
        "workload_risk": 0.05,
        "conflict_risk": 0.05,
    }

    @classmethod
    def calculate(cls, factors: PriorityFactors) -> PriorityResult:
        score = round(
            sum(
                cls._clamp(getattr(factors, name)) * weight
                for name, weight in cls.WEIGHTS.items()
            ),
            2,
        )
        if score >= 85:
            level = "CRITICAL"
        elif score >= 70:
            level = "HIGH"
        elif score >= 45:
            level = "MEDIUM"
        else:
            level = "LOW"
        return PriorityResult(score=score, level=level)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, float(value)))


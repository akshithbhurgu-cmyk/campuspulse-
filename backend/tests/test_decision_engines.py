import unittest
from datetime import UTC, datetime, timedelta

from app.engines.attendance import AttendanceEngine
from app.engines.conflict import ConflictEngine
from app.engines.priority import PriorityEngine, PriorityFactors
from app.engines.risk import RiskEngine, RiskInputs
from app.engines.time_blocks import TimeBlock


class AttendanceEngineTests(unittest.TestCase):
    def test_risky_attendance_recovery(self) -> None:
        result = AttendanceEngine.calculate(attended=34, conducted=46, target_percentage=75)
        self.assertEqual(result.current_percentage, 73.91)
        self.assertEqual(result.recovery_classes, 2)
        self.assertEqual(result.safe_skips, 0)
        self.assertLess(result.if_next_missed_percentage, result.current_percentage)

    def test_safe_skips_are_calculated(self) -> None:
        result = AttendanceEngine.calculate(attended=35, conducted=40, target_percentage=75)
        self.assertEqual(result.safe_skips, 6)
        self.assertEqual(result.recovery_classes, 0)

    def test_invalid_counts_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AttendanceEngine.calculate(attended=5, conducted=4)

    def test_no_classes_requires_first_attended_class(self) -> None:
        result = AttendanceEngine.calculate(attended=0, conducted=0)
        self.assertEqual(result.current_percentage, 0)
        self.assertEqual(result.recovery_classes, 1)


class RiskAndPriorityEngineTests(unittest.TestCase):
    def test_risk_components_are_deterministic(self) -> None:
        now = datetime(2026, 9, 16, 9, tzinfo=UTC)
        result = RiskEngine.calculate(
            RiskInputs(
                now=now,
                deadline_at=now + timedelta(hours=36),
                preparation_percentage=42,
                performance_percentage=65,
                attendance_percentage=66.67,
                required_minutes=300,
                available_minutes=180,
                conflict_count=1,
            )
        )
        self.assertEqual(result.deadline, 85)
        self.assertEqual(result.preparation, 58)
        self.assertEqual(result.workload, 100)
        self.assertEqual(result.conflict, 50)
        self.assertGreater(result.overall, 60)

    def test_priority_weighting_and_level(self) -> None:
        result = PriorityEngine.calculate(
            PriorityFactors(
                deadline_urgency=95,
                assessment_importance=90,
                preparation_gap=80,
                performance_gap=65,
                attendance_risk=70,
                workload_risk=100,
                conflict_risk=50,
            )
        )
        self.assertEqual(result.score, 82.0)
        self.assertEqual(result.level, "HIGH")


class ConflictEngineTests(unittest.TestCase):
    def test_touching_blocks_do_not_conflict(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        candidate = TimeBlock(start, start + timedelta(hours=1), "Study")
        touching = TimeBlock(start + timedelta(hours=1), start + timedelta(hours=2), "Dinner")
        self.assertFalse(ConflictEngine.has_conflict(candidate, [touching]))

    def test_overlap_minutes_are_reported(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        candidate = TimeBlock(start, start + timedelta(hours=1), "Study")
        busy = TimeBlock(start + timedelta(minutes=30), start + timedelta(hours=2), "Gym")
        conflict = ConflictEngine.find_conflicts(candidate, [busy])[0]
        self.assertEqual(conflict.overlap_minutes, 30)


if __name__ == "__main__":
    unittest.main()

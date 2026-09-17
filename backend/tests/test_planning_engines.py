import unittest
from datetime import UTC, datetime, timedelta

from app.engines.availability import AvailabilityEngine
from app.engines.planner import PlannedStudySession, Planner, StudyTask
from app.engines.replanner import Replanner
from app.engines.time_blocks import TimeBlock


class AvailabilityEngineTests(unittest.TestCase):
    def test_overlapping_busy_blocks_are_merged(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        free = AvailabilityEngine.find_free_slots(
            start,
            start + timedelta(hours=5),
            [
                TimeBlock(start + timedelta(hours=1), start + timedelta(hours=2), "Travel"),
                TimeBlock(
                    start + timedelta(hours=1, minutes=30),
                    start + timedelta(hours=3),
                    "Dinner",
                ),
            ],
        )
        self.assertEqual([(slot.starts_at.hour, slot.ends_at.hour) for slot in free], [(18, 19), (21, 23)])


class PlannerTests(unittest.TestCase):
    def test_higher_priority_task_receives_earliest_slots(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        result = Planner.generate(
            [
                StudyTask("low", "EWP revision", 60, 50),
                StudyTask("high", "DL slip test", 120, 95),
            ],
            [
                TimeBlock(start, start + timedelta(hours=2), "available"),
                TimeBlock(start + timedelta(hours=3), start + timedelta(hours=4), "available"),
            ],
        )
        self.assertEqual(result.sessions[0].task_key, "high")
        self.assertEqual(sum(item.duration_minutes for item in result.sessions), 180)
        self.assertFalse(result.unresolved_minutes)

    def test_unresolved_work_is_reported(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        result = Planner.generate(
            [StudyTask("dl", "DL", 180, 95)],
            [TimeBlock(start, start + timedelta(hours=1), "available")],
        )
        self.assertEqual(result.unresolved_minutes, {"dl": 120})


class ReplannerTests(unittest.TestCase):
    def test_only_conflicting_unlocked_session_moves(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        affected = PlannedStudySession(
            "dl",
            "DL revision",
            start,
            start + timedelta(hours=1),
            95,
            start + timedelta(days=1),
        )
        unaffected = PlannedStudySession(
            "ewp",
            "EWP work",
            start + timedelta(hours=2),
            start + timedelta(hours=3),
            70,
            start + timedelta(days=2),
        )
        result = Replanner.replan(
            [affected, unaffected],
            [
                TimeBlock(
                    start + timedelta(minutes=30),
                    start + timedelta(hours=1, minutes=30),
                    "New personal event",
                )
            ],
            [TimeBlock(start, start + timedelta(hours=5), "replacement window")],
        )
        self.assertEqual([item.task_key for item in result.kept], ["ewp"])
        self.assertEqual(sum(item.duration_minutes for item in result.rescheduled), 60)
        self.assertFalse(result.unresolved_task_keys)

    def test_locked_conflict_is_reported_not_moved(self) -> None:
        start = datetime(2026, 9, 16, 18, tzinfo=UTC)
        locked = PlannedStudySession(
            "dl",
            "Locked DL revision",
            start,
            start + timedelta(hours=1),
            95,
            None,
            locked=True,
        )
        result = Replanner.replan(
            [locked],
            [TimeBlock(start, start + timedelta(hours=1), "New event")],
            [TimeBlock(start + timedelta(hours=1), start + timedelta(hours=3), "available")],
        )
        self.assertEqual(result.kept, (locked,))
        self.assertEqual(result.locked_conflicts, (locked,))
        self.assertFalse(result.rescheduled)


if __name__ == "__main__":
    unittest.main()


import os
import unittest
from datetime import UTC, date, datetime
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AcademicCalendarEvent, Announcement, Assessment, Assignment, ChangeHistory, IngestionItem
from app.ingestion.extractor import AcademicExtraction
from app.ingestion.extractor import explicit_date, explicit_event_type
from app.seed import seed_synthetic_semester
from app.services.ingestion import ingestion_service


class StaticExtractor:
    def extract(self, text):
        return AcademicExtraction(
            title="CNN Architecture Slip Test", event_type="ASSESSMENT", course_name="Deep Learning",
            scheduled_at=None, topics=["CNN", "VGGNet", "ResNet"], summary="Slip-test notice.", confidence=0.9,
        )


class QALRExtractor:
    def extract(self, text):
        return AcademicExtraction(
            title="QALR II Internal", event_type="ASSESSMENT", course_name="QALR II",
            scheduled_at=None, topics=[], summary="Assessment notice.", confidence=0.9,
        )


class EventExtractor:
    def __init__(self, event_type, course_name="Deep Learning"):
        self.event_type = event_type
        self.course_name = course_name

    def extract(self, text):
        return AcademicExtraction(
            title="Approved academic update", event_type=self.event_type, course_name=self.course_name,
            scheduled_at=datetime(2026, 9, 25, tzinfo=UTC), topics=[], summary="Approved source.", confidence=0.9,
        )


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        with patch("app.seed.date") as seed_date:
            seed_date.today.return_value = date(2026, 9, 16)
            seed_synthetic_semester(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_preview_is_review_only_and_matches_course(self):
        item = ingestion_service.preview_text(self.db, 1, "DL slip test notice", StaticExtractor())
        self.assertEqual(item.status, "PREVIEW")
        self.assertEqual(item.extraction["event_type"], "ASSESSMENT")
        self.assertEqual(item.extraction["course_match"], "DL")
        self.assertEqual(self.db.query(Announcement).count(), 3)

    def test_only_unambiguous_written_dates_are_parsed(self):
        self.assertEqual(str(explicit_date("Test on 18 September 2026").date()), "2026-09-18")
        self.assertIsNone(explicit_date("Test on 18/09/26"))

    def test_clear_holiday_notice_is_not_left_as_a_generic_announcement(self):
        self.assertEqual(
            explicit_event_type("The college will remain closed for an academic holiday on 21 October 2026."),
            "HOLIDAY",
        )
        self.assertIsNone(explicit_event_type("DL assignment is due on 21 October 2026."))

    def test_gmail_preview_is_idempotent_by_external_id(self):
        first = ingestion_service.preview_text(
            self.db, 1, "DL slip test notice", StaticExtractor(), source="GMAIL", external_id="gmail-123"
        )
        second = ingestion_service.preview_text(
            self.db, 1, "DL slip test notice", StaticExtractor(), source="GMAIL", external_id="gmail-123"
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.db.query(IngestionItem).filter_by(source="GMAIL").count(), 1)

    def test_course_match_ignores_punctuation_variants(self):
        item = ingestion_service.preview_text(self.db, 1, "QALR II internal assessment", QALRExtractor())
        self.assertEqual(item.extraction["course_match"], "QALR2")

    def test_apply_requires_preview_and_ignore_does_not_create_announcement(self):
        ignored = ingestion_service.preview_text(self.db, 1, "DL update", StaticExtractor())
        ingestion_service.ignore(self.db, 1, ignored.id)
        self.assertEqual(ignored.status, "IGNORED")
        self.assertEqual(self.db.query(Announcement).count(), 3)
        preview = ingestion_service.preview_text(self.db, 1, "DL update", StaticExtractor())
        applied, announcement, record_type, record_id = ingestion_service.apply(self.db, 1, preview.id)
        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(announcement.course_id, applied.course_id)
        self.assertIsNone(record_type)
        self.assertIsNone(record_id)
        with self.assertRaises(ValueError):
            ingestion_service.apply(self.db, 1, preview.id)

    def test_apply_creates_safe_structured_records_and_audit_history(self):
        scenarios = [
            ("ASSESSMENT", Assessment, "ASSESSMENT"),
            ("ASSIGNMENT", Assignment, "ASSIGNMENT"),
            ("DEADLINE", AcademicCalendarEvent, "ACADEMIC_CALENDAR_EVENT"),
        ]
        for event_type, model, expected_type in scenarios:
            item = ingestion_service.preview_text(
                self.db, 1, f"{event_type} update", EventExtractor(event_type)
            )
            _, _, record_type, record_id = ingestion_service.apply(self.db, 1, item.id)
            self.assertEqual(record_type, expected_type)
            self.assertIsNotNone(record_id)
            self.assertIsNotNone(self.db.get(model, record_id))
        self.assertEqual(self.db.query(ChangeHistory).filter_by(action="INGESTION_APPLIED").count(), 3)


if __name__ == "__main__":
    unittest.main()

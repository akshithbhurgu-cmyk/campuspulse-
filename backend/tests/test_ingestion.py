import os
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Announcement, IngestionItem
from app.ingestion.extractor import AcademicExtraction
from app.ingestion.extractor import explicit_date
from app.seed import seed_synthetic_semester
from app.services.ingestion import ingestion_service


class StaticExtractor:
    def extract(self, text):
        return AcademicExtraction(
            title="CNN Architecture Slip Test", event_type="ASSESSMENT", course_name="Deep Learning",
            scheduled_at=None, topics=["CNN", "VGGNet", "ResNet"], summary="Slip-test notice.", confidence=0.9,
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

    def test_apply_requires_preview_and_ignore_does_not_create_announcement(self):
        ignored = ingestion_service.preview_text(self.db, 1, "DL update", StaticExtractor())
        ingestion_service.ignore(self.db, 1, ignored.id)
        self.assertEqual(ignored.status, "IGNORED")
        self.assertEqual(self.db.query(Announcement).count(), 3)
        preview = ingestion_service.preview_text(self.db, 1, "DL update", StaticExtractor())
        applied, announcement = ingestion_service.apply(self.db, 1, preview.id)
        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(announcement.course_id, applied.course_id)
        with self.assertRaises(ValueError):
            ingestion_service.apply(self.db, 1, preview.id)


if __name__ == "__main__":
    unittest.main()

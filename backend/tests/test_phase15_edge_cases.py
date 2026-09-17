import os
import unittest
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.orchestrator import CampusPulseAgent, OllamaUnavailableError
from app.db.base import Base
from app.db.models import StudyPlan, StudySession
from app.db.models.enums import StudyPlanStatus
from app.gmail import recent_messages
from app.ingestion.extractor import ExtractionError, OllamaExtractor
from app.ingestion.pdf import PdfExtractionError, extract_pdf_text
from app.seed import seed_synthetic_semester
from app.services.replanning import replanning_service
from app.services.plans import plan_service


class Phase15EdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        with patch("app.seed.date") as clock:
            clock.today.return_value = date(2026, 9, 16)
            seed_synthetic_semester(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_empty_or_non_pdf_content_fails_safely(self):
        with self.assertRaises(PdfExtractionError): extract_pdf_text(b"")
        with self.assertRaises(PdfExtractionError): extract_pdf_text(b"not a pdf")

    @patch("app.ingestion.extractor.ChatOllama")
    def test_malformed_llm_output_becomes_controlled_error(self, model):
        model.return_value.with_structured_output.return_value.invoke.return_value = {"bad": "shape"}
        with self.assertRaises(ExtractionError):
            OllamaExtractor(base_url="http://unused", model="test", timeout_seconds=1).extract("DL test")

    @patch("app.gmail.TOKEN")
    def test_gmail_without_authorization_is_controlled_error(self, token):
        token.exists.return_value = False
        with self.assertRaisesRegex(RuntimeError, "not authorized"):
            recent_messages()

    def test_locked_session_cannot_be_confirmed_for_move(self):
        plan = StudyPlan(student_id=1, plan_date=date(2026, 9, 16), status=StudyPlanStatus.ACTIVE)
        plan.sessions.append(StudySession(title="Locked", starts_at=datetime(2026, 9, 16, 10, tzinfo=UTC), ends_at=datetime(2026, 9, 16, 11, tzinfo=UTC), is_locked=True))
        self.db.add(plan); self.db.commit()
        with self.assertRaisesRegex(ValueError, "Locked"):
            replanning_service.confirm(self.db, 1, [{"session_id": plan.sessions[0].id, "starts_at": datetime(2026, 9, 16, 12, tzinfo=UTC), "ends_at": datetime(2026, 9, 16, 13, tzinfo=UTC)}])

    def test_replan_preview_has_no_database_side_effects(self):
        before = self.db.query(StudySession).count()
        result = replanning_service.preview(self.db, 1, datetime(2026, 9, 16, 9, tzinfo=UTC), datetime(2026, 9, 16, 10, tzinfo=UTC), timezone="Asia/Kolkata")
        self.assertEqual(self.db.query(StudySession).count(), before)
        self.assertIn("rescheduled", result)

    def test_saved_session_can_be_edited_without_overlapping_another_session(self):
        plan = StudyPlan(student_id=1, plan_date=date(2026, 9, 16), status=StudyPlanStatus.ACTIVE)
        plan.sessions.extend([
            StudySession(title="First", starts_at=datetime(2026, 9, 16, 10, tzinfo=UTC), ends_at=datetime(2026, 9, 16, 11, tzinfo=UTC)),
            StudySession(title="Second", starts_at=datetime(2026, 9, 16, 12, tzinfo=UTC), ends_at=datetime(2026, 9, 16, 13, tzinfo=UTC)),
        ])
        self.db.add(plan); self.db.commit()
        updated = plan_service.update_session(
            self.db, 1, plan.sessions[0].id, title="Edited task",
            starts_at=datetime(2026, 9, 16, 10, 30, tzinfo=UTC),
            ends_at=datetime(2026, 9, 16, 11, 30, tzinfo=UTC), timezone="Asia/Kolkata",
        )
        self.assertEqual(updated["title"], "Edited task")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            plan_service.update_session(
                self.db, 1, plan.sessions[0].id, title="Overlap",
                starts_at=datetime(2026, 9, 16, 12, 30, tzinfo=UTC),
                ends_at=datetime(2026, 9, 16, 13, 30, tzinfo=UTC), timezone="Asia/Kolkata",
            )

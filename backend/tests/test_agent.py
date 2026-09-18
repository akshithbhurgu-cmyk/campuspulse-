import os
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.orchestrator import CampusPulseAgent, OllamaUnavailableError
from app.db.base import Base
from app.seed import seed_synthetic_semester


class ToolCallingModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = 0
        type(self).last_instance = self

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "get_attendance", "args": {}, "id": "attendance-1"}],
            )
        return AIMessage(content="FOS attendance is 66.67%.")


class LoopingToolCallingModel(ToolCallingModel):
    def invoke(self, messages):
        self.calls += 1
        return AIMessage(
            content="",
            tool_calls=[{"name": "get_attendance", "args": {}, "id": f"loop-{self.calls}"}],
        )


class EmptyFinalModel(ToolCallingModel):
    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "get_dashboard", "args": {}, "id": "dashboard-1"}],
            )
        return AIMessage(content="")


class UnavailableModel(ToolCallingModel):
    def invoke(self, messages):
        raise ConnectionError("Ollama is offline")


class EmptyThenWriterModel(ToolCallingModel):
    instances = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_number = type(self).instances
        type(self).instances += 1
        self.bound = False

    def bind_tools(self, tools):
        self.bound = True
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.bound and self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "get_dashboard", "args": {}, "id": "dashboard-1"}],
            )
        if self.bound:
            return AIMessage(content="")
        return AIMessage(content="FOS attendance needs attention, so attend the next classes.")


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        with patch("app.seed.date") as seed_date:
            seed_date.today.return_value = date(2026, 9, 16)
            seed_synthetic_semester(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def agent(self):
        return CampusPulseAgent(
            self.db,
            base_url="http://unused.test",
            model="test-model",
            timezone="Asia/Kolkata",
            timeout_seconds=17,
        )

    @patch("app.agent.orchestrator.ChatOllama", ToolCallingModel)
    def test_graph_executes_a_read_tool_and_uses_configured_timeout(self):
        result = self.agent().ask("What is my FOS attendance?")
        self.assertEqual(result["answer"], "FOS attendance is 66.67%.")
        self.assertEqual(result["tools_used"], ["get_attendance"])
        self.assertEqual(result["model"], "test-model")
        self.assertEqual(ToolCallingModel.last_instance.kwargs["client_kwargs"], {"timeout": 17})

    @patch("app.agent.orchestrator.ChatOllama", LoopingToolCallingModel)
    def test_repeated_tool_calls_use_deterministic_fallback(self):
        result = self.agent().ask("Keep checking attendance forever")
        self.assertTrue(result["answer"].strip())
        self.assertIn("CampusPulse data", result["answer"])
        self.assertEqual(result["tools_used"], ["get_dashboard"])

    @patch("app.agent.orchestrator.ChatOllama", EmptyFinalModel)
    def test_empty_final_model_response_uses_a_tool_grounded_fallback(self):
        result = self.agent().ask("What are my biggest academic risks?")
        self.assertIn("highest current risks", result["answer"])
        self.assertTrue(result["answer"].strip())
        self.assertEqual(result["tools_used"], ["get_dashboard"])

    @patch("app.agent.orchestrator.ChatOllama", EmptyThenWriterModel)
    def test_empty_final_model_uses_tool_free_writer_before_fallback(self):
        EmptyThenWriterModel.instances = 0
        result = self.agent().ask("What should I focus on?")
        self.assertIn("FOS attendance needs attention", result["answer"])
        self.assertEqual(result["tools_used"], ["get_dashboard"])

    @patch("app.agent.orchestrator.ChatOllama", UnavailableModel)
    def test_unreachable_model_becomes_a_controlled_error(self):
        with self.assertRaises(OllamaUnavailableError):
            self.agent().ask("What is my attendance?")


if __name__ == "__main__":
    unittest.main()

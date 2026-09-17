"""A small LangGraph loop over the local Ollama model and factual tools."""
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

from app.agent.tools import build_read_tools
from app.services.dashboard import dashboard_service
from app.tools.campuspulse import CampusPulseTools

SYSTEM_PROMPT = """You are CampusPulse, a factual academic operations assistant.
Use the available tools whenever the question depends on the student's academic data.
Never invent dates, grades, attendance, preparation, or policy. Explain tool-derived
results briefly and clearly. This Phase 10 agent is read-only: do not claim you changed
progress, events, availability, plans, or any other student data.

Tool-use rules:
- For whether a student can skip a class, retrieve the attendance impact for that course
  before answering.
- For a named assessment, test, or slip test, retrieve upcoming assessments and
  preparation. Discuss only the assessment's linked topics and calculate any readiness
  from those tool results; do not substitute a whole-course average.
- For a study recommendation, retrieve the deterministic dashboard before answering.
- If a named course is not present in tool results, say that it was not found instead of
  inventing a record."""


class OllamaUnavailableError(RuntimeError):
    pass


class AgentExecutionError(RuntimeError):
    pass


class CampusPulseAgent:
    def __init__(
        self,
        session: Session,
        *,
        base_url: str,
        model: str,
        timezone: str,
        timeout_seconds: int = 120,
    ):
        self.session = session
        self.base_url = base_url
        self.model = model
        self.timezone = timezone
        self.timeout_seconds = timeout_seconds

    def ask(self, question: str, *, student_id: int = 1) -> dict[str, Any]:
        tools = build_read_tools(CampusPulseTools(self.session, timezone=self.timezone), student_id)
        model = ChatOllama(
            model=self.model,
            base_url=self.base_url,
            temperature=0,
            client_kwargs={"timeout": self.timeout_seconds},
        ).bind_tools(tools)

        def call_model(state: MessagesState) -> dict:
            response = model.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
            return {"messages": [response]}

        graph = StateGraph(MessagesState)
        graph.add_node("model", call_model)
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "model")
        graph.add_conditional_edges("model", tools_condition, {"tools": "tools", END: END})
        graph.add_edge("tools", "model")
        try:
            result = graph.compile().invoke(
                {"messages": [HumanMessage(content=question)]},
                {"recursion_limit": 12},
            )
        except GraphRecursionError as error:
            raise AgentExecutionError(
                "The local model exceeded the tool-call limit for this request."
            ) from error
        except Exception as error:
            raise OllamaUnavailableError("The local Ollama model could not be reached or complete this request.") from error
        messages = result["messages"]
        final_messages = [item for item in reversed(messages) if isinstance(item, AIMessage)]
        if not final_messages:
            raise OllamaUnavailableError("The local Ollama model returned no final response.")
        used = [getattr(item, "name", "") for item in messages if getattr(item, "type", "") == "tool"]
        content = next(
            (self._message_text(item) for item in final_messages if self._message_text(item)),
            "",
        )
        # Some local models correctly call a tool but occasionally emit an empty
        # final message. Never render a blank answer after successfully fetching
        # the student's data; return a deterministic, tool-grounded summary.
        if not content:
            content = self._tool_grounded_fallback(student_id, used)
        return {"answer": content, "tools_used": used, "model": self.model}

    @staticmethod
    def _message_text(message: AIMessage) -> str:
        content = message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return " ".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
        return str(content).strip()

    def _tool_grounded_fallback(self, student_id: int, used_tools: list[str]) -> str:
        dashboard = dashboard_service.get_dashboard(
            self.session, student_id, timezone=self.timezone
        )
        risks = dashboard["risks"][:3]
        priorities = dashboard["top_priorities"][:2]
        lines = [
            "I retrieved your CampusPulse data, but the local model did not finish its written explanation.",
        ]
        if risks:
            lines.append("Your highest current risks are:")
            lines.extend(
                f"- {risk['summary']} ({risk['severity'].lower()} risk)"
                for risk in risks
            )
        if priorities:
            lines.append("Top priorities:")
            lines.extend(
                f"- {item['title']} — priority {item['score']}%"
                for item in priorities
            )
        if not risks and not priorities:
            lines.append("There are no current risk or priority signals in the dashboard.")
        return "\n".join(lines)

from datetime import UTC, datetime
import re
from typing import Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field


class AcademicExtraction(BaseModel):
    """A proposed interpretation. It is always review-only until Apply."""

    title: str = Field(min_length=1, max_length=180)
    event_type: Literal["ANNOUNCEMENT", "ASSESSMENT", "ASSIGNMENT", "DEADLINE", "HOLIDAY", "EVENT"]
    course_name: str | None = Field(default=None, max_length=180)
    scheduled_at: datetime | None = None
    topics: list[str] = Field(default_factory=list, max_length=30)
    summary: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class ExtractionError(RuntimeError):
    pass


class Extractor(Protocol):
    def extract(self, text: str) -> AcademicExtraction: ...


SYSTEM_PROMPT = """Extract one academic notice into the supplied schema.
Return a cautious preview, never invent a course, date, time, topic, deadline, or marks.
Use ANNOUNCEMENT when the text does not clearly establish a specific event type.
Use null for a missing course or timestamp and reduce confidence when information is ambiguous.
The current date is provided only to interpret explicit relative dates; do not guess a year."""

MONTHS = {
    name: number for number, name in enumerate(
        ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"), 1
    )
}


def explicit_date(text: str) -> datetime | None:
    """Parse only an unambiguous written date; ambiguous dates stay for review."""
    match = re.search(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b", text.casefold())
    if match is None:
        return None
    try:
        return datetime(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1)), tzinfo=UTC)
    except ValueError:
        return None


class OllamaExtractor:
    def __init__(self, *, base_url: str, model: str, timeout_seconds: int):
        self.base_url = base_url
        self.model = model
        self.timeout_seconds = timeout_seconds

    def extract(self, text: str) -> AcademicExtraction:
        model = ChatOllama(
            model=self.model, base_url=self.base_url, temperature=0,
            client_kwargs={"timeout": self.timeout_seconds},
        ).with_structured_output(AcademicExtraction)
        try:
            result = model.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=text)])
            extraction = result if isinstance(result, AcademicExtraction) else AcademicExtraction.model_validate(result)
            parsed = explicit_date(text)
            return extraction.model_copy(update={"scheduled_at": parsed}) if parsed else extraction
        except Exception as error:
            raise ExtractionError("The local model could not extract this notice.") from error

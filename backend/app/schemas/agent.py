from pydantic import BaseModel, Field


class AgentQuery(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    student_id: int = Field(default=1, ge=1)


class AgentResponse(BaseModel):
    answer: str
    tools_used: list[str]
    model: str

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent import AgentExecutionError, CampusPulseAgent, OllamaUnavailableError
from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.agent import AgentQuery, AgentResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentResponse)
def query_agent(payload: AgentQuery, db: Annotated[Session, Depends(get_db)]) -> dict:
    settings = get_settings()
    agent = CampusPulseAgent(
        db, base_url=settings.ollama_base_url, model=settings.ollama_model,
        timezone=settings.campus_timezone, timeout_seconds=settings.ollama_timeout_seconds,
    )
    try:
        return agent.ask(payload.question, student_id=payload.student_id)
    except OllamaUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except AgentExecutionError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

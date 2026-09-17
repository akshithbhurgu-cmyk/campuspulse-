from typing import Annotated
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.dashboard import ChangeOut, DashboardOut
from app.services.common import StudentNotFoundError
from app.services.dashboard import dashboard_service
from app.services.plans import plan_service
from app.services.replanning import replanning_service
from app.services.changes import change_service
from datetime import datetime

router = APIRouter(tags=["dashboard"])


@router.get("/changes", response_model=list[ChangeOut])
def list_changes(db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1, limit: Annotated[int, Query(ge=1, le=100)] = 50) -> list[dict]:
    return change_service.list(db, student_id, limit)


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    student_id: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    try:
        return dashboard_service.get_dashboard(
            db, student_id, timezone=get_settings().campus_timezone
        )
    except StudentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/plans/today/save", status_code=status.HTTP_201_CREATED)
def save_today_plan(db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1) -> dict:
    try:
        return plan_service.save_today_preview(db, student_id, timezone=get_settings().campus_timezone)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

@router.post("/study-sessions/{session_id}/lock")
def lock_session(session_id: int, locked: bool, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1) -> dict:
    try: return plan_service.set_lock(db, student_id, session_id, locked)
    except LookupError as error: raise HTTPException(status_code=404, detail=str(error)) from error

@router.post("/plans/replan/preview")
def replan_preview(starts_at: datetime, ends_at: datetime, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1) -> dict:
    if ends_at <= starts_at: raise HTTPException(status_code=422, detail="End must be after start.")
    return replanning_service.preview(db, student_id, starts_at, ends_at, timezone=get_settings().campus_timezone)

class ReplanChange(BaseModel):
    session_id: int
    starts_at: datetime
    ends_at: datetime
@router.post("/plans/replan/confirm")
def confirm_replan(changes: list[ReplanChange], db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1) -> dict:
    try: return replanning_service.confirm(db, student_id, [item.model_dump() for item in changes])
    except (LookupError, ValueError) as error: raise HTTPException(status_code=422, detail=str(error)) from error

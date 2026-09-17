from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.dashboard import DashboardOut
from app.services.common import StudentNotFoundError
from app.services.dashboard import dashboard_service

router = APIRouter(tags=["dashboard"])


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


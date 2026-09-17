from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TextIngestionCreate(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    source: Literal["PASTE"] = "PASTE"


class IngestionItemOut(BaseModel):
    id: int
    source: str
    filename: str | None
    raw_text: str
    normalized_text: str
    extraction: dict | None
    course_id: int | None
    course_code: str | None = None
    status: str
    error: str | None
    created_at: datetime
    processed_at: datetime | None


class ApplyResult(BaseModel):
    item: IngestionItemOut
    announcement_id: int
    created_record_type: str | None = None
    created_record_id: int | None = None
    replan_required: bool = False
    dashboard_recalculated: bool

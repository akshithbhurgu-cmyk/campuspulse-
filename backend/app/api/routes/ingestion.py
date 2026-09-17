from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Course, IngestionItem
from app.core.config import get_settings
from app.ingestion.extractor import ExtractionError, OllamaExtractor
from app.ingestion.pdf import PdfExtractionError, extract_pdf_text
from app.gmail import recent_messages
from app.schemas.ingestion import ApplyResult, IngestionItemOut, TextIngestionCreate
from app.services.ingestion import ingestion_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def present(db: Session, item: IngestionItem) -> dict:
    course = db.get(Course, item.course_id) if item.course_id else None
    return {**{field: getattr(item, field) for field in IngestionItemOut.model_fields if field != "course_code"}, "course_code": course.code if course else None}


@router.post("/text", response_model=IngestionItemOut, status_code=status.HTTP_201_CREATED)
def preview_text(payload: TextIngestionCreate, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1):
    try:
        settings = get_settings()
        extractor = OllamaExtractor(
            base_url=settings.ollama_base_url, model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        return present(db, ingestion_service.preview_text(db, student_id, payload.text, extractor))
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ExtractionError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


@router.post("/pdf", response_model=IngestionItemOut, status_code=status.HTTP_201_CREATED)
def preview_pdf(
    file: Annotated[UploadFile, File(...)], db: Annotated[Session, Depends(get_db)],
    student_id: Annotated[int, Query(ge=1)] = 1,
):
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PDF file.")
    try:
        text = extract_pdf_text(file.file.read())
        settings = get_settings()
        extractor = OllamaExtractor(
            base_url=settings.ollama_base_url, model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        return present(db, ingestion_service.preview_text(
            db, student_id, text, extractor, source="PDF", filename=file.filename,
        ))
    except PdfExtractionError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except ExtractionError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/gmail/import", response_model=list[IngestionItemOut])
def import_gmail(
    db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1,
    query: str = "", max_results: Annotated[int, Query(ge=1, le=20)] = 10,
):
    settings = get_settings()
    extractor = OllamaExtractor(base_url=settings.ollama_base_url, model=settings.ollama_model, timeout_seconds=settings.ollama_timeout_seconds)
    try:
        return [present(db, ingestion_service.preview_text(db, student_id, message["text"], extractor, source="GMAIL")) for message in recent_messages(query, max_results)]
    except RuntimeError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    except ExtractionError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


@router.get("/{item_id}", response_model=IngestionItemOut)
def get_item(item_id: int, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1):
    try:
        return present(db, ingestion_service.get(db, student_id, item_id))
    except LookupError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/{item_id}/ignore", response_model=IngestionItemOut)
def ignore(item_id: int, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1):
    try:
        return present(db, ingestion_service.ignore(db, student_id, item_id))
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/{item_id}/apply", response_model=ApplyResult)
def apply(item_id: int, db: Annotated[Session, Depends(get_db)], student_id: Annotated[int, Query(ge=1)] = 1):
    try:
        item, announcement = ingestion_service.apply(db, student_id, item_id)
        return {"item": present(db, item), "announcement_id": announcement.id, "dashboard_recalculated": True}
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

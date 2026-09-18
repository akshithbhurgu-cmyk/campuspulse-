from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.academic import (
    AssignmentOut,
    AssessmentOut,
    AttendanceImpactOut,
    AttendanceOut,
    AvailabilityBlockCreate,
    AvailabilityBlockOut,
    CalendarOut,
    CourseDetailOut,
    CourseSummaryOut,
    PersonalEventCreate,
    PersonalEventOut,
    PreparationCourseOut,
    TopicProgressOut,
    TopicProgressUpdate,
)
from app.services.assessments import assessment_service
from app.services.attendance import attendance_service
from app.services.calendar import calendar_service
from app.services.courses import course_service

router = APIRouter(tags=["academics"])
DatabaseSession = Annotated[Session, Depends(get_db)]
StudentId = Annotated[int, Query(ge=1)]


def not_found(error: LookupError) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/courses", response_model=list[CourseSummaryOut])
def list_courses(db: DatabaseSession, student_id: StudentId = 1) -> list[dict]:
    try:
        return course_service.list_courses(db, student_id)
    except LookupError as error:
        not_found(error)


@router.get("/courses/{course_id}", response_model=CourseDetailOut)
def get_course(course_id: int, db: DatabaseSession, student_id: StudentId = 1) -> dict:
    try:
        return course_service.get_course(db, student_id, course_id)
    except LookupError as error:
        not_found(error)


@router.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(db: DatabaseSession, student_id: StudentId = 1) -> list[dict]:
    try:
        return attendance_service.list_attendance(db, student_id)
    except LookupError as error:
        not_found(error)


@router.get("/attendance/{course_id}", response_model=AttendanceOut)
def get_attendance(course_id: int, db: DatabaseSession, student_id: StudentId = 1) -> dict:
    try:
        return attendance_service.get_attendance(db, student_id, course_id)
    except LookupError as error:
        not_found(error)


@router.get("/attendance/{course_id}/impact", response_model=AttendanceImpactOut)
def get_attendance_impact(
    course_id: int, db: DatabaseSession, student_id: StudentId = 1
) -> dict:
    try:
        return attendance_service.get_impact(db, student_id, course_id)
    except LookupError as error:
        not_found(error)


@router.get("/assessments", response_model=list[AssessmentOut])
def list_assessments(
    db: DatabaseSession,
    student_id: StudentId = 1,
    upcoming_only: bool = False,
) -> list[dict]:
    try:
        return assessment_service.list_assessments(db, student_id, upcoming_only=upcoming_only)
    except LookupError as error:
        not_found(error)


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(
    db: DatabaseSession,
    student_id: StudentId = 1,
    pending_only: bool = False,
) -> list[dict]:
    try:
        return assessment_service.list_assignments(db, student_id, pending_only=pending_only)
    except LookupError as error:
        not_found(error)


@router.get("/calendar", response_model=CalendarOut)
def get_calendar(db: DatabaseSession, student_id: StudentId = 1) -> dict:
    try:
        return calendar_service.get_calendar(db, student_id)
    except LookupError as error:
        not_found(error)


@router.get("/preparation", response_model=list[PreparationCourseOut])
def get_preparation(db: DatabaseSession, student_id: StudentId = 1) -> list[dict]:
    try:
        return course_service.get_preparation(db, student_id)
    except LookupError as error:
        not_found(error)


@router.patch("/topics/{topic_id}/progress", response_model=TopicProgressOut)
def update_topic_progress(
    topic_id: int,
    payload: TopicProgressUpdate,
    db: DatabaseSession,
    student_id: StudentId = 1,
) -> dict:
    try:
        return course_service.update_topic_progress(
            db, student_id, topic_id, payload.completion_percentage
        )
    except LookupError as error:
        not_found(error)


@router.post(
    "/personal-events",
    response_model=PersonalEventOut,
    status_code=status.HTTP_201_CREATED,
)
def create_personal_event(
    payload: PersonalEventCreate,
    db: DatabaseSession,
    student_id: StudentId = 1,
) -> dict:
    try:
        return calendar_service.create_personal_event(db, student_id, payload)
    except LookupError as error:
        not_found(error)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post(
    "/availability",
    response_model=AvailabilityBlockOut,
    status_code=status.HTTP_201_CREATED,
)
def create_availability_block(
    payload: AvailabilityBlockCreate,
    db: DatabaseSession,
    student_id: StudentId = 1,
) -> AvailabilityBlockOut:
    try:
        return AvailabilityBlockOut.model_validate(
            calendar_service.create_availability_block(db, student_id, payload)
        )
    except LookupError as error:
        not_found(error)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.delete("/availability/{block_id}")
def delete_availability_block(
    block_id: int, db: DatabaseSession, student_id: StudentId = 1
) -> dict:
    try:
        return calendar_service.delete_availability_block(db, student_id, block_id)
    except LookupError as error:
        not_found(error)

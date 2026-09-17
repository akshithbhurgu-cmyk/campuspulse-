from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Assessment, AssessmentTopic, Assignment, Course, Semester
from app.db.models.enums import AssessmentStatus
from app.services.common import require_student


class AssessmentService:
    def list_assessments(
        self, session: Session, student_id: int, *, upcoming_only: bool = False
    ) -> list[dict]:
        require_student(session, student_id)
        statement = (
            select(Assessment)
            .join(Course)
            .join(Semester)
            .where(Semester.student_id == student_id)
            .options(
                selectinload(Assessment.course),
                selectinload(Assessment.topic_links).selectinload(AssessmentTopic.topic),
            )
            .order_by(Assessment.scheduled_at)
        )
        if upcoming_only:
            statement = statement.where(
                Assessment.status == AssessmentStatus.PLANNED,
                Assessment.scheduled_at.is_not(None),
                Assessment.scheduled_at >= datetime.now().astimezone(),
            )
        return [self._serialize_assessment(item) for item in session.scalars(statement).all()]

    def list_assignments(
        self, session: Session, student_id: int, *, pending_only: bool = False
    ) -> list[dict]:
        require_student(session, student_id)
        statement = (
            select(Assignment)
            .join(Course)
            .join(Semester)
            .where(Semester.student_id == student_id)
            .options(selectinload(Assignment.course))
            .order_by(Assignment.due_at)
        )
        if pending_only:
            statement = statement.where(Assignment.is_submitted.is_(False))
        return [self._serialize_assignment(item) for item in session.scalars(statement).all()]

    @staticmethod
    def _serialize_assessment(assessment: Assessment) -> dict:
        return {
            "id": assessment.id,
            "course_id": assessment.course_id,
            "course_code": assessment.course.code,
            "course_name": assessment.course.name,
            "title": assessment.title,
            "assessment_type": assessment.assessment_type.value,
            "status": assessment.status.value,
            "scheduled_at": assessment.scheduled_at,
            "maximum_marks": float(assessment.maximum_marks)
            if assessment.maximum_marks is not None
            else None,
            "earned_marks": float(assessment.earned_marks)
            if assessment.earned_marks is not None
            else None,
            "weightage": float(assessment.weightage) if assessment.weightage is not None else None,
            "topics": [link.topic.title for link in assessment.topic_links],
        }

    @staticmethod
    def _serialize_assignment(assignment: Assignment) -> dict:
        return {
            "id": assignment.id,
            "course_id": assignment.course_id,
            "course_code": assignment.course.code,
            "course_name": assignment.course.name,
            "title": assignment.title,
            "description": assignment.description,
            "due_at": assignment.due_at,
            "submitted_at": assignment.submitted_at,
            "maximum_marks": float(assignment.maximum_marks)
            if assignment.maximum_marks is not None
            else None,
            "earned_marks": float(assignment.earned_marks)
            if assignment.earned_marks is not None
            else None,
            "is_submitted": assignment.is_submitted,
        }


assessment_service = AssessmentService()

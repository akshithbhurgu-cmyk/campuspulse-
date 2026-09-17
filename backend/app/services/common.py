from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Student


class StudentNotFoundError(LookupError):
    pass


def require_student(session: Session, student_id: int) -> Student:
    student = session.scalar(select(Student).where(Student.id == student_id))
    if student is None:
        raise StudentNotFoundError(f"Student {student_id} was not found.")
    return student


def percentage(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) * 100 / float(denominator), 2)


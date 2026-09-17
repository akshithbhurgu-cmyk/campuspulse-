from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Attendance, Course, Semester
from app.engines.attendance import AttendanceEngine
from app.services.common import percentage, require_student


class AttendanceNotFoundError(LookupError):
    pass


class AttendanceService:
    def list_attendance(self, session: Session, student_id: int) -> list[dict]:
        require_student(session, student_id)
        records = session.scalars(
            select(Attendance)
            .join(Course)
            .join(Semester)
            .where(Semester.student_id == student_id)
            .options(selectinload(Attendance.course))
            .order_by(Course.code)
        ).all()
        return [self._serialize(record) for record in records]

    def get_attendance(self, session: Session, student_id: int, course_id: int) -> dict:
        return self._serialize(self._get_record(session, student_id, course_id))

    def get_impact(self, session: Session, student_id: int, course_id: int) -> dict:
        record = self._get_record(session, student_id, course_id)
        impact = AttendanceEngine.calculate(
            record.attended_classes,
            record.conducted_classes,
            float(record.target_percentage),
        )
        return {
            **self._serialize(record),
            "if_next_attended_percentage": impact.if_next_attended_percentage,
            "if_next_missed_percentage": impact.if_next_missed_percentage,
            "safe_skips": impact.safe_skips,
            "recovery_classes": impact.recovery_classes,
        }

    @staticmethod
    def _get_record(session: Session, student_id: int, course_id: int) -> Attendance:
        record = session.scalar(
            select(Attendance)
            .join(Course)
            .join(Semester)
            .where(Attendance.course_id == course_id, Semester.student_id == student_id)
            .options(selectinload(Attendance.course))
        )
        if record is None:
            raise AttendanceNotFoundError(f"Attendance for course {course_id} was not found.")
        return record

    @staticmethod
    def _serialize(record: Attendance) -> dict:
        return {
            "course_id": record.course_id,
            "course_code": record.course.code,
            "course_name": record.course.name,
            "attended_classes": record.attended_classes,
            "conducted_classes": record.conducted_classes,
            "target_percentage": float(record.target_percentage),
            "attendance_percentage": percentage(record.attended_classes, record.conducted_classes),
        }


attendance_service = AttendanceService()

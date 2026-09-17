from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Course, CourseUnit, Semester, StudyProgress, Topic
from app.services.common import percentage, require_student


class CourseNotFoundError(LookupError):
    pass


class TopicNotFoundError(LookupError):
    pass


class CourseService:
    def list_courses(self, session: Session, student_id: int) -> list[dict]:
        require_student(session, student_id)
        courses = session.scalars(
            select(Course)
            .join(Semester)
            .where(Semester.student_id == student_id)
            .options(selectinload(Course.attendance), selectinload(Course.units).selectinload(CourseUnit.topics))
            .order_by(Course.code)
        ).all()
        progress = self._progress_by_topic(session, student_id)
        return [self._summary(course, progress) for course in courses]

    def get_course(self, session: Session, student_id: int, course_id: int) -> dict:
        course = self._get_course(session, student_id, course_id)
        progress = self._progress_by_topic(session, student_id)
        return {**self._summary(course, progress), "units": self._units(course, progress)}

    def get_preparation(self, session: Session, student_id: int) -> list[dict]:
        require_student(session, student_id)
        courses = session.scalars(
            select(Course)
            .join(Semester)
            .where(Semester.student_id == student_id)
            .options(selectinload(Course.units).selectinload(CourseUnit.topics))
            .order_by(Course.code)
        ).all()
        progress = self._progress_by_topic(session, student_id)
        return [
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "completion_percentage": self._completion_for_course(course, progress),
                "units": self._units(course, progress),
            }
            for course in courses
        ]

    def update_topic_progress(
        self, session: Session, student_id: int, topic_id: int, completion_percentage: float
    ) -> dict:
        require_student(session, student_id)
        topic = session.scalar(
            select(Topic)
            .join(CourseUnit)
            .join(Course)
            .join(Semester)
            .where(Topic.id == topic_id, Semester.student_id == student_id)
        )
        if topic is None:
            raise TopicNotFoundError(f"Topic {topic_id} was not found for this student.")

        progress = session.scalar(
            select(StudyProgress).where(
                StudyProgress.student_id == student_id, StudyProgress.topic_id == topic_id
            )
        )
        if progress is None:
            progress = StudyProgress(
                student_id=student_id,
                topic_id=topic_id,
                completion_percentage=completion_percentage,
            )
            session.add(progress)
        else:
            progress.completion_percentage = completion_percentage
        session.commit()
        session.refresh(progress)
        return {
            "id": topic.id,
            "title": topic.title,
            "completion_percentage": float(progress.completion_percentage),
        }

    @staticmethod
    def _progress_by_topic(session: Session, student_id: int) -> dict[int, float]:
        return {
            topic_id: float(completion)
            for topic_id, completion in session.execute(
                select(StudyProgress.topic_id, StudyProgress.completion_percentage).where(
                    StudyProgress.student_id == student_id
                )
            )
        }

    def _get_course(self, session: Session, student_id: int, course_id: int) -> Course:
        course = session.scalar(
            select(Course)
            .join(Semester)
            .where(Course.id == course_id, Semester.student_id == student_id)
            .options(selectinload(Course.attendance), selectinload(Course.units).selectinload(CourseUnit.topics))
        )
        if course is None:
            raise CourseNotFoundError(f"Course {course_id} was not found for this student.")
        return course

    def _summary(self, course: Course, progress: dict[int, float]) -> dict:
        attendance_percentage = (
            percentage(course.attendance.attended_classes, course.attendance.conducted_classes)
            if course.attendance
            else None
        )
        return {
            "id": course.id,
            "code": course.code,
            "name": course.name,
            "kind": course.kind.value,
            "credits": float(course.credits) if course.credits is not None else None,
            "faculty_name": course.faculty_name,
            "attendance_percentage": attendance_percentage,
            "preparation_percentage": self._completion_for_course(course, progress),
        }

    def _completion_for_course(self, course: Course, progress: dict[int, float]) -> float:
        topic_values = [
            progress.get(topic.id, 0.0) for unit in course.units for topic in unit.topics
        ]
        return round(sum(topic_values) / len(topic_values), 2) if topic_values else 0.0

    @staticmethod
    def _units(course: Course, progress: dict[int, float]) -> list[dict]:
        return [
            {
                "id": unit.id,
                "sequence": unit.sequence,
                "title": unit.title,
                "topics": [
                    {
                        "id": topic.id,
                        "title": topic.title,
                        "completion_percentage": progress.get(topic.id, 0.0),
                    }
                    for topic in sorted(unit.topics, key=lambda item: item.sequence)
                ],
            }
            for unit in sorted(course.units, key=lambda item: item.sequence)
        ]


course_service = CourseService()

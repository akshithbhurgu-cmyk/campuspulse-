"""LangChain adapters for the read-only subset of Phase 9 tools."""
import json
from datetime import date, datetime, time
from decimal import Decimal

from langchain_core.tools import BaseTool, tool

from app.tools.campuspulse import (
    AssessmentListInput, AssignmentListInput, CampusPulseTools, CourseInput, StudentInput,
)


def _json(value: object) -> str:
    def default(item: object) -> str:
        if isinstance(item, (datetime, date, time, Decimal)):
            return item.isoformat()
        return str(item)
    return json.dumps(value, default=default, ensure_ascii=False)


def build_read_tools(tools: CampusPulseTools, student_id: int) -> list[BaseTool]:
    """Expose factual reads only; Phase 10 must not alter a student's data."""
    @tool
    def get_courses() -> str:
        """Get the student's courses with attendance and preparation summaries."""
        return _json(tools.courses(StudentInput(student_id=student_id)))

    @tool
    def get_course_detail(course_id: int) -> str:
        """Get a course syllabus, units, topics, attendance, and preparation."""
        return _json(tools.course(CourseInput(student_id=student_id, course_id=course_id)))

    @tool
    def get_attendance() -> str:
        """Get attendance counts, percentages, and targets for every course."""
        return _json(tools.attendance(StudentInput(student_id=student_id)))

    @tool
    def get_attendance_impact(course_id: int) -> str:
        """Calculate safe skips, recovery classes, and the effect of attending or missing the next class."""
        return _json(tools.attendance_impact(CourseInput(student_id=student_id, course_id=course_id)))

    @tool
    def get_upcoming_assessments() -> str:
        """Get planned assessments with dates, marks, weightage, and linked topics."""
        return _json(tools.assessments(AssessmentListInput(student_id=student_id, upcoming_only=True)))

    @tool
    def get_pending_assignments() -> str:
        """Get pending assignments and their due dates."""
        return _json(tools.assignments(AssignmentListInput(student_id=student_id, pending_only=True)))

    @tool
    def get_calendar() -> str:
        """Get classes, academic calendar events, and personal events."""
        return _json(tools.calendar(StudentInput(student_id=student_id)))

    @tool
    def get_preparation() -> str:
        """Get course and topic-level preparation percentages."""
        return _json(tools.preparation(StudentInput(student_id=student_id)))

    @tool
    def get_dashboard() -> str:
        """Get the deterministic dashboard: next class, priorities, risks, and today's plan preview."""
        return _json(tools.dashboard(StudentInput(student_id=student_id)))

    return [get_courses, get_course_detail, get_attendance, get_attendance_impact,
            get_upcoming_assessments, get_pending_assignments, get_calendar,
            get_preparation, get_dashboard]

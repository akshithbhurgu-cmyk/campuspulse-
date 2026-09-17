from enum import Enum


class CourseKind(str, Enum):
    THEORY = "THEORY"
    LAB = "LAB"
    ELECTIVE = "ELECTIVE"
    ACTIVITY = "ACTIVITY"


class TimetableSessionKind(str, Enum):
    LECTURE = "LECTURE"
    LAB = "LAB"
    TUTORIAL = "TUTORIAL"
    EXAM = "EXAM"
    OTHER = "OTHER"


class AssessmentType(str, Enum):
    MID = "MID"
    SLIP_TEST = "SLIP_TEST"
    ASSIGNMENT = "ASSIGNMENT"
    SKILL_TEST = "SKILL_TEST"
    DAY_TO_DAY = "DAY_TO_DAY"
    CONTINUOUS_ASSESSMENT = "CONTINUOUS_ASSESSMENT"
    LAB_TEST = "LAB_TEST"
    PRACTICAL = "PRACTICAL"


class AssessmentStatus(str, Enum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CalendarEventType(str, Enum):
    INSTRUCTION = "INSTRUCTION"
    HOLIDAY = "HOLIDAY"
    EXAM = "EXAM"
    DEADLINE = "DEADLINE"
    EVENT = "EVENT"


class PersonalEventType(str, Enum):
    FIXED = "FIXED"
    PERSONAL = "PERSONAL"
    TRAVEL = "TRAVEL"
    HEALTH = "HEALTH"
    OTHER = "OTHER"


class AvailabilityBlockType(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    LOCKED = "LOCKED"


class AnnouncementSource(str, Enum):
    NOTICE_BOARD = "NOTICE_BOARD"
    WHATSAPP = "WHATSAPP"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"
    OTHER = "OTHER"


class RiskType(str, Enum):
    ATTENDANCE = "ATTENDANCE"
    DEADLINE = "DEADLINE"
    PREPARATION = "PREPARATION"
    PERFORMANCE = "PERFORMANCE"
    WORKLOAD = "WORKLOAD"
    CONFLICT = "CONFLICT"
    MISSED_TASK = "MISSED_TASK"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PriorityType(str, Enum):
    ASSESSMENT = "ASSESSMENT"
    ASSIGNMENT = "ASSIGNMENT"
    ATTENDANCE = "ATTENDANCE"
    PREPARATION = "PREPARATION"
    OTHER = "OTHER"


class StudyPlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class StudySessionStatus(str, Enum):
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    MOVED = "MOVED"


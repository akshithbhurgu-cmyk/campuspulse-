"""Create the synthetic Semester 5 scenario used in Phase 3 development."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicCalendarEvent,
    Announcement,
    Assessment,
    AssessmentTopic,
    Assignment,
    Attendance,
    AvailabilityBlock,
    Course,
    CourseUnit,
    PersonalEvent,
    Semester,
    Student,
    StudyProgress,
    TimetableEntry,
    Topic,
)
from app.db.models.enums import (
    AnnouncementSource,
    AssessmentStatus,
    AssessmentType,
    AvailabilityBlockType,
    CalendarEventType,
    CourseKind,
    PersonalEventType,
    TimetableSessionKind,
)
from app.db.session import SessionLocal

SYNTHETIC_STUDENT_EMAIL = "student@campuspulse.local"

COURSE_CATALOG: tuple[tuple[str, str, CourseKind, str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    (
        "DL",
        "Deep Learning",
        CourseKind.THEORY,
        "3.0",
        (
            ("Neural Network Foundations", ("Neural Networks", "Activation Functions", "Backpropagation", "Optimization")),
            ("Convolutional Neural Networks", ("CNN", "Padding", "Pooling", "LeNet", "AlexNet", "VGGNet", "ResNet")),
            ("Modern Deep Learning", ("Transfer Learning", "RNN", "LSTM")),
        ),
    ),
    (
        "EWP",
        "Essentials of Web Programming",
        CourseKind.THEORY,
        "3.0",
        (
            ("Web Foundations", ("HTML5", "CSS3", "JavaScript", "DOM")),
            ("Dynamic Web Applications", ("Forms", "PHP", "Sessions", "Database Connectivity")),
        ),
    ),
    (
        "FOS",
        "Foundations of Operating Systems",
        CourseKind.THEORY,
        "3.0",
        (
            ("Processes and Scheduling", ("Processes", "Threads", "CPU Scheduling", "Synchronization")),
            ("Memory and Storage", ("Paging", "Virtual Memory", "File Systems", "Deadlocks")),
        ),
    ),
    (
        "ENVM",
        "Entrepreneurship and New Venture Management",
        CourseKind.THEORY,
        "2.0",
        (
            ("Entrepreneurial Foundations", ("Entrepreneurial Mindset", "Opportunity Recognition", "Business Models")),
            ("Venture Planning", ("Market Research", "Finance Basics", "Pitch Deck")),
        ),
    ),
    (
        "PSE1",
        "Problem Solving in Engineering – I",
        CourseKind.THEORY,
        "2.0",
        (
            ("Problem Solving", ("Problem Decomposition", "Algorithms", "Pseudocode", "Flowcharts")),
            ("Programming Patterns", ("Arrays", "Strings", "Recursion", "Complexity")),
        ),
    ),
    (
        "QALR2",
        "QALR – II",
        CourseKind.THEORY,
        "2.0",
        (
            ("Quantitative Reasoning", ("Percentages", "Ratios", "Time and Work", "Data Interpretation")),
            ("Logical Reasoning", ("Number Series", "Coding and Decoding", "Syllogisms", "Puzzles")),
        ),
    ),
    (
        "FSDJ",
        "Full Stack Development using Java",
        CourseKind.THEORY,
        "3.0",
        (
            ("Java Core", ("OOP", "Collections", "Exception Handling", "JDBC")),
            ("Java Web Development", ("Servlets", "JSP", "REST APIs", "Spring Boot")),
        ),
    ),
    (
        "EWPL",
        "EWP Lab",
        CourseKind.LAB,
        "1.5",
        (
            ("Web Design Exercises", ("Semantic Pages", "Responsive Layouts", "JavaScript Validation")),
            ("Dynamic Web Exercises", ("Form Handling", "Session Management", "Database CRUD")),
        ),
    ),
    (
        "DLL",
        "Deep Learning Lab",
        CourseKind.LAB,
        "1.5",
        (
            ("Neural Network Experiments", ("Tensor Operations", "Training Loop", "Activation Comparison")),
            ("CNN Experiments", ("Image Classification", "CNN Tuning", "Transfer Learning Lab")),
        ),
    ),
)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


def add_timetable_entry(
    session: Session,
    semester: Semester,
    courses: dict[str, Course],
    course_code: str,
    day_of_week: int,
    start: time,
    end: time,
    kind: TimetableSessionKind,
    location: str,
) -> None:
    session.add(
        TimetableEntry(
            semester=semester,
            course=courses[course_code],
            day_of_week=day_of_week,
            start_time=start,
            end_time=end,
            session_kind=kind,
            location=location,
        )
    )


def seed_synthetic_semester(session: Session) -> bool:
    """Seed one coherent Semester 5 world and return whether it was created."""
    if session.scalar(select(Student.id).where(Student.email == SYNTHETIC_STUDENT_EMAIL)):
        return False

    today = date.today()
    student = Student(
        full_name="Aarav Rao",
        email=SYNTHETIC_STUDENT_EMAIL,
        roll_number="CP-S5-001",
    )
    semester = Semester(
        student=student,
        number=5,
        academic_year="2026–27",
        term="Semester 5",
        starts_on=today - timedelta(days=28),
        ends_on=today + timedelta(days=112),
    )
    session.add_all((student, semester))

    courses: dict[str, Course] = {}
    topics: dict[tuple[str, str], Topic] = {}
    for code, name, kind, credits, units in COURSE_CATALOG:
        course = Course(
            semester=semester,
            code=code,
            name=name,
            kind=kind,
            credits=Decimal(credits),
            faculty_name=f"{code} Faculty",
        )
        courses[code] = course
        for unit_sequence, (unit_title, topic_titles) in enumerate(units, start=1):
            unit = CourseUnit(course=course, sequence=unit_sequence, title=unit_title)
            for topic_sequence, topic_title in enumerate(topic_titles, start=1):
                topic = Topic(unit=unit, sequence=topic_sequence, title=topic_title)
                topics[(code, topic_title)] = topic

    session.add_all(courses.values())

    attendance = {
        "DL": (35, 40),
        "EWP": (34, 39),
        "FOS": (28, 42),
        "ENVM": (31, 36),
        "PSE1": (33, 38),
        "QALR2": (29, 37),
        "FSDJ": (32, 39),
        "EWPL": (18, 20),
        "DLL": (17, 20),
    }
    for code, (attended, conducted) in attendance.items():
        session.add(
            Attendance(
                course=courses[code],
                attended_classes=attended,
                conducted_classes=conducted,
                target_percentage=Decimal("75.00"),
            )
        )

    timetable = (
        ("DL", 0, time(9), time(9, 55), TimetableSessionKind.LECTURE, "C-201"),
        ("EWP", 0, time(10), time(10, 55), TimetableSessionKind.LECTURE, "C-202"),
        ("FOS", 0, time(11), time(11, 55), TimetableSessionKind.LECTURE, "C-203"),
        ("QALR2", 0, time(14), time(14, 55), TimetableSessionKind.LECTURE, "C-204"),
        ("DLL", 1, time(9), time(11, 40), TimetableSessionKind.LAB, "DL Lab"),
        ("PSE1", 1, time(13), time(13, 55), TimetableSessionKind.LECTURE, "C-205"),
        ("FSDJ", 2, time(9), time(9, 55), TimetableSessionKind.LECTURE, "C-206"),
        ("ENVM", 2, time(10), time(10, 55), TimetableSessionKind.LECTURE, "C-207"),
        ("DL", 2, time(11), time(11, 55), TimetableSessionKind.LECTURE, "C-201"),
        ("EWPL", 3, time(9), time(11, 40), TimetableSessionKind.LAB, "Web Lab"),
        ("FOS", 3, time(13), time(13, 55), TimetableSessionKind.LECTURE, "C-203"),
        ("EWP", 4, time(9), time(9, 55), TimetableSessionKind.LECTURE, "C-202"),
        ("FSDJ", 4, time(10), time(10, 55), TimetableSessionKind.LECTURE, "C-206"),
        ("QALR2", 4, time(11), time(11, 55), TimetableSessionKind.LECTURE, "C-204"),
    )
    for entry in timetable:
        add_timetable_entry(session, semester, courses, *entry)

    dl_slip_test = Assessment(
        course=courses["DL"],
        title="CNN Architecture Slip Test",
        assessment_type=AssessmentType.SLIP_TEST,
        status=AssessmentStatus.PLANNED,
        scheduled_at=at(today + timedelta(days=2), 10),
        maximum_marks=Decimal("10.00"),
        weightage=Decimal("10.00"),
        notes="Covers CNN, Pooling, VGGNet and ResNet.",
    )
    dl_slip_test.topic_links = [
        AssessmentTopic(topic=topics[("DL", name)])
        for name in ("CNN", "Pooling", "VGGNet", "ResNet")
    ]
    session.add_all(
        (
            dl_slip_test,
            Assessment(
                course=courses["DL"],
                title="MID 1",
                assessment_type=AssessmentType.MID,
                status=AssessmentStatus.COMPLETED,
                scheduled_at=at(today - timedelta(days=14), 10),
                maximum_marks=Decimal("20.00"),
                earned_marks=Decimal("13.00"),
                weightage=Decimal("20.00"),
            ),
            Assessment(
                course=courses["FSDJ"],
                title="Java Skill Test",
                assessment_type=AssessmentType.SKILL_TEST,
                status=AssessmentStatus.PLANNED,
                scheduled_at=at(today + timedelta(days=6), 14),
                maximum_marks=Decimal("20.00"),
                weightage=Decimal("15.00"),
            ),
            Assessment(
                course=courses["EWP"],
                title="MID 1",
                assessment_type=AssessmentType.MID,
                status=AssessmentStatus.COMPLETED,
                scheduled_at=at(today - timedelta(days=12), 14),
                maximum_marks=Decimal("20.00"),
                earned_marks=Decimal("16.00"),
                weightage=Decimal("20.00"),
            ),
            Assessment(
                course=courses["FOS"],
                title="MID 1",
                assessment_type=AssessmentType.MID,
                status=AssessmentStatus.COMPLETED,
                scheduled_at=at(today - timedelta(days=10), 10),
                maximum_marks=Decimal("20.00"),
                earned_marks=Decimal("11.00"),
                weightage=Decimal("20.00"),
            ),
            Assessment(
                course=courses["EWPL"],
                title="Web Lab Practical",
                assessment_type=AssessmentType.PRACTICAL,
                status=AssessmentStatus.PLANNED,
                scheduled_at=at(today + timedelta(days=11), 9),
                maximum_marks=Decimal("30.00"),
                weightage=Decimal("25.00"),
            ),
        )
    )
    session.add_all(
        (
            Assignment(
                course=courses["EWP"],
                title="Responsive Portfolio Website",
                description="Build a responsive portfolio and submit the source archive.",
                due_at=at(today + timedelta(days=1), 23, 59),
                maximum_marks=Decimal("10.00"),
            ),
            Assignment(
                course=courses["FOS"],
                title="CPU Scheduling Analysis",
                description="Compare FCFS, SJF and Round Robin for the supplied process set.",
                due_at=at(today + timedelta(days=4), 17),
                maximum_marks=Decimal("10.00"),
            ),
            Assignment(
                course=courses["ENVM"],
                title="Business Model Canvas",
                description="Prepare a one-page business model canvas for a campus-focused idea.",
                due_at=at(today + timedelta(days=8), 17),
                maximum_marks=Decimal("10.00"),
            ),
        )
    )

    session.add_all(
        (
            AcademicCalendarEvent(
                semester=semester,
                title="Instruction Spell II",
                event_type=CalendarEventType.INSTRUCTION,
                starts_at=at(today - timedelta(days=28), 9),
                ends_at=at(today + timedelta(days=35), 17),
                is_all_day=True,
            ),
            AcademicCalendarEvent(
                semester=semester,
                title="Campus Holiday",
                event_type=CalendarEventType.HOLIDAY,
                starts_at=at(today + timedelta(days=7), 0),
                ends_at=at(today + timedelta(days=7), 23, 59),
                is_all_day=True,
            ),
            AcademicCalendarEvent(
                semester=semester,
                title="MID II Examination Window",
                event_type=CalendarEventType.EXAM,
                starts_at=at(today + timedelta(days=28), 9),
                ends_at=at(today + timedelta(days=33), 17),
                is_all_day=True,
            ),
        )
    )
    session.add_all(
        (
            PersonalEvent(
                student=student,
                title="Gym",
                event_type=PersonalEventType.PERSONAL,
                starts_at=at(today, 18),
                ends_at=at(today, 19),
            ),
            PersonalEvent(
                student=student,
                title="Dinner with family",
                event_type=PersonalEventType.FIXED,
                starts_at=at(today, 20),
                ends_at=at(today, 21),
            ),
            PersonalEvent(
                student=student,
                title="Travel home",
                event_type=PersonalEventType.TRAVEL,
                starts_at=at(today + timedelta(days=1), 17),
                ends_at=at(today + timedelta(days=1), 18),
            ),
        )
    )
    session.add_all(
        (
            AvailabilityBlock(
                student=student,
                block_type=AvailabilityBlockType.AVAILABLE,
                day_of_week=0,
                start_time=time(19),
                end_time=time(22),
                is_recurring=True,
                label="Monday evening study slot",
            ),
            AvailabilityBlock(
                student=student,
                block_type=AvailabilityBlockType.AVAILABLE,
                day_of_week=1,
                start_time=time(18),
                end_time=time(22),
                is_recurring=True,
                label="Tuesday evening study slot",
            ),
            AvailabilityBlock(
                student=student,
                block_type=AvailabilityBlockType.AVAILABLE,
                block_date=today,
                start_time=time(21),
                end_time=time(23),
                is_recurring=False,
                label="Tonight",
            ),
        )
    )

    progress_overrides = {
        ("DL", "CNN"): "70.00",
        ("DL", "Padding"): "80.00",
        ("DL", "Pooling"): "80.00",
        ("DL", "LeNet"): "65.00",
        ("DL", "AlexNet"): "65.00",
        ("DL", "VGGNet"): "45.00",
        ("DL", "ResNet"): "20.00",
        ("DL", "Transfer Learning"): "10.00",
        ("FOS", "CPU Scheduling"): "55.00",
        ("FOS", "Deadlocks"): "30.00",
        ("EWP", "Responsive Layouts"): "80.00",
        ("FSDJ", "Spring Boot"): "25.00",
    }
    for key, topic in topics.items():
        baseline = Decimal("60.00") if key[0] not in {"DL", "FOS"} else Decimal("50.00")
        session.add(
            StudyProgress(
                student=student,
                topic=topic,
                completion_percentage=Decimal(progress_overrides.get(key, str(baseline))),
            )
        )

    session.add_all(
        (
            Announcement(
                semester=semester,
                course=courses["DL"],
                source=AnnouncementSource.FACULTY,
                title="Deep Learning slip test",
                body=(
                    "DL slip test is scheduled in two days. Topics: CNN, Pooling, VGGNet and ResNet."
                ),
            ),
            Announcement(
                semester=semester,
                course=courses["EWP"],
                source=AnnouncementSource.WHATSAPP,
                title="EWP portfolio submission reminder",
                body="Submit the responsive portfolio website by tomorrow night.",
            ),
            Announcement(
                semester=semester,
                source=AnnouncementSource.NOTICE_BOARD,
                title="Campus holiday notice",
                body="The college will remain closed next week for the scheduled campus holiday.",
            ),
        )
    )
    return True


def main() -> None:
    with SessionLocal.begin() as session:
        created = seed_synthetic_semester(session)

    if created:
        print("Synthetic Semester 5 scenario created.")
    else:
        print("Synthetic Semester 5 scenario already exists; no changes made.")


if __name__ == "__main__":
    main()

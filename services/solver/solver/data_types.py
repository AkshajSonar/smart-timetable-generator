"""Plain dataclasses for solver I/O — no SQLAlchemy dependency (NFR-19).

These are the types the solver's model.py and conflict_checker.py operate on.
The API service converts DB rows into these before calling the solver.

Phase 2 additions:
- BatchData: FR-4.1 — batches of a cohort scheduled independently for lab courses.
- batch_id on EligibilityData / AssignmentResult: identifies which batch (or None for
  whole-cohort courses) an assignment belongs to.
- lab_room_count on SolverInput: count of lab-type rooms for H10 check.
- Deferred: FR-4.2 (stable rotation patterns across weeks) — not in Phase 2 scope.
  Logged as explicit deferral to avoid silent gap.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleData:
    """A constraint_rule from the DB mapped for the solver."""
    rule_type: str
    scope: str
    target_id: Optional[str]
    threshold: Optional[float]
    unit: Optional[str]
    polarity: Optional[str]
    weight: Optional[float]


@dataclass
class FacultyData:
    id: str
    workload_cap_week: int
    workload_cap_day: int


@dataclass
class CourseData:
    id: str
    type: str  # core|elective|lab
    hours_per_week: int
    block_size: int = 1
    required_equipment_tags: list[str] = field(default_factory=list)


@dataclass
class CohortData:
    id: str
    name: str


@dataclass
class BatchData:
    """FR-4.1: A split of a cohort for lab scheduling.

    Each batch is treated as an independent scheduling unit with its own
    eligibility entries and its own non-overlapping slot assignments.
    The parent_cohort_id links it back to the full cohort for H2 checking.

    FR-4.2 (stable rotation across weeks) is explicitly deferred — the spec
    requires it but Phase 2 builds single-week scheduling only.
    """
    id: str          # batch UUID (same as DB batch.id)
    label: str       # display label, e.g. "Batch A"
    cohort_id: str   # parent cohort this batch belongs to
    course_id: str   # the lab course this batch is created for


@dataclass
class RoomData:
    id: str
    type: str  # classroom|lab|seminar_hall|auditorium
    capacity: int
    equipment_tags: list[str] = field(default_factory=list)


@dataclass
class EligibilityData:
    faculty_id: str
    course_id: str
    cohort_id: str  # may be a batch_id (str) for batch-level eligibility


@dataclass
class PeriodSlot:
    slot_index: int
    weekday: int
    period_index: int
    start_time: str | None = None
    end_time: str | None = None


@dataclass
class BlockedSlot:
    faculty_id: str
    slot_index: int


@dataclass
class StudentCourseData:
    course_id: str
    cohort_id: str
    batch_id: str | None = None

@dataclass
class StudentData:
    id: str
    courses: list[StudentCourseData]

@dataclass
class ExamSessionData:
    """Pre-processed exam session requirement (room and students are fixed)."""
    id: str
    course_id: str
    cohort_id: str
    room_id: str
    num_students: int  # H13 needs this to enforce room capacity if multiple sessions share a room


@dataclass
class StudentExamData:
    """Pre-processed student assignment to specific exam sessions."""
    id: str
    exam_session_ids: list[str]


@dataclass
class SolverInput:
    faculty: list[FacultyData]
    courses: list[CourseData]
    cohorts: list[CohortData]   # whole-cohort scheduling units
    rooms: list[RoomData]
    eligibility: list[EligibilityData]
    period_slots: list[PeriodSlot]
    blocked_slots: list[BlockedSlot]
    slots_per_day: dict[int, list[int]]  # weekday → [slot_indices]
    num_slots: int
    # H10: count of rooms per type for shared-capacity check
    room_type_counts: dict[str, int] = field(default_factory=dict)  # room_type → count
    batches: list[BatchData] = field(default_factory=list)    # Phase 2: batch scheduling units (empty list = Phase 1 mode)
    students: list[StudentData] = field(default_factory=list) # Phase 3: students and their enrolled courses/batches
    is_exam: bool = False  # Phase 4: flag indicating if this is an exam generation run
    exam_sessions: list[ExamSessionData] = field(default_factory=list) # Phase 4: fixed exam sessions
    students_exams: list[StudentExamData] = field(default_factory=list) # Phase 4: student assignments to exam sessions
    rules: list[RuleData] = field(default_factory=list)
    locked_assignments: list['AssignmentResult'] = field(default_factory=list) # Assignments that must be pinned to their exact slot/room/faculty


@dataclass
class AssignmentResult:
    """A single assignment in the solver's output."""
    faculty_id: str
    course_id: str
    cohort_id: str   # cohort or batch id
    room_id: str
    slot_index: int
    slot_span: int = 1
    batch_id: str | None = None  # non-None when this assignment is for a specific batch


@dataclass
class ExamSessionResult:
    """A single exam session assignment in the solver's output."""
    id: str
    room_id: str
    invigilator_staff_profile_id: str | None
    slot_index: int


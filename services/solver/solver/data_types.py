"""Plain dataclasses for solver I/O — no SQLAlchemy dependency (NFR-19).

These are the types the solver's model.py and conflict_checker.py operate on.
The API service converts DB rows into these before calling the solver.
"""

from dataclasses import dataclass, field


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
class RoomData:
    id: str
    type: str  # classroom|lab|seminar_hall|auditorium
    capacity: int
    equipment_tags: list[str] = field(default_factory=list)


@dataclass
class EligibilityData:
    faculty_id: str
    course_id: str
    cohort_id: str


@dataclass
class PeriodSlot:
    slot_index: int
    weekday: int
    period_index: int


@dataclass
class BlockedSlot:
    faculty_id: str
    slot_index: int


@dataclass
class SolverInput:
    faculty: list[FacultyData]
    courses: list[CourseData]
    cohorts: list[CohortData]
    rooms: list[RoomData]
    eligibility: list[EligibilityData]
    period_slots: list[PeriodSlot]
    blocked_slots: list[BlockedSlot]
    slots_per_day: dict[int, list[int]]  # weekday → [slot_indices]
    num_slots: int


@dataclass
class AssignmentResult:
    """A single assignment in the solver's output."""
    faculty_id: str
    course_id: str
    cohort_id: str
    room_id: str
    slot_index: int
    slot_span: int = 1

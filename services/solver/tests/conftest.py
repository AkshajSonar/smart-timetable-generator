"""Shared test fixtures for solver constraint tests."""

import pytest
from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData, PeriodSlot, BlockedSlot,
)


def make_period_slots(days: int = 5, periods_per_day: int = 6) -> tuple[list[PeriodSlot], dict[int, list[int]], int]:
    """Create a standard week of period slots.

    Returns (period_slots, slots_per_day, num_slots).
    """
    slots = []
    slots_per_day: dict[int, list[int]] = {}
    idx = 0
    for day in range(days):
        slots_per_day[day] = []
        for period in range(periods_per_day):
            slots.append(PeriodSlot(slot_index=idx, weekday=day, period_index=period))
            slots_per_day[day].append(idx)
            idx += 1
    return slots, slots_per_day, idx


def make_simple_input(
    num_faculty: int = 1,
    num_courses: int = 1,
    num_rooms: int = 1,
    hours_per_week: int = 3,
    course_type: str = "core",
    room_type: str = "classroom",
    workload_cap_week: int = 20,
    workload_cap_day: int = 6,
    days: int = 5,
    periods_per_day: int = 6,
    blocked_slots: list[BlockedSlot] | None = None,
) -> SolverInput:
    """Build a minimal SolverInput for testing."""
    faculty = [
        FacultyData(id=f"f{i}", workload_cap_week=workload_cap_week, workload_cap_day=workload_cap_day)
        for i in range(num_faculty)
    ]
    courses = [
        CourseData(id=f"c{i}", type=course_type, hours_per_week=hours_per_week)
        for i in range(num_courses)
    ]
    cohorts = [CohortData(id="k0", name="Cohort A")]
    rooms = [
        RoomData(id=f"r{i}", type=room_type, capacity=40)
        for i in range(num_rooms)
    ]
    # All faculty eligible for all courses in the cohort
    eligibility = [
        EligibilityData(faculty_id=f.id, course_id=c.id, cohort_id="k0")
        for f in faculty for c in courses
    ]
    period_slots, slots_per_day, num_slots = make_period_slots(days, periods_per_day)

    return SolverInput(
        faculty=faculty,
        courses=courses,
        cohorts=cohorts,
        rooms=rooms,
        eligibility=eligibility,
        period_slots=period_slots,
        blocked_slots=blocked_slots or [],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )

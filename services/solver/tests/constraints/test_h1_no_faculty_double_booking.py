"""H1: No faculty double-booked across two cohorts/rooms in the same slot.

Two assertions:
1. Solver output has no H1 violations.
2. Conflict checker flags a manually-corrupted schedule that double-books faculty.
"""

from solver.model import solve
from solver.conflict_checker import check_h1_no_faculty_double_booking, check_all
from solver.data_types import AssignmentResult, SolverInput, FacultyData, CourseData, CohortData, RoomData, EligibilityData, PeriodSlot
from tests.conftest import make_period_slots


def test_solver_satisfies_h1():
    """One faculty, two courses (3h each), 30 slots → solver must not double-book."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[
            CourseData(id="c0", type="core", hours_per_week=3),
            CourseData(id="c1", type="core", hours_per_week=3),
        ],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0"),
            EligibilityData(faculty_id="f0", course_id="c1", cohort_id="k0"),
        ],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is not None, "Solver should find a feasible solution"
    violations = check_h1_no_faculty_double_booking(result)
    assert len(violations) == 0, f"H1 violated: {violations}"


def test_checker_flags_h1_violation():
    """Manually create a schedule where one faculty is in two places at slot 0."""
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=0),
        AssignmentResult(faculty_id="f0", course_id="c1", cohort_id="k0", room_id="r1", slot_index=0),
    ]
    violations = check_h1_no_faculty_double_booking(corrupted)
    assert len(violations) > 0, "Checker should flag H1 double-booking"
    assert all(v.h_code == "H1" for v in violations)

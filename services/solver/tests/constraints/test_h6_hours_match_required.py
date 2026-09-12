"""H6: Scheduled hours/week per (course, cohort) exactly match required hours."""

from solver.model import solve
from solver.conflict_checker import check_h6_hours_match_required
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h6():
    """Course c0 needs 4 hours/week — solver must assign exactly 4."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=4)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is not None
    total_hours = sum(a.slot_span for a in result if a.course_id == "c0" and a.cohort_id == "k0")
    assert total_hours == 4
    violations = check_h6_hours_match_required(result, inp)
    assert len(violations) == 0


def test_checker_flags_h6_violation():
    """Course c0 needs 4 hours but only 2 are assigned."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=4)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=0),
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=1),
    ]
    violations = check_h6_hours_match_required(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H6" for v in violations)

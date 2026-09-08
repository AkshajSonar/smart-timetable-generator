"""H5: Faculty only assigned to (course, cohort) pairs they're eligible for."""

from solver.model import solve
from solver.conflict_checker import check_h5_faculty_eligibility
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h5():
    """f0 eligible for c0 only, f1 for c1 only — solver must respect eligibility."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[
            FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6),
            FacultyData(id="f1", workload_cap_week=20, workload_cap_day=6),
        ],
        courses=[
            CourseData(id="c0", type="core", hours_per_week=3),
            CourseData(id="c1", type="core", hours_per_week=3),
        ],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40), RoomData(id="r1", type="classroom", capacity=40)],
        eligibility=[
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0"),
            EligibilityData(faculty_id="f1", course_id="c1", cohort_id="k0"),
        ],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is not None
    violations = check_h5_faculty_eligibility(result, inp)
    assert len(violations) == 0


def test_checker_flags_h5_violation():
    """Faculty f0 assigned to c1 (not in their eligibility)."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=3), CourseData(id="c1", type="core", hours_per_week=3)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c1", cohort_id="k0", room_id="r0", slot_index=0),
    ]
    violations = check_h5_faculty_eligibility(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H5" for v in violations)

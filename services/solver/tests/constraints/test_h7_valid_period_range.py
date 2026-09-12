"""H7: Slots scheduled only within the valid period range for that day/shift."""

from solver.model import solve
from solver.conflict_checker import check_h7_valid_period_range
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData, PeriodSlot,
)


def test_solver_satisfies_h7():
    """Only 3 valid slots (0,1,2) — solver must not assign outside them."""
    period_slots = [
        PeriodSlot(slot_index=0, weekday=0, period_index=0),
        PeriodSlot(slot_index=1, weekday=0, period_index=1),
        PeriodSlot(slot_index=2, weekday=0, period_index=2),
    ]
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day={0: [0, 1, 2]},
        num_slots=3,
    )
    result = solve(inp)
    assert result is not None
    for a in result:
        assert a.slot_index in {0, 1, 2}, f"H7: slot {a.slot_index} outside valid range"
    violations = check_h7_valid_period_range(result, inp)
    assert len(violations) == 0


def test_checker_flags_h7_violation():
    """Assignment at slot 99 which doesn't exist in period templates."""
    period_slots = [
        PeriodSlot(slot_index=0, weekday=0, period_index=0),
    ]
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=1)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day={0: [0]},
        num_slots=1,
    )
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=99),
    ]
    violations = check_h7_valid_period_range(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H7" for v in violations)

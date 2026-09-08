"""H4: Faculty not scheduled during declared unavailable/admin/reserved blocks."""

from solver.model import solve
from solver.conflict_checker import check_h4_faculty_unavailable_blocks
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData, BlockedSlot,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h4():
    """Faculty f0 blocked at slot 0 — solver must not assign there."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[BlockedSlot(faculty_id="f0", slot_index=0)],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is not None
    for a in result:
        assert a.slot_index != 0, "H4: faculty assigned to blocked slot 0"
    violations = check_h4_faculty_unavailable_blocks(result, inp)
    assert len(violations) == 0


def test_checker_flags_h4_violation():
    """Faculty f0 assigned at blocked slot 0."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="core", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[BlockedSlot(faculty_id="f0", slot_index=0)],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=0),
    ]
    violations = check_h4_faculty_unavailable_blocks(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H4" for v in violations)

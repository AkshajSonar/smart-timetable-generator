"""H8: Faculty weekly/daily workload cap never exceeded."""

from solver.model import solve
from solver.conflict_checker import check_h8_workload_cap
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h8():
    """Faculty cap = 2/day. Two courses × 3h = 6h total. Solver must stay ≤2/day."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=2)],
        courses=[
            CourseData(id="c0", type="core", hours_per_week=3),
            CourseData(id="c1", type="core", hours_per_week=3),
        ],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40), RoomData(id="r1", type="classroom", capacity=40)],
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
    assert result is not None

    # Verify daily cap
    from collections import defaultdict
    daily = defaultdict(int)
    slot_to_day = {ps.slot_index: ps.weekday for ps in period_slots}
    for a in result:
        daily[(a.faculty_id, slot_to_day[a.slot_index])] += 1
    for (f, d), count in daily.items():
        assert count <= 2, f"H8: faculty {f} has {count} periods on day {d}"

    violations = check_h8_workload_cap(result, inp)
    assert len(violations) == 0


def test_checker_flags_h8_violation():
    """Faculty f0 with cap 2/day given 3 assignments on day 0."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=2)],
        courses=[CourseData(id="c0", type="core", hours_per_week=3)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    # Day 0 has slots 0–5. Assign 3 on day 0 → exceeds cap of 2.
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=0),
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=1),
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=2),
    ]
    violations = check_h8_workload_cap(corrupted, inp)
    assert len(violations) > 0
    assert any(v.h_code == "H8" for v in violations)

"""H9: Room type/equipment matches the course's declared requirement."""

from solver.model import solve
from solver.conflict_checker import check_h9_room_type_match
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h9():
    """Lab course + only a lab room → solver assigns to the lab. No lecture room created."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r_lab", type="lab", capacity=30)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is not None
    for a in result:
        assert a.room_id == "r_lab"
    violations = check_h9_room_type_match(result, inp)
    assert len(violations) == 0


def test_solver_infeasible_h9():
    """Lab course but only classroom rooms → solver returns None (infeasible by construction)."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[RoomData(id="r_class", type="classroom", capacity=40)],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    result = solve(inp)
    assert result is None, "Should be infeasible — lab course, no lab room"


def test_checker_flags_h9_violation():
    """Lab course assigned to a classroom room."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=2)],
        cohorts=[CohortData(id="k0", name="A")],
        rooms=[
            RoomData(id="r_class", type="classroom", capacity=40),
            RoomData(id="r_lab", type="lab", capacity=30),
        ],
        eligibility=[EligibilityData(faculty_id="f0", course_id="c0", cohort_id="k0")],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
    )
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r_class", slot_index=0),
    ]
    violations = check_h9_room_type_match(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H9" for v in violations)

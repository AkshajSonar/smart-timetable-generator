"""H3: No room double-booked across two cohorts/batches in the same slot."""

from solver.model import solve
from solver.conflict_checker import check_h3_no_room_double_booking
from solver.data_types import AssignmentResult, SolverInput, FacultyData, CourseData, CohortData, RoomData, EligibilityData
from tests.conftest import make_period_slots


def test_solver_satisfies_h3():
    """Two faculty, two courses, ONE room — solver must stagger, not overlap the room."""
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
        rooms=[RoomData(id="r0", type="classroom", capacity=40)],
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
    violations = check_h3_no_room_double_booking(result)
    assert len(violations) == 0, f"H3 violated: {violations}"


def test_checker_flags_h3_violation():
    """Room r0 assigned to two groups at the same slot."""
    corrupted = [
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", room_id="r0", slot_index=0),
        AssignmentResult(faculty_id="f1", course_id="c1", cohort_id="k1", room_id="r0", slot_index=0),
    ]
    violations = check_h3_no_room_double_booking(corrupted)
    assert len(violations) > 0
    assert all(v.h_code == "H3" for v in violations)

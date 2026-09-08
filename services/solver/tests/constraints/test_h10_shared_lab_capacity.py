"""H10: Shared-resource capacity across batch-splits never exceeded."""

from solver.model import solve
from solver.conflict_checker import check_h10_shared_lab_capacity
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    BatchData, RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_solver_satisfies_h10():
    """1 lab room, 1 lab course with 2 batches. Capacity=1 means they cannot be in parallel."""
    period_slots, slots_per_day, num_slots = make_period_slots(1, 4)
    # H10 needs room_type_counts
    room_type_counts = {"lab": 1}
    
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=1)],
        cohorts=[CohortData(id="k0", name="A")],
        batches=[
            BatchData(id="b0", cohort_id="k0", course_id="c0", label="Batch 1"),
            BatchData(id="b1", cohort_id="k0", course_id="c0", label="Batch 2"),
        ],
        rooms=[RoomData(id="r_lab1", type="lab", capacity=30)],
        eligibility=[
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="b0"),
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="b1"),
        ],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
        room_type_counts=room_type_counts,
    )
    result = solve(inp)
    assert result is not None
    # 2 assignments total
    assert len(result) == 2
    
    # Must be at different slots because capacity is 1
    slot_0 = result[0].slot_index
    slot_1 = result[1].slot_index
    assert slot_0 != slot_1

    violations = check_h10_shared_lab_capacity(result, inp)
    assert len(violations) == 0


def test_solver_infeasible_h10():
    """1 lab room, 2 batches, each requires 4 hours, but only 4 slots total. 
    Total demand = 8 hours. Capacity = 1 room * 4 slots = 4 hours. Infeasible."""
    period_slots, slots_per_day, num_slots = make_period_slots(1, 4)
    room_type_counts = {"lab": 1}
    
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=8)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=4)],
        cohorts=[CohortData(id="k0", name="A")],
        batches=[
            BatchData(id="b0", cohort_id="k0", course_id="c0", label="Batch 1"),
            BatchData(id="b1", cohort_id="k0", course_id="c0", label="Batch 2"),
        ],
        rooms=[RoomData(id="r_lab1", type="lab", capacity=30)],
        eligibility=[
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="b0"),
            EligibilityData(faculty_id="f0", course_id="c0", cohort_id="b1"),
        ],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
        room_type_counts=room_type_counts,
    )
    result = solve(inp)
    assert result is None, "Should be infeasible — more lab demand than lab capacity"


def test_checker_flags_h10_violation():
    """2 batches scheduled in parallel, but capacity is only 1."""
    period_slots, slots_per_day, num_slots = make_period_slots(1, 4)
    room_type_counts = {"lab": 1}
    
    inp = SolverInput(
        faculty=[FacultyData(id="f0", workload_cap_week=20, workload_cap_day=6)],
        courses=[CourseData(id="c0", type="lab", hours_per_week=1)],
        cohorts=[CohortData(id="k0", name="A")],
        batches=[
            BatchData(id="b0", cohort_id="k0", course_id="c0", label="Batch 1"),
            BatchData(id="b1", cohort_id="k0", course_id="c0", label="Batch 2"),
        ],
        rooms=[RoomData(id="r_lab1", type="lab", capacity=30)],
        eligibility=[],
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
        room_type_counts=room_type_counts,
    )
    corrupted = [
        # Both batches at slot 0
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", batch_id="b0", room_id="r_lab1", slot_index=0),
        AssignmentResult(faculty_id="f0", course_id="c0", cohort_id="k0", batch_id="b1", room_id="r_lab1", slot_index=0),
    ]
    violations = check_h10_shared_lab_capacity(corrupted, inp)
    assert len(violations) > 0
    assert all(v.h_code == "H10" for v in violations)

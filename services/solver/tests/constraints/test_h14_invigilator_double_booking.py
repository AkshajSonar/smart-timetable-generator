"""Tests for H14: Invigilator not double-booked; only assigned within availability/workload cap."""

from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData, RoomData,
    PeriodSlot, BlockedSlot, ExamSessionData, ExamSessionResult
)
from solver.model import solve
from solver.conflict_checker import check_h14_invigilator_double_booking

def _base_input() -> SolverInput:
    return SolverInput(
        faculty=[FacultyData(id="f1", workload_cap_week=2, workload_cap_day=2)],
        courses=[CourseData(id="c1", type="core", hours_per_week=1, block_size=1, required_equipment_tags=[])],
        cohorts=[CohortData(id="k1", name="Cohort 1")],
        rooms=[RoomData(id="r1", type="classroom", capacity=30, equipment_tags=[])],
        eligibility=[], # Exam solver ignores eligibility for invigilators
        period_slots=[
            PeriodSlot(slot_index=0, weekday=1, period_index=1),
            PeriodSlot(slot_index=1, weekday=1, period_index=2),
        ],
        blocked_slots=[],
        slots_per_day={1: [0, 1]},
        num_slots=2,
        is_exam=True,
        exam_sessions=[
            ExamSessionData(id="e1", course_id="c1", cohort_id="k1", room_id="r1", num_students=10),
            ExamSessionData(id="e2", course_id="c1", cohort_id="k1", room_id="r1", num_students=10),
        ],
        students_exams=[]
    )

def test_h14_feasible():
    """Assertion 1: Solver satisfies H14 when feasible."""
    inp = _base_input()
    res = solve(inp)
    assert res is not None
    assert len(res) == 2
    
    # Check invigilator assigned to different slots
    slots_used = {r.slot_index for r in res if r.invigilator_staff_profile_id == "f1"}
    assert len(slots_used) == 2
    
    violations = check_h14_invigilator_double_booking(res, inp)
    assert len(violations) == 0

def test_h14_infeasible_double_booking():
    """Assertion 2a: Solver correctly returns INFEASIBLE when double-booking is unavoidable."""
    inp = _base_input()
    inp.period_slots = [PeriodSlot(slot_index=0, weekday=1, period_index=1)]
    inp.slots_per_day = {1: [0]}
    inp.num_slots = 1
    
    # 2 exams, 1 slot, 1 invigilator. Must double book f1.
    res = solve(inp)
    assert res is None

def test_h14_infeasible_blocked_slot():
    """Assertion 2b: Solver returns INFEASIBLE when the only slot is blocked for the invigilator."""
    inp = _base_input()
    inp.exam_sessions.pop() # Only 1 exam
    inp.period_slots = [PeriodSlot(slot_index=0, weekday=1, period_index=1)]
    inp.slots_per_day = {1: [0]}
    inp.num_slots = 1
    
    inp.blocked_slots.append(BlockedSlot(faculty_id="f1", slot_index=0))
    res = solve(inp)
    assert res is None

def test_h14_infeasible_workload_cap():
    """Assertion 2c: Solver returns INFEASIBLE when assigning would exceed workload cap."""
    inp = _base_input()
    inp.faculty[0].workload_cap_week = 1
    res = solve(inp)
    assert res is None

def test_h14_checker_flags_corrupted_case():
    """Assertion 3: Checker flags a manually corrupted solution."""
    inp = _base_input()
    corrupted_assignments = [
        ExamSessionResult(id="e1", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
        ExamSessionResult(id="e2", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
    ]
    violations = check_h14_invigilator_double_booking(corrupted_assignments, inp)
    # Check double booking
    assert any("double-booked" in v.message for v in violations)
    
    # Let's corrupt workload
    inp.faculty[0].workload_cap_week = 1
    corrupted_assignments_workload = [
        ExamSessionResult(id="e1", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
        ExamSessionResult(id="e2", room_id="r1", invigilator_staff_profile_id="f1", slot_index=1),
    ]
    violations_workload = check_h14_invigilator_double_booking(corrupted_assignments_workload, inp)
    assert any("exceeds cap" in v.message for v in violations_workload)

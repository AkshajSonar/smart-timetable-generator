"""Tests for H13: Exam-room seating capacity is never exceeded."""

from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData, RoomData,
    PeriodSlot, ExamSessionData, StudentExamData, ExamSessionResult
)
from solver.model import solve
from solver.conflict_checker import check_h13_exam_room_capacity

def _base_input() -> SolverInput:
    return SolverInput(
        faculty=[FacultyData(id="f1", workload_cap_week=10, workload_cap_day=10)],
        courses=[CourseData(id="c1", type="core", hours_per_week=1, block_size=1, required_equipment_tags=[])],
        cohorts=[CohortData(id="k1", name="Cohort 1")],
        rooms=[RoomData(id="r1", type="classroom", capacity=30, equipment_tags=[])],
        eligibility=[],
        period_slots=[PeriodSlot(slot_index=0, weekday=1, period_index=1)],
        blocked_slots=[],
        slots_per_day={1: [0]},
        num_slots=1,
        is_exam=True,
        exam_sessions=[
            ExamSessionData(id="e1", course_id="c1", cohort_id="k1", room_id="r1", num_students=20),
            ExamSessionData(id="e2", course_id="c1", cohort_id="k1", room_id="r1", num_students=10),
        ],
        students_exams=[]
    )

def test_h13_feasible():
    """Assertion 1: Solver satisfies H13 when feasible."""
    inp = _base_input()
    # Room r1 has capacity 30. e1 (20) + e2 (10) = 30 <= 30. 
    # Both can be scheduled in slot 0 in the same room.
    # Wait, the solver requires an invigilator for each session.
    # We only have f1, but if e1 and e2 are scheduled in the SAME slot, f1 would be double-booked!
    # Let's add another faculty so it doesn't fail on H14.
    inp.faculty.append(FacultyData(id="f2", workload_cap_week=10, workload_cap_day=10))
    
    res = solve(inp)
    assert res is not None
    assert len(res) == 2
    
    violations = check_h13_exam_room_capacity(res, inp)
    assert len(violations) == 0

def test_h13_infeasible():
    """Assertion 2: Solver correctly returns INFEASIBLE when H13 cannot be met."""
    inp = _base_input()
    inp.faculty.append(FacultyData(id="f2", workload_cap_week=10, workload_cap_day=10))
    # Change e2 num_students to 11. Total = 31 > 30.
    inp.exam_sessions[1].num_students = 11
    
    res = solve(inp)
    assert res is None

def test_h13_checker_flags_corrupted_case():
    """Assertion 3: Checker flags a manually corrupted solution."""
    inp = _base_input()
    inp.exam_sessions[1].num_students = 11
    corrupted_assignments = [
        ExamSessionResult(id="e1", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
        ExamSessionResult(id="e2", room_id="r1", invigilator_staff_profile_id="f2", slot_index=0),
    ]
    violations = check_h13_exam_room_capacity(corrupted_assignments, inp)
    assert len(violations) == 1
    assert "Room r1 capacity exceeded at slot 0: used 31, capacity 30" in violations[0].message

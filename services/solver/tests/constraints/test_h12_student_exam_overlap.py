"""Tests for H12: No student has two overlapping exam sessions."""

from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData, RoomData,
    PeriodSlot, ExamSessionData, StudentExamData, ExamSessionResult
)
from solver.model import solve
from solver.conflict_checker import check_h12_student_exam_overlap

def _base_input() -> SolverInput:
    return SolverInput(
        faculty=[FacultyData(id="f1", workload_cap_week=10, workload_cap_day=10)],
        courses=[
            CourseData(id="c1", type="core", hours_per_week=1, block_size=1, required_equipment_tags=[]),
            CourseData(id="c2", type="core", hours_per_week=1, block_size=1, required_equipment_tags=[]),
        ],
        cohorts=[CohortData(id="k1", name="Cohort 1")],
        rooms=[RoomData(id="r1", type="classroom", capacity=30, equipment_tags=[])],
        eligibility=[],
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
            ExamSessionData(id="e2", course_id="c2", cohort_id="k1", room_id="r1", num_students=10),
        ],
        students_exams=[
            StudentExamData(id="s1", exam_session_ids=["e1", "e2"])
        ]
    )

def test_h12_feasible():
    """Assertion 1: Solver satisfies H12 when feasible."""
    inp = _base_input()
    # 2 slots available, 2 exams for the same student. Should be feasible, assigned to different slots.
    res = solve(inp)
    assert res is not None
    assert len(res) == 2
    
    # Check they are in different slots
    slots_used = {r.slot_index for r in res}
    assert len(slots_used) == 2
    
    violations = check_h12_student_exam_overlap(res, inp)
    assert len(violations) == 0

def test_h12_infeasible():
    """Assertion 2: Solver correctly returns INFEASIBLE when H12 cannot be met."""
    inp = _base_input()
    # Restrict to only 1 slot.
    inp.period_slots = [PeriodSlot(slot_index=0, weekday=1, period_index=1)]
    inp.slots_per_day = {1: [0]}
    inp.num_slots = 1
    
    # The student has 2 exams but only 1 slot is available.
    res = solve(inp)
    assert res is None

def test_h12_checker_flags_corrupted_case():
    """Assertion 3: Checker flags a manually corrupted solution."""
    inp = _base_input()
    corrupted_assignments = [
        ExamSessionResult(id="e1", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
        ExamSessionResult(id="e2", room_id="r1", invigilator_staff_profile_id="f1", slot_index=0),
    ]
    violations = check_h12_student_exam_overlap(corrupted_assignments, inp)
    assert len(violations) == 1
    assert "Student s1 has overlapping exams at slot 0" in violations[0].message

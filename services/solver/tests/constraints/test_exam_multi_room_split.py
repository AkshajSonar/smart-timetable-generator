import pytest
from uuid import uuid4
from solver.data_types import (
    SolverInput, ExamSessionData, StudentExamData, RoomData,
    PeriodSlot, FacultyData
)
from solver.model import solve

def test_exam_multi_room_split_feasible():
    """Test that the solver can successfully assign invigilators to an exam split across multiple rooms simultaneously."""
    room1_id = uuid4()
    room2_id = uuid4()
    course_id = uuid4()
    cohort_id = uuid4()
    faculty1_id = uuid4()
    faculty2_id = uuid4()
    session1_id = str(uuid4())
    session2_id = str(uuid4())

    inp = SolverInput(
        is_exam=True,
        slots_per_day={1: [0]},
        num_slots=1,
        faculty=[
            FacultyData(id=faculty1_id, workload_cap_week=20, workload_cap_day=6),
            FacultyData(id=faculty2_id, workload_cap_week=20, workload_cap_day=6)
        ],
        courses=[],
        cohorts=[],
        rooms=[
            RoomData(id=room1_id, type="classroom", capacity=50, equipment_tags=[]),
            RoomData(id=room2_id, type="classroom", capacity=50, equipment_tags=[])
        ],
        period_slots=[
            PeriodSlot(slot_index=0, weekday=1, period_index=1)
        ],
        blocked_slots=[],
        eligibility=[],
        exam_sessions=[
            ExamSessionData(id=session1_id, course_id=course_id, cohort_id=cohort_id, room_id=room1_id, num_students=40),
            ExamSessionData(id=session2_id, course_id=course_id, cohort_id=cohort_id, room_id=room2_id, num_students=40)
        ],
        students_exams=[
            # Students don't matter for invigilator multi-room assignment
        ]
    )

    result = solve(inp)
    assert result is not None, "Solver should find a feasible solution"
    assert len(result) == 2
    
    s1 = next(s for s in result if s.id == session1_id)
    s2 = next(s for s in result if s.id == session2_id)
    
    # Both sessions should be at the same time but in different rooms, with different invigilators
    assert s1.slot_index == s2.slot_index
    assert s1.room_id == room1_id
    assert s2.room_id == room2_id
    assert s1.invigilator_staff_profile_id != s2.invigilator_staff_profile_id

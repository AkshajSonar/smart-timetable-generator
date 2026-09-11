from solver.data_types import (
    SolverInput, FacultyData, CourseData, CohortData, RoomData,
    EligibilityData, PeriodSlot, AssignmentResult
)
from solver.model import solve

def _base_input():
    return SolverInput(
        faculty=[FacultyData("F1", 40, 8)],
        courses=[CourseData("C1", "core", 1)],
        cohorts=[CohortData("K1", "Cohort 1")],
        rooms=[RoomData("R1", "classroom", 30)],
        eligibility=[
            EligibilityData("F1", "C1", "K1")
        ],
        period_slots=[
            PeriodSlot(0, 0, 0),
            PeriodSlot(1, 0, 1)
        ],
        blocked_slots=[],
        slots_per_day={0: [0, 1]},
        num_slots=2,
    )

def test_locked_assignment_forces_slot():
    """Prove that a locked assignment pins the solver to that exact slot/room/faculty,
    even if other solutions exist.
    """
    inp = _base_input()
    
    # Normally, C1 could be placed in slot 0 or 1.
    # We will lock it into slot 1.
    inp.locked_assignments = [
        AssignmentResult(
            faculty_id="F1",
            course_id="C1",
            cohort_id="K1",
            room_id="R1",
            slot_index=1,
        )
    ]
    
    res = solve(inp)
    assert res is not None
    assert len(res) == 1
    assert res[0].slot_index == 1
    
    # If we lock it into an invalid slot (e.g. one where the faculty is blocked)
    # the solver must return None (infeasible).
    inp_invalid = _base_input()
    from solver.data_types import BlockedSlot
    inp_invalid.blocked_slots = [BlockedSlot("F1", 1)]
    inp_invalid.locked_assignments = [
        AssignmentResult(
            faculty_id="F1",
            course_id="C1",
            cohort_id="K1",
            room_id="R1",
            slot_index=1, # But F1 is blocked here!
        )
    ]
    
    res_invalid = solve(inp_invalid)
    assert res_invalid is None

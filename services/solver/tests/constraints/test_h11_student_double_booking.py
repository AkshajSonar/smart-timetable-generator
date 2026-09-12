"""Tests for H11: An individual student's timetable has no double-booking across their course combination."""

import pytest
from solver.data_types import (
    CourseData,
    CohortData,
    BatchData,
    RoomData,
    FacultyData,
    EligibilityData,
    PeriodSlot,
    SolverInput,
    StudentData,
    StudentCourseData,
)
from solver.model import solve
from solver.conflict_checker import check_all

@pytest.fixture
def base_input() -> SolverInput:
    """A simple base scenario for H11 testing.
    2 slots, 1 student, 2 courses, 1 batch.
    """
    return SolverInput(
        faculty=[FacultyData(id="f1", workload_cap_week=10, workload_cap_day=10)],
        courses=[
            CourseData(id="c1", type="core", hours_per_week=1),
            CourseData(id="c2", type="elective", hours_per_week=1),
        ],
        cohorts=[CohortData(id="k1", name="Cohort 1")],
        rooms=[RoomData(id="r1", type="classroom", capacity=30)],
        batches=[
            BatchData(id="b1", label="Batch A", cohort_id="k1", course_id="c1"),
            BatchData(id="b2", label="Batch B", cohort_id="k1", course_id="c1")
        ],
        eligibility=[
            EligibilityData(faculty_id="f1", course_id="c1", cohort_id="b1"),
            EligibilityData(faculty_id="f1", course_id="c1", cohort_id="b2"),
            EligibilityData(faculty_id="f1", course_id="c2", cohort_id="k1"),
        ],
        period_slots=[
            PeriodSlot(slot_index=0, weekday=0, period_index=0),
            PeriodSlot(slot_index=1, weekday=0, period_index=1),
            PeriodSlot(slot_index=2, weekday=0, period_index=2),
        ],
        blocked_slots=[],
        slots_per_day={0: [0, 1, 2]},
        num_slots=3,
        room_type_counts={"classroom": 2},
        students=[
            StudentData(id="s1", courses=[
                StudentCourseData(course_id="c1", cohort_id="k1", batch_id="b1"),
                StudentCourseData(course_id="c2", cohort_id="k1", batch_id=None),
            ])
        ]
    )

def test_h11_satisfies(base_input: SolverInput):
    """Feasible: 2 courses, 2 slots, the student should be scheduled sequentially."""
    results = solve(base_input)
    assert results is not None
    violations = check_all(results, base_input)
    assert len(violations) == 0

def test_h11_infeasible(base_input: SolverInput):
    """Infeasible: 2 courses, 1 slot. The student cannot attend both."""
    base_input.num_slots = 1
    base_input.period_slots = [PeriodSlot(slot_index=0, weekday=0, period_index=0)]
    base_input.slots_per_day = {0: [0]}
    
    results = solve(base_input)
    assert results is None

def test_h11_violation_reporting(base_input: SolverInput):
    """Violation check: manually constructing overlapping assignments for the student."""
    from solver.data_types import AssignmentResult
    
    # Both c1 (in batch b1) and c2 are scheduled at slot 0
    bad_assignments = [
        AssignmentResult(faculty_id="f1", course_id="c1", cohort_id="k1", batch_id="b1", room_id="r1", slot_index=0),
        AssignmentResult(faculty_id="f1", course_id="c2", cohort_id="k1", batch_id=None, room_id="r1", slot_index=0),
    ]
    
    violations = check_all(bad_assignments, base_input)
    # Both are at slot 0, and the student is in b1, so H11 should trigger.
    # Note: H3 (room double booking) might also trigger.
    h11_violations = [v for v in violations if v.h_code == "H11"]
    assert len(h11_violations) > 0
    assert "Student s1 double-booked at slot 0" in h11_violations[0].message

def test_h11_not_overconstrained(base_input: SolverInput):
    """Third assertion specifically requested: an elective that overlaps a batch the student is NOT in must be accepted.
    Student 1 is in b1. 
    Course c1/Batch b2 and Course c2 overlap at slot 0.
    This is completely fine for Student 1 since they don't attend b2.
    """
    from solver.data_types import AssignmentResult
    
    good_assignments = [
        # Student 1 is in b1, which is at slot 1
        AssignmentResult(faculty_id="f1", course_id="c1", cohort_id="k1", batch_id="b1", room_id="r1", slot_index=1),
        # Another batch b2 is at slot 0
        AssignmentResult(faculty_id="f1", course_id="c1", cohort_id="k1", batch_id="b2", room_id="r1", slot_index=0),
        # Student 1's elective c2 is at slot 0
        AssignmentResult(faculty_id="f1", course_id="c2", cohort_id="k1", batch_id=None, room_id="r1", slot_index=0),
    ]
    
    # Wait, H3 room double booking might trigger if r1 is used by both b2 and c2 at slot 0, so let's use a different room
    good_assignments[2].room_id = "r2"
    
    violations = check_all(good_assignments, base_input)
    h11_violations = [v for v in violations if v.h_code == "H11"]
    # Should be valid for H11 because student 1 is in b1 (slot 1) and c2 (slot 0). 
    # They don't care that b2 is at slot 0.
    assert len(h11_violations) == 0

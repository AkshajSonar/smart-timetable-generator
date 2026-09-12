"""FR-6.1: Multi-cohort scale test."""

from solver.model import solve
from solver.conflict_checker import check_all
from solver.data_types import (
    AssignmentResult, SolverInput, FacultyData, CourseData, CohortData,
    BatchData, RoomData, EligibilityData,
)
from tests.conftest import make_period_slots


def test_multicohort_scale_no_violations():
    """Generates a model with 3 cohorts sharing no faculty/rooms to verify zero cross-cohort violations in a single solve."""
    period_slots, slots_per_day, num_slots = make_period_slots(5, 6)
    
    faculty = []
    courses = []
    cohorts = []
    rooms = []
    eligibility = []
    
    for i in range(3):
        cohort_id = f"k{i}"
        faculty_id = f"f{i}"
        course_id = f"c{i}"
        room_id = f"r{i}"
        
        cohorts.append(CohortData(id=cohort_id, name=f"Cohort {i}"))
        faculty.append(FacultyData(id=faculty_id, workload_cap_week=20, workload_cap_day=6))
        courses.append(CourseData(id=course_id, type="core", hours_per_week=5))
        rooms.append(RoomData(id=room_id, type="classroom", capacity=40))
        eligibility.append(EligibilityData(faculty_id=faculty_id, course_id=course_id, cohort_id=cohort_id))

    inp = SolverInput(
        faculty=faculty,
        courses=courses,
        cohorts=cohorts,
        batches=[],
        rooms=rooms,
        eligibility=eligibility,
        period_slots=period_slots,
        blocked_slots=[],
        slots_per_day=slots_per_day,
        num_slots=num_slots,
        room_type_counts={"classroom": 3},
    )
    
    result = solve(inp)
    assert result is not None
    # 3 cohorts * 5 hours = 15 assignments
    assert len(result) == 15
    
    violations = check_all(result, inp)
    assert len(violations) == 0


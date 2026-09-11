import pytest
from solver.data_types import (
    SolverInput, RuleData, FacultyData, CohortData, CourseData
)
from solver.rule_compiler import compile_constraint_rules


def test_h8_override_faculty_max_periods():
    """
    Prove a rule tightens a faculty's cap beyond their default profile cap,
    AND that a faculty with NO matching constraint_rule still uses their
    default unchanged.
    """
    f1 = FacultyData(id="f1", workload_cap_week=20, workload_cap_day=4)
    f2 = FacultyData(id="f2", workload_cap_week=20, workload_cap_day=4)
    
    rules = [
        RuleData(
            rule_type="max_periods_per_day",
            scope="faculty",
            target_id="f1",
            threshold=2.0,
            unit=None,
            polarity=None,
            weight=None
        )
    ]
    
    inp = SolverInput(
        faculty=[f1, f2],
        courses=[], cohorts=[], batches=[], rooms=[], eligibility=[], period_slots=[],
        blocked_slots=[], slots_per_day={}, num_slots=0,
        rules=rules
    )
    
    compiled = compile_constraint_rules(inp)
    
    # f1 is overridden
    assert compiled.faculty_max_periods_day.get("f1") == 2
    # f2 is NOT overridden (dictionary get will return None, fallback handled in model.py)
    assert "f2" not in compiled.faculty_max_periods_day


def test_missing_target_id_graceful_skip():
    """
    Confirm compile_constraint_rules handles missing targets gracefully (skip + log)
    rather than assuming every confirmed rule's target still resolves.
    """
    f1 = FacultyData(id="f1", workload_cap_week=20, workload_cap_day=4)
    
    rules = [
        RuleData(
            rule_type="max_periods_per_day",
            scope="faculty",
            target_id="f_deleted", # No longer in valid_faculty_ids
            threshold=2.0,
            unit=None,
            polarity=None,
            weight=None
        )
    ]
    
    inp = SolverInput(
        faculty=[f1],
        courses=[], cohorts=[], batches=[], rooms=[], eligibility=[], period_slots=[],
        blocked_slots=[], slots_per_day={}, num_slots=0,
        rules=rules
    )
    
    compiled = compile_constraint_rules(inp)
    
    # Should skip "f_deleted" instead of crashing or inserting it
    assert "f_deleted" not in compiled.faculty_max_periods_day


def test_soft_constraint_null_weight_fallback():
    """
    For any S1-S9 mapped rule_type, if weight is NULL, the compiler MUST treat this
    as "use the default weight", never as "weight = 0".
    """
    rules = [
        RuleData(
            rule_type="exam_min_gap_days",
            scope="tenant",
            target_id=None,
            threshold=1.0,
            unit="days",
            polarity=None,
            weight=None # Explicitly NULL
        ),
        RuleData(
            rule_type="elective_no_overlap_core",
            scope="cohort",
            target_id="c1",
            threshold=None,
            unit=None,
            polarity=None,
            weight=None # Explicitly NULL
        )
    ]
    
    inp = SolverInput(
        faculty=[], courses=[], cohorts=[CohortData(id="c1", name="C1")], batches=[], rooms=[], eligibility=[], period_slots=[],
        blocked_slots=[], slots_per_day={}, num_slots=0,
        rules=rules
    )
    
    compiled = compile_constraint_rules(inp)
    
    assert compiled.s9_exam_weight == 50 # Default for S9
    assert compiled.elective_no_overlap_core_weight == 30 # Default for elective_no_overlap_core


def test_all_rule_types_compile_safely():
    """Ensure all other mapped rules compile without crashing and extract fields."""
    rules = [
        RuleData(rule_type="min_gap_between_periods", scope="tenant", target_id=None, threshold=1.0, unit=None, polarity=None, weight=25.0),
        RuleData(rule_type="no_consecutive_same_course", scope="tenant", target_id=None, threshold=None, unit=None, polarity=None, weight=25.0),
        RuleData(rule_type="preferred_time_of_day", scope="tenant", target_id=None, threshold=None, unit="morning", polarity=None, weight=25.0),
        RuleData(rule_type="balance_load_across_week", scope="tenant", target_id=None, threshold=None, unit=None, polarity=None, weight=25.0),
        RuleData(rule_type="room_utilization_priority", scope="tenant", target_id=None, threshold=None, unit=None, polarity=None, weight=25.0),
    ]
    
    inp = SolverInput(
        faculty=[], courses=[], cohorts=[], batches=[], rooms=[], eligibility=[], period_slots=[],
        blocked_slots=[], slots_per_day={}, num_slots=0,
        rules=rules
    )
    
    compiled = compile_constraint_rules(inp)
    
    assert compiled.min_gap_between_periods_weight == 25
    assert compiled.min_gap_between_periods_threshold == 1.0
    assert compiled.no_consecutive_same_course_weight == 25
    assert compiled.preferred_time_of_day_weight == 25
    assert compiled.preferred_time_of_day_unit == "morning"
    assert compiled.balance_load_across_week_weight == 25
    assert compiled.room_utilization_priority_weight == 25

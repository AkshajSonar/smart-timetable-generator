import logging
from dataclasses import dataclass, field
from typing import Any

from solver.data_types import SolverInput

logger = logging.getLogger(__name__)


@dataclass
class CompiledRules:
    """The compiled version of all active constraint_rules for a generation run."""
    
    # H8 overrides mapping staff_profile_id -> max periods
    faculty_max_periods_day: dict[str, int] = field(default_factory=dict)
    faculty_max_periods_week: dict[str, int] = field(default_factory=dict)
    
    # Soft Constraints mapped from rules
    s9_exam_weight: int | None = None
    
    elective_no_overlap_core_weight: int | None = None
    
    min_gap_between_periods_weight: int | None = None
    min_gap_between_periods_threshold: float | None = None
    
    no_consecutive_same_course_weight: int | None = None
    
    # Store list of (target_id, unit, polarity, weight)
    preferred_time_of_day_rules: list[tuple[str | None, str | None, str | None, int | None]] = field(default_factory=list)
    
    balance_load_across_week_weight: int | None = None
    
    room_utilization_priority_weight: int | None = None


def compile_constraint_rules(inp: SolverInput) -> CompiledRules:
    """
    Compile all confirmed RuleData from SolverInput into a CompiledRules object.
    
    Gracefully skips rules whose target_id no longer exists in the input data.
    If a soft constraint rule's weight is NULL, it falls back to a default weight
    instead of 0 or crashing.
    """
    compiled = CompiledRules()
    
    # Known sets of entity IDs for target resolution check
    valid_faculty_ids = {f.id for f in inp.faculty}
    valid_cohort_ids = {c.id for c in inp.cohorts}
    valid_course_ids = {c.id for c in inp.courses}
    
    # Default weights for soft constraints
    DEFAULT_WEIGHTS = {
        "exam_min_gap_days": 50,
        "elective_no_overlap_core": 30,
        "min_gap_between_periods": 20,
        "no_consecutive_same_course": 20,
        "preferred_time_of_day": 20,
        "balance_load_across_week": 20,
        "room_utilization_priority": 10,
    }

    for rule in inp.rules:
        # Graceful skip for deleted target entities
        if rule.target_id:
            if rule.scope == "faculty" and rule.target_id not in valid_faculty_ids:
                logger.warning(f"Skipping rule {rule.rule_type}: target faculty {rule.target_id} not found.")
                continue
            if rule.scope == "cohort" and rule.target_id not in valid_cohort_ids:
                logger.warning(f"Skipping rule {rule.rule_type}: target cohort {rule.target_id} not found.")
                continue
            if rule.scope == "course" and rule.target_id not in valid_course_ids:
                logger.warning(f"Skipping rule {rule.rule_type}: target course {rule.target_id} not found.")
                continue

        # Soft constraint weight fallback
        rule_weight = rule.weight if rule.weight is not None else DEFAULT_WEIGHTS.get(rule.rule_type, 0)
        
        # H8 Overrides
        if rule.rule_type == "max_periods_per_day":
            if rule.scope == "faculty" and rule.target_id and rule.threshold is not None:
                compiled.faculty_max_periods_day[rule.target_id] = int(rule.threshold)
                
        elif rule.rule_type == "max_periods_per_week":
            if rule.scope == "faculty" and rule.target_id and rule.threshold is not None:
                compiled.faculty_max_periods_week[rule.target_id] = int(rule.threshold)
                
        # S9 Override
        elif rule.rule_type == "exam_min_gap_days":
            # Override S9 penalty weight
            compiled.s9_exam_weight = int(rule_weight)
            
        # elective_no_overlap_core
        elif rule.rule_type == "elective_no_overlap_core":
            compiled.elective_no_overlap_core_weight = int(rule_weight)
            
        # min_gap_between_periods
        elif rule.rule_type == "min_gap_between_periods":
            compiled.min_gap_between_periods_weight = int(rule_weight)
            compiled.min_gap_between_periods_threshold = rule.threshold
            
        # no_consecutive_same_course
        elif rule.rule_type == "no_consecutive_same_course":
            compiled.no_consecutive_same_course_weight = int(rule_weight)
            
        # preferred_time_of_day
        elif rule.rule_type == "preferred_time_of_day":
            compiled.preferred_time_of_day_rules.append(
                (rule.target_id, rule.unit, rule.polarity, int(rule_weight))
            )
            
        # balance_load_across_week
        elif rule.rule_type == "balance_load_across_week":
            compiled.balance_load_across_week_weight = int(rule_weight)
            
        # room_utilization_priority
        elif rule.rule_type == "room_utilization_priority":
            compiled.room_utilization_priority_weight = int(rule_weight)
            
    return compiled

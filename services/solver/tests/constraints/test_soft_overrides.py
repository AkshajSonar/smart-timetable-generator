import pytest
from ortools.sat.python import cp_model
from solver.data_types import (
    SolverInput, RuleData, FacultyData, CourseData, CohortData, RoomData,
    EligibilityData, StudentExamData, PeriodSlot
)
from solver.rule_compiler import compile_constraint_rules
from solver.objective import add_s9_exam_spread, add_elective_no_overlap_core_penalty


def test_s9_override_exam_gap():
    """
    Confirm a confirmed exam_min_gap_days rule's weight measurably changes 
    the S9 objective term vs. the Phase 4 default.
    """
    model = cp_model.CpModel()
    
    # 2 slots on 2 different days
    slots_per_day = {0: [0], 1: [1]}
    s1 = StudentExamData(id="s1", exam_session_ids=["e1", "e2"])
    
    # Base input with NO rules -> default weight 50
    inp_default = SolverInput(
        faculty=[], courses=[], cohorts=[], batches=[], rooms=[], eligibility=[],
        period_slots=[], blocked_slots=[], slots_per_day=slots_per_day, num_slots=2,
        students_exams=[s1],
        rules=[]
    )
    compiled_default = compile_constraint_rules(inp_default)
    
    # Create variables forcing the exams to be on consecutive days (slots 0 and 1)
    e1_s0 = model.NewBoolVar("e1_s0")
    e2_s1 = model.NewBoolVar("e2_s1")
    model.Add(e1_s0 == 1)
    model.Add(e2_s1 == 1)
    
    exam_assign = {
        ("e1", "invig1", 0): e1_s0,
        ("e2", "invig1", 1): e2_s1
    }
    
    penalty_default = add_s9_exam_spread(model, exam_assign, inp_default, compiled_default)
    model.Minimize(penalty_default)
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.OPTIMAL
    assert solver.ObjectiveValue() == 50.0 # Default weight is 50
    
    # Now with a rule overriding the weight to 999
    inp_override = SolverInput(
        faculty=[], courses=[], cohorts=[], batches=[], rooms=[], eligibility=[],
        period_slots=[], blocked_slots=[], slots_per_day=slots_per_day, num_slots=2,
        students_exams=[s1],
        rules=[RuleData(rule_type="exam_min_gap_days", scope="tenant", target_id=None, threshold=1, unit="days", polarity=None, weight=999)]
    )
    compiled_override = compile_constraint_rules(inp_override)
    
    model2 = cp_model.CpModel()
    e1_s0_2 = model2.NewBoolVar("e1_s0")
    e2_s1_2 = model2.NewBoolVar("e2_s1")
    model2.Add(e1_s0_2 == 1)
    model2.Add(e2_s1_2 == 1)
    
    exam_assign2 = {
        ("e1", "invig1", 0): e1_s0_2,
        ("e2", "invig1", 1): e2_s1_2
    }
    
    penalty_override = add_s9_exam_spread(model2, exam_assign2, inp_override, compiled_override)
    model2.Minimize(penalty_override)
    
    solver2 = cp_model.CpSolver()
    status2 = solver2.Solve(model2)
    assert status2 == cp_model.OPTIMAL
    assert solver2.ObjectiveValue() == 999.0 # Overridden weight!


def test_elective_no_overlap_core_penalty():
    """
    Confirm the solver's objective value or chosen assignment reflects the penalty 
    when an elective/core-of-same-cohort overlap is avoidable.
    """
    model = cp_model.CpModel()
    
    c_core = CourseData(id="c_core", type="core", hours_per_week=1)
    c_elec = CourseData(id="c_elec", type="elective", hours_per_week=1)
    
    inp_override = SolverInput(
        faculty=[], courses=[c_core, c_elec], cohorts=[CohortData(id="k1", name="K1")], batches=[], rooms=[], eligibility=[],
        period_slots=[], blocked_slots=[], slots_per_day={}, num_slots=1,
        rules=[RuleData(rule_type="elective_no_overlap_core", scope="cohort", target_id="k1", threshold=None, unit=None, polarity=None, weight=777)]
    )
    compiled = compile_constraint_rules(inp_override)
    
    core_s0 = model.NewBoolVar("core_s0")
    elec_s0 = model.NewBoolVar("elec_s0")
    
    # Force overlap in slot 0 for cohort k1
    model.Add(core_s0 == 1)
    model.Add(elec_s0 == 1)
    
    # dict key: (fv, c, k, b, r, sv)
    assign = {
        ("f1", "c_core", "k1", None, "r1", 0): core_s0,
        ("f2", "c_elec", "k1", None, "r2", 0): elec_s0,
    }
    
    penalty = add_elective_no_overlap_core_penalty(model, assign, inp_override, compiled)
    model.Minimize(penalty)
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    assert status == cp_model.OPTIMAL
    assert solver.ObjectiveValue() == 777.0 # Overridden weight


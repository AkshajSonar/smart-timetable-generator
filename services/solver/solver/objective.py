"""Soft constraint objective terms (S1–S9)."""

from ortools.sat.python import cp_model
from solver.data_types import SolverInput

# Named constant for S9 penalty weight.
# We set this to 50 as a moderate penalty: consecutive-day exams are highly undesirable
# for student well-being (S9), but are soft constraints (must not override hard constraints).
S9_CONSECUTIVE_DAY_PENALTY_WEIGHT = 50

def add_s9_exam_spread(
    model: cp_model.CpModel,
    exam_assign: dict,
    inp: SolverInput,
    compiled: 'CompiledRules',
):
    """S9 (exam): Spread a student's exams evenly; minimize consecutive-day exams."""
    # For each student, if they have an exam on day D and day D+1, penalize.
    # To do this, we need boolean variables for 'student has exam on day D'.
    # students_exams -> exam_session_ids
    
    # Pre-compute slots for each day
    # day -> list of slot_indices
    # we can create a boolean variable for each student and day: student_day[student, day]
    
    penalties = []
    exam_assign_map = {}
    for (ev, iv, sv), v in exam_assign.items():
        exam_assign_map.setdefault((ev, sv), []).append(v)

    for student in inp.students_exams:
        student_days = []
        for day, slots in inp.slots_per_day.items():
            day_vars = []
            for e in student.exam_session_ids:
                for s in slots:
                    if (e, s) in exam_assign_map:
                        day_vars.extend(exam_assign_map[(e, s)])
            
            if day_vars:
                has_exam_day = model.NewBoolVar(f"s9_{student.id}_day_{day}")
                model.AddMaxEquality(has_exam_day, day_vars)
                student_days.append((day, has_exam_day))
        
        # Now penalize consecutive days
        # Sort student_days by day index just in case
        student_days.sort(key=lambda x: x[0])
        
        for i in range(len(student_days) - 1):
            day1, var1 = student_days[i]
            day2, var2 = student_days[i+1]
            if day2 == day1 + 1:
                # consecutive days
                consecutive = model.NewBoolVar(f"s9_{student.id}_cons_{day1}_{day2}")
                # consecutive is true if both var1 and var2 are true
                # var1 + var2 - 1 <= consecutive
                # We want to MINIMIZE consecutive, so the solver will push it to 0 if possible
                # consecutive >= var1 + var2 - 1
                model.Add(var1 + var2 - 1 <= consecutive)
                penalties.append(consecutive)
                
    if penalties:
        weight = compiled.s9_exam_weight if compiled.s9_exam_weight is not None else S9_CONSECUTIVE_DAY_PENALTY_WEIGHT
        return sum(penalties) * weight
    return None

def add_elective_no_overlap_core_penalty(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    compiled: 'CompiledRules',
):
    """elective_no_overlap_core: Soft penalty for elective courses overlapping with core courses of the same cohort."""
    # The default weight is 30 unless overridden.
    weight = compiled.elective_no_overlap_core_weight if compiled.elective_no_overlap_core_weight is not None else 30
    
    penalties = []
    
    # Identify electives and core courses
    courses_by_id = {c.id: c for c in inp.courses}
    
    elective_vars_map = {}
    core_vars_map = {}
    
    for (fv, c, k, b, r, sv), v in assign.items():
        course_type = courses_by_id[c].type
        if course_type == "elective":
            elective_vars_map.setdefault((k, sv), []).append(v)
        elif course_type == "core":
            core_vars_map.setdefault((k, sv), []).append(v)
            
    for (k, sv), elective_vars in elective_vars_map.items():
        if (k, sv) in core_vars_map:
            core_vars = core_vars_map[(k, sv)]
            
            # has_elective is true if any elective var is true
            has_elective = model.NewBoolVar(f"has_elective_{k}_{sv}")
            model.AddMaxEquality(has_elective, elective_vars)
            
            # has_core is true if any core var is true
            has_core = model.NewBoolVar(f"has_core_{k}_{sv}")
            model.AddMaxEquality(has_core, core_vars)
            
            # overlap is true if both are true
            overlap = model.NewBoolVar(f"overlap_{k}_{sv}")
            model.Add(has_elective + has_core - 1 <= overlap)
            penalties.append(overlap)
                
    if penalties:
        return sum(penalties) * weight
    return None

def add_s5_minimize_same_course_twice_in_day(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    compiled: 'CompiledRules',
):
    """S5: Minimize same-course-twice-in-one-day unless load requires it."""
    weight = compiled.no_consecutive_same_course_weight if compiled.no_consecutive_same_course_weight is not None else 20
    penalties = []
    
    # Group variables by (c, k, b)
    units_by_day = {}
    for (f, c, k, b, r, s), v in assign.items():
        # Find which day this slot belongs to
        day = next((d for d, slots in inp.slots_per_day.items() if s in slots), None)
        if day is not None:
            units_by_day.setdefault((c, k, b, day), []).append(v)
            
    for (c, k, b, day), vars_in_day in units_by_day.items():
        if len(vars_in_day) > 1:
            # We want to penalize sum(vars_in_day) - 1 if > 0
            # Let excess >= 0
            excess = model.NewIntVar(0, len(vars_in_day), f"s5_excess_{c}_{k}_{b}_{day}")
            model.Add(excess >= sum(vars_in_day) - 1)
            penalties.append(excess)
            
    if penalties:
        return sum(penalties) * weight
    return None

def add_s8_preferred_time_of_day(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    compiled: 'CompiledRules',
):
    """S8: Respect individual faculty time-of-day preferences (soft requires)."""
    day_name_to_int = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    
    penalties = []
    for (target_id, unit, polarity, weight) in compiled.preferred_time_of_day_rules:
        # Hard forbids are handled in model.py. Here we only penalize missed "require" preferences.
        if polarity == "require" and unit and target_id:
            w = weight if weight is not None else 20
            day_int = day_name_to_int.get(unit.lower())
            if day_int is not None and day_int in inp.slots_per_day:
                preferred_slots = set(inp.slots_per_day[day_int])
                
                # We penalize assignments that are NOT in the preferred slots for this faculty.
                for (fv, c, k, b, r, sv), v in assign.items():
                    if fv == target_id and sv not in preferred_slots:
                        # Add a soft penalty for every block scheduled on a non-preferred day
                        penalties.append(v * w)
                        
    if penalties:
        return sum(penalties)
    return None

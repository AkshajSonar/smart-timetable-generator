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
):
    """S9 (exam): Spread a student's exams evenly; minimize consecutive-day exams."""
    # For each student, if they have an exam on day D and day D+1, penalize.
    # To do this, we need boolean variables for 'student has exam on day D'.
    # students_exams -> exam_session_ids
    
    # Pre-compute slots for each day
    # day -> list of slot_indices
    # we can create a boolean variable for each student and day: student_day[student, day]
    
    penalties = []

    for student in inp.students_exams:
        student_days = []
        for day, slots in inp.slots_per_day.items():
            # Does student have an exam on this day?
            # It's true if sum of their exam_assign vars for these slots > 0.
            # But we can just use a boolean: b = model.NewBoolVar(...)
            # model.AddMaxEquality(b, [v for e in student.exam_session_ids for s in slots for (ev, i, sv), v in exam_assign.items() if ev == e and sv == s])
            
            day_vars = []
            for e in student.exam_session_ids:
                for s in slots:
                    # Collect all invigilator combinations for this exam session and slot
                    day_vars.extend([v for (ev, iv, sv), v in exam_assign.items() if ev == e and sv == s])
            
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
        # We add this to the model's objective.
        # Since this is a penalty, we minimize it.
        # Check if the model already has an objective? CP-SAT model.Minimize() overwrites the objective.
        # Currently we only have this one soft constraint.
        # But we can maintain an objective expression.
        # Actually, model.Minimize(sum(penalties) * weight) works.
        model.Minimize(sum(penalties) * S9_CONSECUTIVE_DAY_PENALTY_WEIGHT)

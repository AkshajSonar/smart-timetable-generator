"""CP-SAT solver model — one builder function per H-code (§9.3).

Class Timetable Decision variable: assign[f, c, k, r, s] ∈ {0, 1}
  Staff f teaches course c to cohort k in room r at slot s.

Exam Timetable Decision variable (Phase 4): exam_assign[e, i, s] ∈ {0, 1}
  Exam session e is assigned invigilator i at slot s.
  - Fixed by pre-processing (not solver decisions): room, cohort, course, and exact student seating for the exam session.
  - CP-SAT decisions: Which slot `s` the exam session occurs in, and which invigilator `i` is assigned.

H5 (eligibility) and H9 (room type match) are enforced by construction —
variables are only created for valid (f,c,k) and (c,r) pairs.

H7 (valid period range) is enforced by construction — variables are only
created for slot indices present in the period_slots input.
"""

from ortools.sat.python import cp_model

from solver.data_types import AssignmentResult, ExamSessionResult, SolverInput
from solver.rule_compiler import compile_constraint_rules


# ---------- Room-type matching for H9 (Phase 1 simplification) ----------

_COURSE_TYPE_TO_ROOM_TYPES = {
    "core": {"classroom", "lecture_hall", "seminar_hall"},
    "elective": {"classroom", "lecture_hall", "seminar_hall"},
    "classroom": {"classroom", "lecture_hall", "seminar_hall"},
    "lab": {"lab"},
}


def _room_matches_course(course_type: str, room_type: str) -> bool:
    """Phase 1: coarse type-based matching per §32 #15 note."""
    return room_type in _COURSE_TYPE_TO_ROOM_TYPES.get(course_type, set())


# ---------- Builder functions (one per H-code) ----------


def build_h1_no_faculty_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    faculty_ids: list[str],
    num_slots: int,
    courses_by_id: dict,
):
    """H1: ∀ f,s: Σ_{c,k,b,r} assign[f,c,k,b,r,s'] ≤ 1 for every s' in [s..s+block_size-1]."""
    assign_map: dict[tuple[str, int], list] = {}
    for (fv, c, k, b, r, sv), v in assign.items():
        bs = courses_by_id[c].block_size
        for offset in range(bs):
            assign_map.setdefault((fv, sv + offset), []).append(v)
    for f in faculty_ids:
        for s in range(num_slots):
            vars_at_slot = assign_map.get((f, s), [])
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h2_no_cohort_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    courses_by_id: dict,
):
    """H2: No cohort/batch double-booked across two courses in the same slot (block_size-aware)."""
    batches_by_cohort: dict[str, list[str]] = {}
    for k in inp.cohorts:
        batches_by_cohort[k.id] = []
    for b in inp.batches:
        batches_by_cohort[b.cohort_id].append(b.id)

    assign_map: dict[tuple[str, str | None, int], list] = {}
    for (f, c, kv, b, r, sv), v in assign.items():
        bs = courses_by_id[c].block_size
        for offset in range(bs):
            assign_map.setdefault((kv, b, sv + offset), []).append(v)
    for k in [c.id for c in inp.cohorts]:
        for s in range(inp.num_slots):
            whole_vars = assign_map.get((k, None, s), [])
            batches = batches_by_cohort.get(k, [])
            if not batches:
                if whole_vars:
                    model.Add(sum(whole_vars) <= 1)
            else:
                for batch_id in batches:
                    batch_vars = assign_map.get((k, batch_id, s), [])
                    if whole_vars or batch_vars:
                        model.Add(sum(whole_vars) + sum(batch_vars) <= 1)


def build_h3_no_room_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    room_ids: list[str],
    num_slots: int,
    courses_by_id: dict,
):
    """H3: ∀ r,s: Σ_{f,c,k,b} assign[f,c,k,b,r,s'] ≤ 1 for every s' in [s..s+block_size-1]."""
    assign_map: dict[tuple[str, int], list] = {}
    for (f, c, k, b, rv, sv), v in assign.items():
        bs = courses_by_id[c].block_size
        for offset in range(bs):
            assign_map.setdefault((rv, sv + offset), []).append(v)
    for r in room_ids:
        for s in range(num_slots):
            vars_at_slot = assign_map.get((r, s), [])
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h4_faculty_unavailable_blocks(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    courses_by_id: dict,
):
    """H4: assign[f,*,*,*,*,s] = 0 if any slot in [s..s+block_size-1] is in f's blocked set."""
    blocked_set: dict[str, set[int]] = {}
    for b in inp.blocked_slots:
        blocked_set.setdefault(b.faculty_id, set()).add(b.slot_index)

    for (f, c, k, b, r, s), v in assign.items():
        bs = courses_by_id[c].block_size
        f_blocked = blocked_set.get(f, set())
        for offset in range(bs):
            if (s + offset) in f_blocked:
                model.Add(v == 0)
                break


def build_h5_faculty_eligibility():
    """H5: enforced by construction — variables only created for eligible (f,c,k,b) tuples."""
    pass  # No-op: eligibility filtering happens in variable creation


def build_h6_hours_match_required(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H6: Σ_{r,s} assign[f,c,k,b,r,s] * block_size == required_hours[c,k] for each (c,k,b).

    For block_size>1 courses, each selected variable represents block_size hours.
    So the count of selected variables must equal required_hours / block_size.
    """
    courses_by_id = {c.id: c for c in inp.courses}

    scheduling_units = set()
    for (f, c, k, b, r, s) in assign.keys():
        scheduling_units.add((c, k, b))

    for (course_id, cohort_id, batch_id) in scheduling_units:
        course = courses_by_id[course_id]
        # Number of blocks to schedule = total_hours / block_size
        num_blocks = course.hours_per_week // course.block_size
        vars_for_unit = [
            v for (f, c, k, b, r, s), v in assign.items()
            if c == course_id and k == cohort_id and b == batch_id
        ]
        if vars_for_unit:
            model.Add(sum(vars_for_unit) == num_blocks)


def build_h7_valid_period_range():
    """H7: enforced by construction — variables only created for valid slot indices."""
    pass  # No-op: slot filtering happens in variable creation


def build_h8_workload_cap(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    compiled: 'CompiledRules',
    courses_by_id: dict,
):
    """H8: per-week and per-day workload caps for each faculty (block_size-aware).

    Each selected variable for a block_size=N course counts as N teaching-hours
    toward the faculty workload cap.
    """
    for f_data in inp.faculty:
        f = f_data.id
        
        # Override caps if a confirmed rule targets this faculty
        cap_week = compiled.faculty_max_periods_week.get(f, f_data.workload_cap_week)
        cap_day = compiled.faculty_max_periods_day.get(f, f_data.workload_cap_day)
        
        # Weekly cap: sum(block_size * var) <= cap_week
        weighted_vars = []
        for (fv, c, k, b, r, s), v in assign.items():
            if fv == f:
                bs = courses_by_id[c].block_size
                if bs == 1:
                    weighted_vars.append(v)
                else:
                    weighted_vars.extend([v] * bs)  # count v once per hour it occupies
        if weighted_vars:
            model.Add(sum(weighted_vars) <= cap_week)

        # Daily cap: sum(block_size * var for vars whose start is on this day) <= cap_day
        day_slots_set = {day: set(slots) for day, slots in inp.slots_per_day.items()}
        for day, slots in day_slots_set.items():
            day_weighted = []
            for (fv, c, k, b, r, s), v in assign.items():
                if fv == f and s in slots:
                    bs = courses_by_id[c].block_size
                    if bs == 1:
                        day_weighted.append(v)
                    else:
                        day_weighted.extend([v] * bs)
            if day_weighted:
                model.Add(sum(day_weighted) <= cap_day)


def build_h9_room_type_match():
    """H9: enforced by construction — variables only created for matching (course_type, room_type) pairs."""
    pass  # No-op: room-type filtering happens in variable creation


def build_h10_shared_lab_capacity(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    courses_by_id: dict,
):
    """H10: For lab type L, slot s: Σ assign using a room of type L at s ≤ count(rooms of type L).
    Block_size-aware: a variable starting at s with block_size=3 occupies s, s+1, s+2.
    """
    room_types = set(r.type for r in inp.rooms)
    rooms_by_type_set: dict[str, set[str]] = {t: set() for t in room_types}
    for r in inp.rooms:
        rooms_by_type_set[r.type].add(r.id)

    # Build occupancy map expanded by block_size
    for room_type in room_types:
        capacity = inp.room_type_counts.get(room_type, len(rooms_by_type_set[room_type]))
        rt_rooms = rooms_by_type_set[room_type]
        slot_vars: dict[int, list] = {}
        for (f, c, k, b, r, sv), v in assign.items():
            if r in rt_rooms:
                bs = courses_by_id[c].block_size
                for offset in range(bs):
                    slot_vars.setdefault(sv + offset, []).append(v)
        for s in range(inp.num_slots):
            vars_for_type = slot_vars.get(s, [])
            if vars_for_type:
                model.Add(sum(vars_for_type) <= capacity)


def build_h11_no_student_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
    courses_by_id: dict,
):
    """H11: An individual student's timetable has no double-booking across their course combination.
    Block_size-aware: a course with block_size=3 starting at slot s occupies s, s+1, s+2.
    """
    assign_map: dict[tuple[str, str, str | None, int], list] = {}
    for (fv, c, k, b, r, sv), v in assign.items():
        bs = courses_by_id[c].block_size
        for offset in range(bs):
            assign_map.setdefault((c, k, b, sv + offset), []).append(v)

    for student in inp.students:
        for s in range(inp.num_slots):
            student_vars_at_slot = []
            for sc in student.courses:
                key = (sc.course_id, sc.cohort_id, sc.batch_id, s)
                if key in assign_map:
                    student_vars_at_slot.extend(assign_map[key])

            if len(student_vars_at_slot) > 1:
                model.Add(sum(student_vars_at_slot) <= 1)


# ---------- Exam Builder functions (Phase 4) ----------


def build_h12_student_exam_overlap(
    model: cp_model.CpModel,
    exam_assign: dict,
    inp: SolverInput,
):
    """H12: No student has two overlapping exam sessions."""
    exam_assign_map = {}
    for (e, i, sv), v in exam_assign.items():
        exam_assign_map.setdefault((e, sv), []).append(v)
        
    for student in inp.students_exams:
        for s in range(inp.num_slots):
            vars_at_slot = []
            for e in student.exam_session_ids:
                if (e, s) in exam_assign_map:
                    vars_at_slot.extend(exam_assign_map[(e, s)])
                    
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h13_exam_room_capacity(
    model: cp_model.CpModel,
    exam_assign: dict,
    inp: SolverInput,
):
    """H13: Exam-room seating capacity is never exceeded at any slot.
    Allows multiple exam sessions to share a room if capacity permits.
    """
    rooms_by_id = {r.id: r for r in inp.rooms}
    sessions_by_id = {s.id: s for s in inp.exam_sessions}

    # Group vars by (room_id, slot)
    room_slot_vars = {}
    for (e, i, sv), v in exam_assign.items():
        room_id = sessions_by_id[e].room_id
        num_students = sessions_by_id[e].num_students
        room_slot_vars.setdefault((room_id, sv), []).append(v * num_students)

    for r in inp.rooms:
        for s in range(inp.num_slots):
            if (r.id, s) in room_slot_vars:
                model.Add(sum(room_slot_vars[(r.id, s)]) <= r.capacity)


def build_h14_invigilator_double_booking(
    model: cp_model.CpModel,
    exam_assign: dict,
    faculty_ids: list[str],
    inp: SolverInput,
):
    """H14: Invigilators are not double-booked and respect workload/availability."""
    # 1. No double booking
    for f in faculty_ids:
        for s in range(inp.num_slots):
            vars_at_slot = [v for (e, i, sv), v in exam_assign.items() if i == f and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)

    # 2. Unavailable blocks
    blocked_set: dict[str, set[int]] = {}
    for b in inp.blocked_slots:
        blocked_set.setdefault(b.faculty_id, set()).add(b.slot_index)

    for (e, i, s), v in exam_assign.items():
        if s in blocked_set.get(i, set()):
            model.Add(v == 0)

    # 3. Workload caps
    faculty_by_id = {f.id: f for f in inp.faculty}
    for f_data in inp.faculty:
        f = f_data.id
        all_vars = [v for (e, i, s), v in exam_assign.items() if i == f]
        if all_vars:
            model.Add(sum(all_vars) <= f_data.workload_cap_week)

        for day, day_slots in inp.slots_per_day.items():
            day_vars = [v for (e, i, s), v in exam_assign.items() if i == f and s in day_slots]
            if day_vars:
                model.Add(sum(day_vars) <= f_data.workload_cap_day)


# ---------- Main solve function ----------

def _solve_classes(inp: SolverInput, timeout_seconds: int) -> list[AssignmentResult] | None:
    model = cp_model.CpModel()

    batches_by_id = {b.id: b for b in inp.batches}

    # Pre-compute eligible (faculty, course, cohort, batch) tuples (H5 by construction)
    eligible_tuples = set()
    for e in inp.eligibility:
        if e.cohort_id in batches_by_id:
            batch = batches_by_id[e.cohort_id]
            eligible_tuples.add((e.faculty_id, e.course_id, batch.cohort_id, batch.id))
        else:
            eligible_tuples.add((e.faculty_id, e.course_id, e.cohort_id, None))

    # Pre-compute valid (course, room) pairs (H9 by construction)
    courses_by_id = {c.id: c for c in inp.courses}
    rooms_by_id = {r.id: r for r in inp.rooms}

    valid_room_pairs: dict[str, list[str]] = {}  # course_id → [room_ids]
    for course in inp.courses:
        valid_rooms = []
        for room in inp.rooms:
            if _room_matches_course(course.type, room.type):
                valid_rooms.append(room.id)
        valid_room_pairs[course.id] = valid_rooms

    # Valid slot indices (H7 by construction)
    valid_slots = set(ps.slot_index for ps in inp.period_slots)

    # H15: block_size>1 courses must not cross day boundaries.
    # Precompute which slots are valid start-slots for each block_size.
    slot_to_day: dict[int, int] = {}
    for ps in inp.period_slots:
        slot_to_day[ps.slot_index] = ps.weekday

    def _valid_start_slots(block_size: int) -> set[int]:
        """Return slot indices where a block of `block_size` can start without crossing a day boundary."""
        if block_size == 1:
            return valid_slots
        result = set()
        for s in valid_slots:
            # All slots s..s+block_size-1 must exist and be on the same day
            day = slot_to_day.get(s)
            if day is None:
                continue
            ok = True
            for off in range(1, block_size):
                if slot_to_day.get(s + off) != day:
                    ok = False
                    break
            if ok:
                result.add(s)
        return result

    # Create decision variables: assign[f, c, k, b, r, s]
    assign: dict[tuple[str, str, str, str | None, str, int], cp_model.IntVar] = {}

    for (f, c, k, b) in eligible_tuples:
        course = courses_by_id[c]
        starts = _valid_start_slots(course.block_size)
        for r in valid_room_pairs.get(c, []):
            for s in starts:
                b_str = b if b else "none"
                var_name = f"assign_{f}_{c}_{k}_{b_str}_{r}_{s}"
                assign[(f, c, k, b, r, s)] = model.NewBoolVar(var_name)

    if not assign:
        return None  # No variables means no valid assignments possible

    # Apply all hard constraints
    faculty_ids = [f.id for f in inp.faculty]
    room_ids = [r.id for r in inp.rooms]

    compiled = compile_constraint_rules(inp)

    build_h1_no_faculty_double_booking(model, assign, faculty_ids, inp.num_slots, courses_by_id)
    build_h2_no_cohort_double_booking(model, assign, inp, courses_by_id)
    build_h3_no_room_double_booking(model, assign, room_ids, inp.num_slots, courses_by_id)
    build_h4_faculty_unavailable_blocks(model, assign, inp, courses_by_id)
    build_h5_faculty_eligibility()  # by construction
    build_h6_hours_match_required(model, assign, inp)
    build_h7_valid_period_range()  # by construction
    build_h8_workload_cap(model, assign, inp, compiled, courses_by_id)
    build_h9_room_type_match()  # by construction
    build_h10_shared_lab_capacity(model, assign, inp, courses_by_id)
    build_h11_no_student_double_booking(model, assign, inp, courses_by_id)

    # Enforce locked assignments (FR-9.2)
    for locked in inp.locked_assignments:
        key = (locked.faculty_id, locked.course_id, locked.cohort_id, locked.batch_id, locked.room_id, locked.slot_index)
        if key in assign:
            model.Add(assign[key] == 1)

    # Soft constraints
    import solver.objective as obj
    penalties = []
    
    pen_overlap = obj.add_elective_no_overlap_core_penalty(model, assign, inp, compiled)
    if pen_overlap is not None:
        penalties.append(pen_overlap)
        
    if penalties:
        model.Minimize(sum(penalties))
    
    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Extract solution
    results = []
    for (f, c, k, b, r, s), v in assign.items():
        if solver.Value(v) == 1:
            results.append(AssignmentResult(
                faculty_id=f,
                course_id=c,
                cohort_id=k,  # the parent cohort
                room_id=r,
                slot_index=s,
                slot_span=courses_by_id[c].block_size,
                batch_id=b,   # explicitly track batch_id
            ))

    return results


def _solve_exams(inp: SolverInput, timeout_seconds: int) -> list[ExamSessionResult] | None:
    model = cp_model.CpModel()

    # Valid slot indices (H7 by construction)
    valid_slots = set(ps.slot_index for ps in inp.period_slots)

    # exam_assign[e, i, s]
    exam_assign: dict[tuple[str, str, int], cp_model.IntVar] = {}

    for session in inp.exam_sessions:
        e = session.id
        for faculty in inp.faculty:
            i = faculty.id
            for s in valid_slots:
                var_name = f"exam_assign_{e}_{i}_{s}"
                exam_assign[(e, i, s)] = model.NewBoolVar(var_name)

        # Every exam session MUST be scheduled exactly once (one slot, one invigilator)
        session_vars = [v for (ev, iv, sv), v in exam_assign.items() if ev == e]
        if session_vars:
            model.AddExactlyOne(session_vars)

    if not exam_assign:
        return None

    compiled = compile_constraint_rules(inp)

    # 1. Hard Constraints
    faculty_ids = [f.id for f in inp.faculty]
    build_h12_student_exam_overlap(model, exam_assign, inp)
    build_h13_exam_room_capacity(model, exam_assign, inp)
    build_h14_invigilator_double_booking(model, exam_assign, faculty_ids, inp)

    # 2. Soft Constraints (Objective)
    import solver.objective as obj
    penalty = obj.add_s9_exam_spread(model, exam_assign, inp, compiled)
    if penalty is not None:
        model.Minimize(penalty)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    results = []
    sessions_by_id = {s.id: s for s in inp.exam_sessions}
    for (e, i, s), v in exam_assign.items():
        if solver.Value(v) == 1:
            results.append(ExamSessionResult(
                id=e,
                room_id=sessions_by_id[e].room_id,
                invigilator_staff_profile_id=i,
                slot_index=s,
            ))

    return results


def solve(inp: SolverInput, timeout_seconds: int = 30) -> list[AssignmentResult] | list[ExamSessionResult] | None:
    """Build the CP-SAT model, apply constraints, and solve.

    Returns a list of AssignmentResult or ExamSessionResult on success, or None if infeasible.
    """
    if inp.is_exam:
        return _solve_exams(inp, timeout_seconds)
    else:
        return _solve_classes(inp, timeout_seconds)

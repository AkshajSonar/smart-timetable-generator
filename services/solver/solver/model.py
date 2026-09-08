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


# ---------- Room-type matching for H9 (Phase 1 simplification) ----------

_COURSE_TYPE_TO_ROOM_TYPES = {
    "core": {"classroom", "lecture_hall", "seminar_hall"},
    "elective": {"classroom", "lecture_hall", "seminar_hall"},
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
):
    """H1: ∀ f,s: Σ_{c,k,b,r} assign[f,c,k,b,r,s] ≤ 1."""
    for f in faculty_ids:
        for s in range(num_slots):
            vars_at_slot = [v for (fv, c, k, b, r, sv), v in assign.items() if fv == f and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h2_no_cohort_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H2: No cohort/batch double-booked across two courses in the same slot."""
    batches_by_cohort: dict[str, list[str]] = {}
    for k in inp.cohorts:
        batches_by_cohort[k.id] = []
    for b in inp.batches:
        batches_by_cohort[b.cohort_id].append(b.id)

    for k in [c.id for c in inp.cohorts]:
        for s in range(inp.num_slots):
            whole_vars = [v for (f, c, kv, b, r, sv), v in assign.items() if kv == k and b is None and sv == s]
            batches = batches_by_cohort.get(k, [])
            
            if not batches:
                if whole_vars:
                    model.Add(sum(whole_vars) <= 1)
            else:
                for batch_id in batches:
                    batch_vars = [v for (f, c, kv, b, r, sv), v in assign.items() if kv == k and b == batch_id and sv == s]
                    if whole_vars or batch_vars:
                        model.Add(sum(whole_vars) + sum(batch_vars) <= 1)


def build_h3_no_room_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    room_ids: list[str],
    num_slots: int,
):
    """H3: ∀ r,s: Σ_{f,c,k,b} assign[f,c,k,b,r,s] ≤ 1."""
    for r in room_ids:
        for s in range(num_slots):
            vars_at_slot = [v for (f, c, k, b, rv, sv), v in assign.items() if rv == r and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h4_faculty_unavailable_blocks(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H4: assign[f,*,*,*,*,s] = 0 for every s in f's blocked set."""
    blocked_set: dict[str, set[int]] = {}
    for b in inp.blocked_slots:
        blocked_set.setdefault(b.faculty_id, set()).add(b.slot_index)

    for (f, c, k, b, r, s), v in assign.items():
        if s in blocked_set.get(f, set()):
            model.Add(v == 0)


def build_h5_faculty_eligibility():
    """H5: enforced by construction — variables only created for eligible (f,c,k,b) tuples."""
    pass  # No-op: eligibility filtering happens in variable creation


def build_h6_hours_match_required(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H6: Σ_{r,s} assign[f,c,k,b,r,s] == required_hours[c,k] for each (c,k,b) eligible."""
    courses_by_id = {c.id: c for c in inp.courses}

    scheduling_units = set()
    for (f, c, k, b, r, s) in assign.keys():
        scheduling_units.add((c, k, b))

    for (course_id, cohort_id, batch_id) in scheduling_units:
        required = courses_by_id[course_id].hours_per_week
        vars_for_unit = [
            v for (f, c, k, b, r, s), v in assign.items()
            if c == course_id and k == cohort_id and b == batch_id
        ]
        if vars_for_unit:
            model.Add(sum(vars_for_unit) == required)


def build_h7_valid_period_range():
    """H7: enforced by construction — variables only created for valid slot indices."""
    pass  # No-op: slot filtering happens in variable creation


def build_h8_workload_cap(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H8: per-week and per-day workload caps for each faculty."""
    faculty_by_id = {f.id: f for f in inp.faculty}

    for f_data in inp.faculty:
        f = f_data.id
        # Weekly cap
        all_vars = [v for (fv, c, k, b, r, s), v in assign.items() if fv == f]
        if all_vars:
            model.Add(sum(all_vars) <= f_data.workload_cap_week)

        # Daily cap
        for day, day_slots in inp.slots_per_day.items():
            day_vars = [v for (fv, c, k, b, r, s), v in assign.items() if fv == f and s in day_slots]
            if day_vars:
                model.Add(sum(day_vars) <= f_data.workload_cap_day)


def build_h9_room_type_match():
    """H9: enforced by construction — variables only created for matching (course_type, room_type) pairs."""
    pass  # No-op: room-type filtering happens in variable creation


def build_h10_shared_lab_capacity(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H10: For lab type L, slot s: Σ assign using a room of type L at s ≤ count(rooms of type L)."""
    room_types = set(r.type for r in inp.rooms)
    rooms_by_type = {t: [] for t in room_types}
    for r in inp.rooms:
        rooms_by_type[r.type].append(r.id)

    for room_type in room_types:
        capacity = inp.room_type_counts.get(room_type, len(rooms_by_type[room_type]))
        for s in range(inp.num_slots):
            vars_for_type = [
                v for (f, c, k, b, r, sv), v in assign.items()
                if sv == s and r in rooms_by_type[room_type]
            ]
            if vars_for_type:
                model.Add(sum(vars_for_type) <= capacity)


def build_h11_no_student_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H11: An individual student's timetable has no double-booking across their course combination.
    Uses explicit batch membership logic: if a student is in Batch A for a course, they are only
    constrained against Batch A's assignments for that course, not Batch B's.
    """
    for student in inp.students:
        for s in range(inp.num_slots):
            # Gather all variables for this student's courses at this slot
            student_vars_at_slot = []
            for sc in student.courses:
                # If they are in a specific batch for this course, match only that batch.
                # If they are not in a batch (whole cohort course), match where b is None.
                # Wait, what if the input just says batch_id is None, meaning it's a whole-cohort course?
                # Then we match b == None. But what if there are no batches for that course at all?
                # The decision variable has b=None. So matching sc.batch_id works.
                vars_for_course = [
                    v for (fv, c, k, b, r, sv), v in assign.items()
                    if c == sc.course_id and k == sc.cohort_id and b == sc.batch_id and sv == s
                ]
                student_vars_at_slot.extend(vars_for_course)
            
            if student_vars_at_slot:
                model.Add(sum(student_vars_at_slot) <= 1)


# ---------- Exam Builder functions (Phase 4) ----------


def build_h12_student_exam_overlap(
    model: cp_model.CpModel,
    exam_assign: dict,
    inp: SolverInput,
):
    """H12: No student has two overlapping exam sessions."""
    for student in inp.students_exams:
        for s in range(inp.num_slots):
            vars_at_slot = [
                v for (e, i, sv), v in exam_assign.items()
                if sv == s and e in student.exam_session_ids
            ]
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

    for r in inp.rooms:
        for s in range(inp.num_slots):
            vars_in_room = [
                v for (e, i, sv), v in exam_assign.items()
                if sv == s and sessions_by_id[e].room_id == r.id
            ]
            if vars_in_room:
                # Sum of (is_active * num_students) <= capacity
                model.Add(
                    sum(v * sessions_by_id[e].num_students for (e, i, sv), v in exam_assign.items() if sv == s and sessions_by_id[e].room_id == r.id)
                    <= r.capacity
                )


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

    # Create decision variables: assign[f, c, k, b, r, s]
    assign: dict[tuple[str, str, str, str | None, str, int], cp_model.IntVar] = {}

    for (f, c, k, b) in eligible_tuples:
        for r in valid_room_pairs.get(c, []):
            for s in valid_slots:
                b_str = b if b else "none"
                var_name = f"assign_{f}_{c}_{k}_{b_str}_{r}_{s}"
                assign[(f, c, k, b, r, s)] = model.NewBoolVar(var_name)

    if not assign:
        return None  # No variables means no valid assignments possible

    # Apply all hard constraints
    faculty_ids = [f.id for f in inp.faculty]
    room_ids = [r.id for r in inp.rooms]

    build_h1_no_faculty_double_booking(model, assign, faculty_ids, inp.num_slots)
    build_h2_no_cohort_double_booking(model, assign, inp)
    build_h3_no_room_double_booking(model, assign, room_ids, inp.num_slots)
    build_h4_faculty_unavailable_blocks(model, assign, inp)
    build_h5_faculty_eligibility()  # by construction
    build_h6_hours_match_required(model, assign, inp)
    build_h7_valid_period_range()  # by construction
    build_h8_workload_cap(model, assign, inp)
    build_h9_room_type_match()  # by construction
    build_h10_shared_lab_capacity(model, assign, inp)
    build_h11_no_student_double_booking(model, assign, inp)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
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

    faculty_ids = [f.id for f in inp.faculty]

    # Apply Exam Hard Constraints
    build_h12_student_exam_overlap(model, exam_assign, inp)
    build_h13_exam_room_capacity(model, exam_assign, inp)
    build_h14_invigilator_double_booking(model, exam_assign, faculty_ids, inp)

    # Apply S9 (Soft Objective)
    from solver.objective import add_s9_exam_spread
    add_s9_exam_spread(model, exam_assign, inp)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
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

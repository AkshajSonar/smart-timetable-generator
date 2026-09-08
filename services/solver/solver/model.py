"""CP-SAT solver model — one builder function per H-code (§9.3).

Decision variable: assign[f, c, k, r, s] ∈ {0, 1}
  Staff f teaches course c to cohort k in room r at slot s.

H5 (eligibility) and H9 (room type match) are enforced by construction —
variables are only created for valid (f,c,k) and (c,r) pairs.

H7 (valid period range) is enforced by construction — variables are only
created for slot indices present in the period_slots input.
"""

from ortools.sat.python import cp_model

from solver.data_types import AssignmentResult, SolverInput


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
    """H1: ∀ f,s: Σ_{c,k,r} assign[f,c,k,r,s] ≤ 1."""
    for f in faculty_ids:
        for s in range(num_slots):
            vars_at_slot = [v for (fv, c, k, r, sv), v in assign.items() if fv == f and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h2_no_cohort_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    cohort_ids: list[str],
    num_slots: int,
):
    """H2: ∀ k,s: Σ_{f,c,r} assign[f,c,k,r,s] ≤ 1."""
    for k in cohort_ids:
        for s in range(num_slots):
            vars_at_slot = [v for (f, c, kv, r, sv), v in assign.items() if kv == k and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h3_no_room_double_booking(
    model: cp_model.CpModel,
    assign: dict,
    room_ids: list[str],
    num_slots: int,
):
    """H3: ∀ r,s: Σ_{f,c,k} assign[f,c,k,r,s] ≤ 1."""
    for r in room_ids:
        for s in range(num_slots):
            vars_at_slot = [v for (f, c, k, rv, sv), v in assign.items() if rv == r and sv == s]
            if vars_at_slot:
                model.Add(sum(vars_at_slot) <= 1)


def build_h4_faculty_unavailable_blocks(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H4: assign[f,*,*,*,s] = 0 for every s in f's blocked set."""
    blocked_set: dict[str, set[int]] = {}
    for b in inp.blocked_slots:
        blocked_set.setdefault(b.faculty_id, set()).add(b.slot_index)

    for (f, c, k, r, s), v in assign.items():
        if s in blocked_set.get(f, set()):
            model.Add(v == 0)


def build_h5_faculty_eligibility():
    """H5: enforced by construction — variables only created for eligible (f,c,k) triples."""
    pass  # No-op: eligibility filtering happens in variable creation


def build_h6_hours_match_required(
    model: cp_model.CpModel,
    assign: dict,
    inp: SolverInput,
):
    """H6: Σ_{r,s} assign[f,c,k,r,s] == required_hours[c,k] for each (f,c,k) eligible.

    For Phase 1 (single cohort), the hours for (c,k) must sum exactly to
    course.hours_per_week across all eligible faculty for that (c,k).
    """
    courses_by_id = {c.id: c for c in inp.courses}

    # Group by (course_id, cohort_id) — sum across all faculty and rooms
    for cohort in inp.cohorts:
        for course in inp.courses:
            required = courses_by_id[course.id].hours_per_week
            vars_for_ck = [
                v for (f, c, k, r, s), v in assign.items()
                if c == course.id and k == cohort.id
            ]
            if vars_for_ck:
                model.Add(sum(vars_for_ck) == required)


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
        all_vars = [v for (fv, c, k, r, s), v in assign.items() if fv == f]
        if all_vars:
            model.Add(sum(all_vars) <= f_data.workload_cap_week)

        # Daily cap
        for day, day_slots in inp.slots_per_day.items():
            day_vars = [v for (fv, c, k, r, s), v in assign.items() if fv == f and s in day_slots]
            if day_vars:
                model.Add(sum(day_vars) <= f_data.workload_cap_day)


def build_h9_room_type_match():
    """H9: enforced by construction — variables only created for matching (course_type, room_type) pairs."""
    pass  # No-op: room-type filtering happens in variable creation


# ---------- Main solve function ----------


def solve(inp: SolverInput, timeout_seconds: int = 30) -> list[AssignmentResult] | None:
    """Build the CP-SAT model, apply H1–H9, and solve.

    Returns a list of AssignmentResult on success, or None if infeasible.
    """
    model = cp_model.CpModel()

    # Pre-compute eligible (faculty, course, cohort) triples (H5 by construction)
    eligible_triples = set()
    for e in inp.eligibility:
        eligible_triples.add((e.faculty_id, e.course_id, e.cohort_id))

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

    # Create decision variables: assign[f, c, k, r, s]
    assign: dict[tuple[str, str, str, str, int], cp_model.IntVar] = {}

    for (f, c, k) in eligible_triples:
        for r in valid_room_pairs.get(c, []):
            for s in valid_slots:
                var_name = f"assign_{f}_{c}_{k}_{r}_{s}"
                assign[(f, c, k, r, s)] = model.NewBoolVar(var_name)

    if not assign:
        return None  # No variables means no valid assignments possible

    # Apply all hard constraints
    faculty_ids = [f.id for f in inp.faculty]
    cohort_ids = [k.id for k in inp.cohorts]
    room_ids = [r.id for r in inp.rooms]

    build_h1_no_faculty_double_booking(model, assign, faculty_ids, inp.num_slots)
    build_h2_no_cohort_double_booking(model, assign, cohort_ids, inp.num_slots)
    build_h3_no_room_double_booking(model, assign, room_ids, inp.num_slots)
    build_h4_faculty_unavailable_blocks(model, assign, inp)
    build_h5_faculty_eligibility()  # by construction
    build_h6_hours_match_required(model, assign, inp)
    build_h7_valid_period_range()  # by construction
    build_h8_workload_cap(model, assign, inp)
    build_h9_room_type_match()  # by construction

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    # Extract solution
    results = []
    for (f, c, k, r, s), v in assign.items():
        if solver.Value(v) == 1:
            results.append(AssignmentResult(
                faculty_id=f,
                course_id=c,
                cohort_id=k,
                room_id=r,
                slot_index=s,
                slot_span=courses_by_id[c].block_size,
            ))

    return results

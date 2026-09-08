"""Independent conflict checker — re-validates H1–H9 from raw assignment rows.

THIS IS A SEPARATE CODE PATH FROM THE SOLVER'S CONSTRAINT CONSTRUCTION
(invariant #2, FR-6.2, NFR-1). It does NOT call any build_h* function from
model.py. It re-derives violations by iterating assignments directly.
"""

from collections import defaultdict
from dataclasses import dataclass

from solver.data_types import AssignmentResult, SolverInput
from solver.model import _room_matches_course


@dataclass
class Violation:
    h_code: str
    message: str


def check_h1_no_faculty_double_booking(
    assignments: list[AssignmentResult],
) -> list[Violation]:
    """H1: No faculty in two places at the same slot."""
    violations = []
    by_faculty_slot: dict[tuple[str, int], list[AssignmentResult]] = defaultdict(list)
    for a in assignments:
        for offset in range(a.slot_span):
            by_faculty_slot[(a.faculty_id, a.slot_index + offset)].append(a)
    for (f, s), group in by_faculty_slot.items():
        if len(group) > 1:
            violations.append(Violation(
                h_code="H1",
                message=f"Faculty {f} double-booked at slot {s}: {len(group)} assignments",
            ))
    return violations


def check_h2_no_cohort_double_booking(
    assignments: list[AssignmentResult],
) -> list[Violation]:
    """H2: No cohort/batch double-booked across two courses in the same slot."""
    violations = []
    
    # Track whole-cohort vs batch assignments separately per cohort per slot
    whole_cohort_by_slot: dict[tuple[str, int], list[AssignmentResult]] = defaultdict(list)
    batch_by_slot: dict[tuple[str, str, int], list[AssignmentResult]] = defaultdict(list)

    for a in assignments:
        for offset in range(a.slot_span):
            s = a.slot_index + offset
            if a.batch_id is None:
                whole_cohort_by_slot[(a.cohort_id, s)].append(a)
            else:
                batch_by_slot[(a.cohort_id, a.batch_id, s)].append(a)

    cohorts = set(k for k, _ in whole_cohort_by_slot.keys()) | set(k for k, _, _ in batch_by_slot.keys())

    for k in cohorts:
        # All slots this cohort has assignments in
        slots = set(s for kv, s in whole_cohort_by_slot.keys() if kv == k) | set(s for kv, _, s in batch_by_slot.keys() if kv == k)
        
        for s in slots:
            whole = whole_cohort_by_slot[(k, s)]
            # Check whole cohort double booking
            if len(whole) > 1:
                violations.append(Violation(
                    h_code="H2",
                    message=f"Cohort {k} double-booked at slot {s}: {len(whole)} whole-cohort assignments",
                ))
                continue
                
            # Find all batches for this cohort at this slot
            batches_at_slot = set(b for kv, b, sv in batch_by_slot.keys() if kv == k and sv == s)
            
            for b in batches_at_slot:
                batch_assigns = batch_by_slot[(k, b, s)]
                total = len(whole) + len(batch_assigns)
                if total > 1:
                    violations.append(Violation(
                        h_code="H2",
                        message=f"Cohort {k} batch {b} double-booked at slot {s}: {len(whole)} whole + {len(batch_assigns)} batch assignments",
                    ))

    return violations


def check_h3_no_room_double_booking(
    assignments: list[AssignmentResult],
) -> list[Violation]:
    """H3: No room used by two groups at the same slot."""
    violations = []
    by_room_slot: dict[tuple[str, int], list[AssignmentResult]] = defaultdict(list)
    for a in assignments:
        for offset in range(a.slot_span):
            by_room_slot[(a.room_id, a.slot_index + offset)].append(a)
    for (r, s), group in by_room_slot.items():
        if len(group) > 1:
            violations.append(Violation(
                h_code="H3",
                message=f"Room {r} double-booked at slot {s}: {len(group)} assignments",
            ))
    return violations


def check_h4_faculty_unavailable_blocks(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H4: Faculty not scheduled in blocked slots."""
    violations = []
    blocked_set: dict[str, set[int]] = defaultdict(set)
    for b in inp.blocked_slots:
        blocked_set[b.faculty_id].add(b.slot_index)

    for a in assignments:
        for offset in range(a.slot_span):
            actual_slot = a.slot_index + offset
            if actual_slot in blocked_set.get(a.faculty_id, set()):
                violations.append(Violation(
                    h_code="H4",
                    message=f"Faculty {a.faculty_id} scheduled at blocked slot {actual_slot}",
                ))
    return violations


def check_h5_faculty_eligibility(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H5: Faculty only assigned to eligible (course, cohort) pairs."""
    violations = []
    eligible = set()
    for e in inp.eligibility:
        eligible.add((e.faculty_id, e.course_id, e.cohort_id))

    for a in assignments:
        if (a.faculty_id, a.course_id, a.cohort_id) not in eligible:
            violations.append(Violation(
                h_code="H5",
                message=f"Faculty {a.faculty_id} not eligible for course {a.course_id} / cohort {a.cohort_id}",
            ))
    return violations


def check_h6_hours_match_required(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H6: Scheduled hours per eligible (course, cohort/batch) == required hours."""
    violations = []
    courses_by_id = {c.id: c for c in inp.courses}
    batches_by_id = {b.id: b for b in inp.batches}

    # Find valid scheduling units from eligibility
    scheduling_units = set()
    for e in inp.eligibility:
        if e.cohort_id in batches_by_id:
            batch = batches_by_id[e.cohort_id]
            scheduling_units.add((e.course_id, batch.cohort_id, batch.id))
        else:
            scheduling_units.add((e.course_id, e.cohort_id, None))

    # Calculate actual hours
    hours: dict[tuple[str, str, str | None], int] = defaultdict(int)
    for a in assignments:
        hours[(a.course_id, a.cohort_id, a.batch_id)] += a.slot_span

    for (course_id, cohort_id, batch_id) in scheduling_units:
        course = courses_by_id.get(course_id)
        if not course:
            continue
            
        required = course.hours_per_week
        actual = hours.get((course_id, cohort_id, batch_id), 0)
        if actual != required:
            target = f"batch {batch_id}" if batch_id else f"cohort {cohort_id}"
            violations.append(Violation(
                h_code="H6",
                message=f"Course {course_id} / {target}: scheduled {actual}h, required {required}h",
            ))
            
    return violations


def check_h7_valid_period_range(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H7: All assignments within valid period range."""
    violations = []
    valid_slots = set(ps.slot_index for ps in inp.period_slots)

    for a in assignments:
        for offset in range(a.slot_span):
            actual_slot = a.slot_index + offset
            if actual_slot not in valid_slots:
                violations.append(Violation(
                    h_code="H7",
                    message=f"Assignment at slot {actual_slot} is outside valid period range",
                ))
    return violations


def check_h8_workload_cap(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H8: Faculty weekly/daily workload cap not exceeded."""
    violations = []
    faculty_by_id = {f.id: f for f in inp.faculty}

    # Weekly load
    weekly_load: dict[str, int] = defaultdict(int)
    for a in assignments:
        weekly_load[a.faculty_id] += a.slot_span

    for fid, load in weekly_load.items():
        cap = faculty_by_id[fid].workload_cap_week
        if load > cap:
            violations.append(Violation(
                h_code="H8",
                message=f"Faculty {fid} weekly load {load} exceeds cap {cap}",
            ))

    # Daily load
    # Map slot_index → weekday
    slot_to_day: dict[int, int] = {}
    for ps in inp.period_slots:
        slot_to_day[ps.slot_index] = ps.weekday

    daily_load: dict[tuple[str, int], int] = defaultdict(int)
    for a in assignments:
        for offset in range(a.slot_span):
            actual_slot = a.slot_index + offset
            day = slot_to_day.get(actual_slot)
            if day is not None:
                daily_load[(a.faculty_id, day)] += 1

    for (fid, day), load in daily_load.items():
        cap = faculty_by_id[fid].workload_cap_day
        if load > cap:
            violations.append(Violation(
                h_code="H8",
                message=f"Faculty {fid} daily load on day {day}: {load} exceeds cap {cap}",
            ))

    return violations


def check_h9_room_type_match(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H9: Room type/equipment matches course requirement."""
    violations = []
    courses_by_id = {c.id: c for c in inp.courses}
    rooms_by_id = {r.id: r for r in inp.rooms}

    for a in assignments:
        course = courses_by_id.get(a.course_id)
        room = rooms_by_id.get(a.room_id)
        if course and room:
            if not _room_matches_course(course.type, room.type):
                violations.append(Violation(
                    h_code="H9",
                    message=f"Room {a.room_id} (type={room.type}) doesn't match course {a.course_id} (type={course.type})",
                ))
    return violations


def check_h10_shared_lab_capacity(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """H10: For lab type L, slot s: Σ assign using a room of type L at s ≤ count(rooms of type L)."""
    violations = []
    room_types = set(r.type for r in inp.rooms)
    rooms_by_type = {t: set() for t in room_types}
    for r in inp.rooms:
        rooms_by_type[r.type].add(r.id)

    # Track usage per room type per slot
    usage_by_type_slot: dict[tuple[str, int], int] = defaultdict(int)
    rooms_by_id = {r.id: r for r in inp.rooms}

    for a in assignments:
        r = rooms_by_id.get(a.room_id)
        if r:
            for offset in range(a.slot_span):
                usage_by_type_slot[(r.type, a.slot_index + offset)] += 1

    for room_type in room_types:
        capacity = inp.room_type_counts.get(room_type, len(rooms_by_type[room_type]))
        for s in range(inp.num_slots):
            actual = usage_by_type_slot.get((room_type, s), 0)
            if actual > capacity:
                violations.append(Violation(
                    h_code="H10",
                    message=f"Room type {room_type} capacity exceeded at slot {s}: used {actual}, capacity {capacity}",
                ))
    return violations


def check_all(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """Run all H1–H10 checks and return combined violations."""
    violations = []
    violations.extend(check_h1_no_faculty_double_booking(assignments))
    violations.extend(check_h2_no_cohort_double_booking(assignments))
    violations.extend(check_h3_no_room_double_booking(assignments))
    violations.extend(check_h4_faculty_unavailable_blocks(assignments, inp))
    violations.extend(check_h5_faculty_eligibility(assignments, inp))
    violations.extend(check_h6_hours_match_required(assignments, inp))
    violations.extend(check_h7_valid_period_range(assignments, inp))
    violations.extend(check_h8_workload_cap(assignments, inp))
    violations.extend(check_h9_room_type_match(assignments, inp))
    violations.extend(check_h10_shared_lab_capacity(assignments, inp))
    return violations

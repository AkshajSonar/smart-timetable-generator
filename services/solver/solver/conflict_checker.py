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
    """H2: No cohort in two courses at the same slot."""
    violations = []
    by_cohort_slot: dict[tuple[str, int], list[AssignmentResult]] = defaultdict(list)
    for a in assignments:
        for offset in range(a.slot_span):
            by_cohort_slot[(a.cohort_id, a.slot_index + offset)].append(a)
    for (k, s), group in by_cohort_slot.items():
        if len(group) > 1:
            violations.append(Violation(
                h_code="H2",
                message=f"Cohort {k} double-booked at slot {s}: {len(group)} assignments",
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
    """H6: Scheduled hours per (course, cohort) == required hours."""
    violations = []
    courses_by_id = {c.id: c for c in inp.courses}

    hours: dict[tuple[str, str], int] = defaultdict(int)
    for a in assignments:
        hours[(a.course_id, a.cohort_id)] += a.slot_span

    for cohort in inp.cohorts:
        for course in inp.courses:
            required = course.hours_per_week
            actual = hours.get((course.id, cohort.id), 0)
            if actual != required:
                violations.append(Violation(
                    h_code="H6",
                    message=f"Course {course.id} / cohort {cohort.id}: scheduled {actual}h, required {required}h",
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


def check_all(
    assignments: list[AssignmentResult],
    inp: SolverInput,
) -> list[Violation]:
    """Run all H1–H9 checks and return combined violations."""
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
    return violations

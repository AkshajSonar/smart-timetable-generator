"""Shared edit service — FR-9.1, FR-10.3.

Extracted from the /edit router handler so substitution /confirm can
reuse the same version_no-gated, conflict_checker-validated commit path
without reimplementing parallel logic.

Called by:
  - timetables /edit  (manual cell edit, is_locked=True)
  - substitutions /confirm  (substitute assignment, is_locked=False — the
    substitution_log row is the audit trail; the assignment is a live patch)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "solver"))


async def apply_assignment_edit(
    db: AsyncSession,
    *,
    version_id: UUID,
    tenant_id: UUID,
    assignment_id: UUID,
    version_no: int,
    new_staff_profile_id: UUID | None = None,
    new_room_id: UUID | None = None,
    new_slot_start: int | None = None,
    actor_identity_id: UUID,
    audit_action: str = "edit",
    lock_cell: bool = True,
) -> int:
    """Apply an assignment change with full H1-H11 re-validation.

    Returns the new version_no after incrementing.

    Raises HTTPException:
      - 404 if timetable_version or assignment not found
      - 409 CONFLICT if version_no is stale
      - 422 INFEASIBLE_CONFIGURATION if any hard constraint is violated
    """
    from app.models.assignment import Assignment
    from app.models.batch import Batch
    from app.models.cohort import Cohort
    from app.models.course import Course
    from app.models.eligibility import Eligibility
    from app.models.period_template import PeriodTemplate
    from app.models.room import Room
    from app.models.staff_availability_block import StaffAvailabilityBlock
    from app.models.staff_profile import StaffProfile
    from app.models.timetable_version import TimetableVersion
    from app.models.stubs import AuditLog
    from app.models.student_profile import StudentProfile
    from app.models.batch_membership import BatchMembership
    from app.models.enrollment_record import EnrollmentRecord
    from app.models.elective_section import ElectiveSection
    from solver.conflict_checker import check_all
    from solver.data_types import (
        AssignmentResult, BlockedSlot, CourseData, EligibilityData,
        FacultyData, PeriodSlot, RoomData, SolverInput, StudentData, StudentCourseData,
    )

    # 1. Load TimetableVersion + version_no check
    tv = (await db.execute(select(TimetableVersion).where(TimetableVersion.id == version_id))).scalar_one_or_none()
    if not tv:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}},
        )
    if tv.version_no != version_no:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": (
                        f"Stale version_no: submitted {version_no}, "
                        f"current is {tv.version_no}. Re-fetch and retry."
                    ),
                }
            },
        )

    # 2. Load the target assignment
    target = (await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.timetable_version_id == version_id,
        )
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Assignment not found in this timetable version"}},
        )

    # 3. Load all assignments for snapshot
    all_assignments = list((await db.execute(
        select(Assignment).where(Assignment.timetable_version_id == version_id)
    )).scalars().all())

    # 4. Build in-memory snapshot with proposed change
    def _to_result(a: Assignment) -> AssignmentResult:
        return AssignmentResult(
            faculty_id=str(a.staff_profile_id),
            course_id=str(a.course_id),
            cohort_id=str(a.cohort_id),
            room_id=str(a.room_id),
            slot_index=a.slot_start,
            slot_span=a.slot_span,
            batch_id=str(a.batch_id) if a.batch_id else None,
        )

    snapshot: list[AssignmentResult] = []
    for a in all_assignments:
        if a.id == assignment_id:
            r = _to_result(a)
            if new_staff_profile_id is not None:
                r.faculty_id = str(new_staff_profile_id)
            if new_room_id is not None:
                r.room_id = str(new_room_id)
            if new_slot_start is not None:
                r.slot_index = new_slot_start
            snapshot.append(r)
        else:
            snapshot.append(_to_result(a))

    # 5. Load master data for H1-H11
    faculty_rows = list((await db.execute(select(StaffProfile))).scalars().all())
    course_rows = list((await db.execute(select(Course))).scalars().all())
    room_rows = list((await db.execute(select(Room))).scalars().all())
    elig_rows = list((await db.execute(select(Eligibility))).scalars().all())
    period_rows = list((await db.execute(select(PeriodTemplate))).scalars().all())
    blocked_rows = list((await db.execute(select(StaffAvailabilityBlock))).scalars().all())
    student_rows = list((await db.execute(select(StudentProfile))).scalars().all())
    membership_rows = list((await db.execute(select(BatchMembership))).scalars().all())
    batch_rows = list((await db.execute(select(Batch))).scalars().all())
    enroll_rows = list((await db.execute(select(EnrollmentRecord))).scalars().all())
    elec_rows = list((await db.execute(select(ElectiveSection))).scalars().all())

    batch_by_id = {str(b.id): b for b in batch_rows}
    elec_by_id = {str(e.id): e for e in elec_rows}
    member_by_student: dict[str, list[str]] = {}
    for m in membership_rows:
        member_by_student.setdefault(str(m.student_profile_id), []).append(str(m.batch_id))

    slots_per_day: dict[int, list[int]] = {}
    period_slots_data: list[PeriodSlot] = []
    for i, pt in enumerate(period_rows):
        ps = PeriodSlot(slot_index=i, weekday=pt.weekday, period_index=pt.period_index)
        period_slots_data.append(ps)
        slots_per_day.setdefault(pt.weekday, []).append(i)

    students_data: list[StudentData] = []
    for s in student_rows:
        sid = str(s.id)
        courses_for_student: list[StudentCourseData] = []
        for bid in member_by_student.get(sid, []):
            b = batch_by_id.get(bid)
            if b:
                courses_for_student.append(
                    StudentCourseData(course_id=str(b.course_id), cohort_id=str(b.cohort_id), batch_id=bid)
                )
        for er in enroll_rows:
            if str(er.student_profile_id) == sid:
                sec = elec_by_id.get(str(er.elective_section_id))
                if sec:
                    courses_for_student.append(
                        StudentCourseData(course_id=str(sec.course_id), cohort_id=str(s.cohort_id), batch_id=None)
                    )
        if courses_for_student:
            students_data.append(StudentData(id=sid, courses=courses_for_student))

    room_type_counts: dict[str, int] = {}
    for r in room_rows:
        room_type_counts[r.type] = room_type_counts.get(r.type, 0) + 1

    inp = SolverInput(
        faculty=[FacultyData(id=str(f.id), workload_cap_week=f.workload_cap_week, workload_cap_day=f.workload_cap_day) for f in faculty_rows],
        courses=[CourseData(id=str(c.id), type=c.type, hours_per_week=c.hours_per_week, block_size=getattr(c, "block_size", 1)) for c in course_rows],
        cohorts=[],
        rooms=[RoomData(id=str(r.id), type=r.type, capacity=r.capacity, equipment_tags=r.equipment_tags or []) for r in room_rows],
        eligibility=[EligibilityData(faculty_id=str(e.staff_profile_id), course_id=str(e.course_id), cohort_id=str(e.cohort_id)) for e in elig_rows],
        period_slots=period_slots_data,
        blocked_slots=[BlockedSlot(faculty_id=str(b.staff_profile_id), slot_index=b.period_index) for b in blocked_rows],
        slots_per_day=slots_per_day,
        num_slots=len(period_slots_data),
        room_type_counts=room_type_counts,
        students=students_data,
    )

    # 6. Run H1-H11 conflict checker
    violations = check_all(snapshot, inp)
    if violations:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "Edit creates hard-constraint violations",
                    "details": [{"h_code": v.h_code, "message": v.message} for v in violations],
                }
            },
        )

    # 7. Commit: apply edit, optionally lock cell, increment version_no
    before_snapshot = {
        "staff_profile_id": str(target.staff_profile_id),
        "slot_start": target.slot_start,
        "room_id": str(target.room_id),
    }

    if new_staff_profile_id is not None:
        target.staff_profile_id = new_staff_profile_id
    if new_room_id is not None:
        target.room_id = new_room_id
    if new_slot_start is not None:
        target.slot_start = new_slot_start

    if lock_cell:
        target.is_locked = True  # FR-9.2

    tv.version_no += 1  # invariant #7
    db.add(target)
    db.add(tv)

    # 8. Write audit_log
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_identity_id=actor_identity_id,
        action=audit_action,
        entity_type="assignment",
        entity_id=assignment_id,
        before=before_snapshot,
        after={
            "staff_profile_id": str(target.staff_profile_id),
            "slot_start": target.slot_start,
            "room_id": str(target.room_id),
        },
        at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)

    await db.flush()
    return tv.version_no

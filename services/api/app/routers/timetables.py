"""Timetables router — generate + GET under /api/v1/tenants/{tenantId}/timetables."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.assignment import Assignment
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.eligibility import Eligibility
from app.models.period_template import PeriodTemplate
from app.models.room import Room
from app.models.staff_availability_block import StaffAvailabilityBlock
from app.models.staff_profile import StaffProfile
from app.models.timetable_version import TimetableVersion
from app.schemas.timetable import AssignmentRead, GenerateRequest, GenerateResponse, TimetableRead

# Import solver — it lives in a sibling package, imported at call time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "solver"))

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/timetables", tags=["timetables"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_timetable(
    tenantId: UUID,
    body: GenerateRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Phase 1: synchronous single-cohort generation."""
    from solver.data_types import (
        SolverInput, FacultyData, CourseData, CohortData,
        RoomData, EligibilityData, PeriodSlot, BlockedSlot,
    )
    from solver.model import solve
    from solver.conflict_checker import check_all

    # Load master data
    cohort_result = await db.execute(select(Cohort).where(Cohort.id == body.cohort_id))
    cohort = cohort_result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Cohort not found"}})

    # Eligibility for this cohort
    elig_result = await db.execute(select(Eligibility).where(Eligibility.cohort_id == body.cohort_id))
    eligibilities = list(elig_result.scalars().all())
    if not eligibilities:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "No eligibility records for this cohort"}})

    # Courses involved
    course_ids = list(set(e.course_id for e in eligibilities))
    courses_result = await db.execute(select(Course).where(Course.id.in_(course_ids)))
    courses = {c.id: c for c in courses_result.scalars().all()}

    # Faculty involved
    faculty_ids = list(set(e.staff_profile_id for e in eligibilities))
    faculty_result = await db.execute(select(StaffProfile).where(StaffProfile.id.in_(faculty_ids)))
    faculty = {f.id: f for f in faculty_result.scalars().all()}

    # Rooms
    rooms_result = await db.execute(select(Room))
    rooms = {r.id: r for r in rooms_result.scalars().all()}

    # Period templates
    pt_result = await db.execute(select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index))
    period_templates = list(pt_result.scalars().all())

    # Blocked slots
    blocked_result = await db.execute(
        select(StaffAvailabilityBlock).where(
            StaffAvailabilityBlock.staff_profile_id.in_(faculty_ids)
        )
    )
    blocked_slots = list(blocked_result.scalars().all())

    # Build solver input
    solver_faculty = []
    for fid, f in faculty.items():
        solver_faculty.append(FacultyData(
            id=str(fid),
            workload_cap_week=f.workload_cap_week,
            workload_cap_day=f.workload_cap_day,
        ))

    solver_courses = []
    for cid, c in courses.items():
        solver_courses.append(CourseData(
            id=str(cid),
            type=c.type,
            hours_per_week=c.hours_per_week,
            block_size=c.block_size,
            required_equipment_tags=c.required_equipment_tags or [],
        ))

    solver_cohorts = [CohortData(id=str(cohort.id), name=cohort.name)]

    solver_rooms = []
    for rid, r in rooms.items():
        solver_rooms.append(RoomData(
            id=str(rid),
            type=r.type,
            capacity=r.capacity,
            equipment_tags=r.equipment_tags or [],
        ))

    solver_elig = []
    for e in eligibilities:
        solver_elig.append(EligibilityData(
            faculty_id=str(e.staff_profile_id),
            course_id=str(e.course_id),
            cohort_id=str(e.cohort_id),
        ))

    # Build period slots: each (weekday, period_index) → a unique integer slot
    slots_by_day: dict[int, list[int]] = {}
    slot_index = 0
    slot_map: dict[tuple[int, int], int] = {}
    for pt in period_templates:
        slot_map[(pt.weekday, pt.period_index)] = slot_index
        slots_by_day.setdefault(pt.weekday, []).append(slot_index)
        slot_index += 1

    period_slots = [
        PeriodSlot(slot_index=slot_map[(pt.weekday, pt.period_index)], weekday=pt.weekday, period_index=pt.period_index)
        for pt in period_templates
    ]

    solver_blocked = []
    for b in blocked_slots:
        key = (b.weekday, b.period_index)
        if key in slot_map:
            solver_blocked.append(BlockedSlot(
                faculty_id=str(b.staff_profile_id),
                slot_index=slot_map[key],
            ))

    solver_input = SolverInput(
        faculty=solver_faculty,
        courses=solver_courses,
        cohorts=solver_cohorts,
        rooms=solver_rooms,
        eligibility=solver_elig,
        period_slots=period_slots,
        blocked_slots=solver_blocked,
        slots_per_day=slots_by_day,
        num_slots=slot_index,
    )

    # Solve
    result = solve(solver_input)
    if result is None:
        raise HTTPException(status_code=422, detail={
            "error": {"code": "INFEASIBLE_CONFIGURATION", "message": "No feasible timetable found for this configuration", "details": {}}
        })

    # Verify independently (invariant #2)
    violations = check_all(result, solver_input)

    # Store results
    tv = TimetableVersion(tenant_id=tenantId, term_id=body.term_id, state="draft")
    db.add(tv)
    await db.flush()

    for a in result:
        assignment = Assignment(
            tenant_id=tenantId,
            timetable_version_id=tv.id,
            staff_profile_id=UUID(a.faculty_id),
            course_id=UUID(a.course_id),
            cohort_id=UUID(a.cohort_id),
            room_id=UUID(a.room_id),
            slot_start=a.slot_index,
            slot_span=a.slot_span,
        )
        db.add(assignment)

    await db.commit()
    await db.refresh(tv)

    return GenerateResponse(
        timetable_version_id=tv.id,
        status="draft",
        violations=[{"h_code": v.h_code, "message": v.message} for v in violations],
    )


@router.get("/{versionId}", response_model=TimetableRead)
async def get_timetable(
    tenantId: UUID,
    versionId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
):
    tv_result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = tv_result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})

    assign_result = await db.execute(
        select(Assignment).where(Assignment.timetable_version_id == versionId)
    )
    assignments = list(assign_result.scalars().all())

    return TimetableRead(
        id=tv.id,
        tenant_id=tv.tenant_id,
        state=tv.state,
        version_no=tv.version_no,
        assignments=[AssignmentRead.model_validate(a) for a in assignments],
    )

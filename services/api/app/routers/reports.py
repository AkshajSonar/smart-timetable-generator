"""Reports router — GET under /api/v1/tenants/{tenantId}/reports."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.core.tenant_context import set_tenant_context
from app.models.assignment import Assignment
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.eligibility import Eligibility
from app.models.staff_profile import StaffProfile
from app.models.timetable_version import TimetableVersion
from app.schemas.report import LoadVerificationReport, LoadVerificationItem

from app.rbac.dependencies import require_role

router = APIRouter(
    prefix="/api/v1/tenants/{tenantId}/reports",
    tags=["reports"],
    dependencies=[Depends(require_role(["institution_admin", "department_head", "reviewer"]))]
)


@router.get("/verification", response_model=LoadVerificationReport)
async def get_verification_report(
    tenantId: UUID,
    version_id: UUID = Query(..., description="The ID of the timetable version to verify"),
    db: AsyncSession = Depends(set_tenant_context),
):
    """Auto-generated load-verification report (FR-8.4).
    
    Verifies that the generated assignments in a timetable version match
    the expected workload for both faculty and cohorts.
    """
    # Verify version exists
    tv = await db.execute(select(TimetableVersion).where(TimetableVersion.id == version_id))
    if not tv.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})

    # Fetch required hours per (course, cohort/batch)
    elig_res = await db.execute(select(Eligibility))
    eligibilities = list(elig_res.scalars().all())

    course_ids = list(set(e.course_id for e in eligibilities))
    courses_res = await db.execute(select(Course).where(Course.id.in_(course_ids)))
    courses = {c.id: c for c in courses_res.scalars().all()}

    # Calculate required load for faculty
    faculty_required: dict[UUID, int] = defaultdict(int)
    for e in eligibilities:
        course = courses.get(e.course_id)
        if course:
            faculty_required[e.staff_profile_id] += course.hours_per_week
            
    # Calculate required load for cohorts (only count distinct courses for a cohort)
    cohort_required: dict[UUID, int] = defaultdict(int)
    cohort_course_seen = set()
    for e in eligibilities:
        course = courses.get(e.course_id)
        if course and (e.cohort_id, e.course_id) not in cohort_course_seen:
            cohort_required[e.cohort_id] += course.hours_per_week
            cohort_course_seen.add((e.cohort_id, e.course_id))

    # Fetch assignments
    assign_res = await db.execute(select(Assignment).where(Assignment.timetable_version_id == version_id))
    assignments = list(assign_res.scalars().all())

    faculty_scheduled: dict[UUID, int] = defaultdict(int)
    cohort_scheduled: dict[UUID, int] = defaultdict(int)
    for a in assignments:
        faculty_scheduled[a.staff_profile_id] += a.slot_span
        cohort_scheduled[a.cohort_id] += a.slot_span

    # Fetch names
    faculty_ids = list(faculty_required.keys()) + list(faculty_scheduled.keys())
    staff_res = await db.execute(select(StaffProfile).where(StaffProfile.id.in_(list(set(faculty_ids)))))
    staff_profiles = {s.id: f"Faculty {s.id}" for s in staff_res.scalars().all()}  # Note: Name is on identity usually, but for report we might mock or join

    cohort_ids = list(cohort_required.keys()) + list(cohort_scheduled.keys())
    cohort_res = await db.execute(select(Cohort).where(Cohort.id.in_(list(set(cohort_ids)))))
    cohorts = {c.id: c.name for c in cohort_res.scalars().all()}

    # Build report
    faculty_items = []
    for fid in set(faculty_ids):
        req = faculty_required.get(fid, 0)
        sch = faculty_scheduled.get(fid, 0)
        faculty_items.append(LoadVerificationItem(
            id=fid,
            name=staff_profiles.get(fid, str(fid)),
            required_hours=req,
            scheduled_hours=sch,
            difference=sch - req
        ))
        
    cohort_items = []
    for cid in set(cohort_ids):
        req = cohort_required.get(cid, 0)
        sch = cohort_scheduled.get(cid, 0)
        cohort_items.append(LoadVerificationItem(
            id=cid,
            name=cohorts.get(cid, str(cid)),
            required_hours=req,
            scheduled_hours=sch,
            difference=sch - req
        ))

    return LoadVerificationReport(
        faculty_load=faculty_items,
        cohort_load=cohort_items
    )

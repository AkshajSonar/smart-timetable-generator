from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.student_profile import StudentProfile
from app.models.batch_membership import BatchMembership
from app.models.enrollment_record import EnrollmentRecord
from app.models.elective_section import ElectiveSection
from app.models.assignment import Assignment
from app.schemas.student import StudentRead
from app.schemas.timetable import PublishedScheduleResponse
from app.schemas.common import PaginatedResponse
from app.core.auth import verify_jwt
from app.models.staff_profile import StaffProfile
from app.rbac.dependencies import require_role

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/students", tags=["students"])


@router.get("", response_model=PaginatedResponse[StudentRead])
async def list_students(
    tenantId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head", "reviewer"]))
):
    result = await db.execute(select(StudentProfile))
    items = list(result.scalars().all())
    return PaginatedResponse(
        items=[StudentRead.model_validate(s) for s in items],
        next_cursor=None
    )


@router.get("/{studentId}/timetable", response_model=list[PublishedScheduleResponse])
async def get_student_timetable(
    tenantId: UUID,
    studentId: UUID,
    versionId: UUID = Query(..., description="The timetable version ID to fetch assignments for"),
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _role: None = Depends(require_role(["institution_admin", "department_head", "reviewer", "student"]))
):
    # Verify student exists
    student_result = await db.execute(select(StudentProfile).where(StudentProfile.id == studentId))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Student not found"}})

    # Ownership check: if caller is a student (and not accessing their own profile), check if they have admin roles
    if student.identity_id != identity_id:
        staff_res = await db.execute(
            select(StaffProfile.roles).where(
                StaffProfile.identity_id == identity_id,
                StaffProfile.tenant_id == tenantId
            )
        )
        roles = staff_res.scalar_one_or_none() or []
        allowed_admin = {"institution_admin", "department_head", "reviewer"}
        if not allowed_admin.intersection(roles):
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Cannot access another student's timetable"}})

    # Fetch version state
    from app.models.timetable_version import TimetableVersion
    tv_result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = tv_result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Version not found"}})

    # Fetch student's specific batches
    bm_result = await db.execute(
        select(BatchMembership).where(BatchMembership.student_profile_id == studentId)
    )
    student_batches = {bm.batch_id for bm in bm_result.scalars().all()}

    # Fetch student's enrolled electives -> map to course_ids
    enr_result = await db.execute(
        select(EnrollmentRecord.elective_section_id).where(EnrollmentRecord.student_profile_id == studentId)
    )
    enrolled_section_ids = list(enr_result.scalars().all())
    
    student_elective_courses = set()
    if enrolled_section_ids:
        es_result = await db.execute(
            select(ElectiveSection.course_id).where(ElectiveSection.id.in_(enrolled_section_ids))
        )
        student_elective_courses = set(es_result.scalars().all())

    # Fetch dual-routed schedules
    from app.services.schedule_mapper import get_dual_routed_schedules
    all_schedules = await get_dual_routed_schedules(db, versionId, tv.state, 'class')

    from app.models.course import Course
    course_result = await db.execute(select(Course))
    courses = {c.id: c for c in course_result.scalars().all()}

    student_schedules = []
    for a in all_schedules:
        course = courses.get(a.course_id)
        if not course:
            continue
            
        if a.cohort_id != student.cohort_id:
            if course.type == "elective" and course.id in student_elective_courses:
                pass 
            else:
                continue
                
        if a.batch_id is not None:
            if a.batch_id in student_batches:
                student_schedules.append(a)
        else:
            if course.type == "elective":
                if course.id in student_elective_courses:
                    student_schedules.append(a)
            else:
                student_schedules.append(a)

    return student_schedules

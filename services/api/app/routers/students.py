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
from app.schemas.timetable import AssignmentRead
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/students", tags=["students"])


@router.get("", response_model=PaginatedResponse[StudentRead])
async def list_students(
    tenantId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
):
    result = await db.execute(select(StudentProfile))
    items = list(result.scalars().all())
    return PaginatedResponse(
        items=[StudentRead.model_validate(s) for s in items],
        next_cursor=None
    )


@router.get("/{studentId}/timetable", response_model=list[AssignmentRead])
async def get_student_timetable(
    tenantId: UUID,
    studentId: UUID,
    versionId: UUID = Query(..., description="The timetable version ID to fetch assignments for"),
    db: AsyncSession = Depends(set_tenant_context),
):
    # Verify student exists
    student_result = await db.execute(select(StudentProfile).where(StudentProfile.id == studentId))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Student not found"}})

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

    # Fetch all assignments for this version
    assign_result = await db.execute(
        select(Assignment).where(Assignment.timetable_version_id == versionId)
    )
    all_assignments = list(assign_result.scalars().all())

    # Filter assignments for this specific student
    # A student attends an assignment if:
    # 1. It is for their cohort, AND it's not a batch assignment (batch_id is None) -> (Wait, only if it's not an elective they are NOT enrolled in. Or rather, if it's an elective, they must be enrolled)
    # 2. It is for their cohort, AND it's a batch assignment, AND they are in that batch.
    
    from app.models.course import Course
    course_result = await db.execute(select(Course))
    courses = {c.id: c for c in course_result.scalars().all()}

    student_assignments = []
    for a in all_assignments:
        # First, it must be for their cohort OR they are enrolled in the elective (wait, electives use the same cohort_id in our model, or they could use a derived cohort)
        # Assuming the assignment's cohort_id matches the student's cohort_id, OR the assignment is for an elective course they are enrolled in.
        
        course = courses.get(a.course_id)
        if not course:
            continue
            
        if a.cohort_id != student.cohort_id:
            # If it's a different cohort, the only way they attend is if it's an elective they are enrolled in 
            # (if electives use derived cohorts).
            if course.type == "elective" and course.id in student_elective_courses:
                pass # they attend
            else:
                continue
                
        # If it's for their cohort (or an elective they are in)
        if a.batch_id is not None:
            # It's a batch assignment
            if a.batch_id in student_batches:
                student_assignments.append(a)
        else:
            # It's a whole-cohort assignment
            if course.type == "elective":
                if course.id in student_elective_courses:
                    student_assignments.append(a)
            else:
                student_assignments.append(a)

    return [AssignmentRead.model_validate(a) for a in student_assignments]

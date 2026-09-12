from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.student_profile import StudentProfile
from app.models.course import Course
from app.models.elective_section import ElectiveSection
from app.models.enrollment_record import EnrollmentRecord
from app.schemas.import_data import EnrollmentImportRequest, ImportResult

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/import", tags=["import"])


@router.post("/enrollment", response_model=ImportResult)
async def import_enrollment(
    tenantId: UUID,
    body: EnrollmentImportRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Import pre-resolved elective enrollment for a term."""
    success_count = 0
    errors = []

    # Fetch all students and map by external_student_code
    stud_result = await db.execute(select(StudentProfile))
    students_by_code = {s.external_student_code: s for s in stud_result.scalars().all()}

    # Fetch elective sections and map by external_id
    es_result = await db.execute(select(ElectiveSection).where(ElectiveSection.external_id.is_not(None)))
    es_by_external_id = {es.external_id: es for es in es_result.scalars().all()}

    # Pre-fetch existing enrollments to avoid duplicates
    enr_result = await db.execute(select(EnrollmentRecord))
    existing_enr = {(e.student_profile_id, e.elective_section_id) for e in enr_result.scalars().all()}

    for row in body.rows:
        row_id = f"{row.student_external_id} - {row.elective_section_external_id}"
        
        student = students_by_code.get(row.student_external_id)
        if not student:
            errors.append({"row": row_id, "error": f"Student with external_id {row.student_external_id} not found"})
            continue

        es = es_by_external_id.get(row.elective_section_external_id)
        if not es:
            errors.append({"row": row_id, "error": f"Elective section with external_id {row.elective_section_external_id} not found"})
            continue

        if (student.id, es.id) in existing_enr:
            # Already enrolled
            continue

        # Check capacity
        current_enrollments = sum(1 for e in existing_enr if e[1] == es.id)
        if current_enrollments >= es.capacity:
            errors.append({"row": row_id, "error": f"Elective section {row.elective_section_external_id} is at capacity ({es.capacity})"})
            continue

        # Add new enrollment
        new_enr = EnrollmentRecord(
            tenant_id=tenantId,
            student_profile_id=student.id,
            elective_section_id=es.id
        )
        db.add(new_enr)
        existing_enr.add((student.id, es.id))  # Update local cache
        success_count += 1

    await db.commit()

    return ImportResult(success_count=success_count, errors=errors)

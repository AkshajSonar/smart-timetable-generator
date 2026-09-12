from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.student_profile import StudentProfile
from app.models.course import Course
from app.models.room import Room
from app.models.staff_profile import StaffProfile
from app.models.identity import Identity
from app.models.department import Department
from app.models.elective_section import ElectiveSection
from app.models.enrollment_record import EnrollmentRecord
from app.schemas.import_data import (
    EnrollmentImportRequest, FacultyImportRequest, CourseImportRequest, RoomImportRequest, ImportResult
)

from app.rbac.dependencies import require_role
router = APIRouter(
    dependencies=[Depends(require_role(["institution_admin"]))],
    prefix="/api/v1/tenants/{tenantId}/import", tags=["import"])


@router.post("/enrollment", response_model=ImportResult)
async def import_enrollment(
    tenantId: UUID,
    body: EnrollmentImportRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Import pre-resolved elective enrollment for a term (FR-3.1)."""
    success_count = 0
    errors = []

    stud_result = await db.execute(select(StudentProfile))
    students_by_code = {s.external_student_code: s for s in stud_result.scalars().all()}

    es_result = await db.execute(select(ElectiveSection).where(ElectiveSection.external_id.is_not(None)))
    es_by_external_id = {es.external_id: es for es in es_result.scalars().all()}

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
            continue

        current_enrollments = sum(1 for e in existing_enr if e[1] == es.id)
        if current_enrollments >= es.capacity:
            errors.append({"row": row_id, "error": f"Elective section {row.elective_section_external_id} is at capacity ({es.capacity})"})
            continue

        new_enr = EnrollmentRecord(
            tenant_id=tenantId,
            student_profile_id=student.id,
            elective_section_id=es.id
        )
        db.add(new_enr)
        existing_enr.add((student.id, es.id))
        success_count += 1

    await db.commit()
    return ImportResult(success_count=success_count, errors=errors)


@router.post("/faculty", response_model=ImportResult)
async def import_faculty(
    tenantId: UUID,
    body: FacultyImportRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Bulk import faculty profiles (FR-2.2)."""
    success_count = 0
    errors = []

    identities_q = await db.execute(select(Identity))
    existing_emails = {i.email: i for i in identities_q.scalars().all()}

    for row in body.rows:
        row_id = row.email or row.full_name
        if not row.email or not row.full_name:
            errors.append({"row": row_id, "error": "Email and full_name are required"})
            continue

        identity = existing_emails.get(row.email)
        if not identity:
            identity = Identity(
                email=row.email,
                full_name=row.full_name,
                auth_provider_ref=f"imported:{row.email}"
            )
            db.add(identity)
            await db.flush()
            existing_emails[row.email] = identity

        sp_q = await db.execute(select(StaffProfile).where(StaffProfile.identity_id == identity.id, StaffProfile.tenant_id == tenantId))
        sp = sp_q.scalar_one_or_none()
        if not sp:
            sp = StaffProfile(
                tenant_id=tenantId,
                identity_id=identity.id,
                employment_type=row.employment_type or "full_time",
                workload_cap_week=row.workload_cap_week,
                workload_cap_day=row.workload_cap_day,
                roles=["faculty"]
            )
            db.add(sp)
            success_count += 1

    await db.commit()
    return ImportResult(success_count=success_count, errors=errors)


@router.post("/courses", response_model=ImportResult)
async def import_courses(
    tenantId: UUID,
    body: CourseImportRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Bulk import courses (FR-2.2)."""
    success_count = 0
    errors = []

    dept_q = await db.execute(select(Department).where(Department.tenant_id == tenantId))
    dept = dept_q.scalars().first()
    if not dept:
        dept = Department(tenant_id=tenantId, name="General Academics")
        db.add(dept)
        await db.flush()

    existing_courses_q = await db.execute(select(Course).where(Course.tenant_id == tenantId))
    existing_names = {c.name.lower() for c in existing_courses_q.scalars().all()}

    for row in body.rows:
        if not row.name:
            errors.append({"row": "Unknown", "error": "Course name is required"})
            continue

        if row.name.lower() in existing_names:
            continue

        c = Course(
            tenant_id=tenantId,
            department_id=dept.id,
            name=row.name,
            type=row.type if row.type in ["core", "elective", "lab"] else "core",
            hours_per_week=row.hours_per_week,
            block_size=row.block_size
        )
        db.add(c)
        existing_names.add(row.name.lower())
        success_count += 1

    await db.commit()
    return ImportResult(success_count=success_count, errors=errors)


@router.post("/rooms", response_model=ImportResult)
async def import_rooms(
    tenantId: UUID,
    body: RoomImportRequest,
    db: AsyncSession = Depends(set_tenant_context),
):
    """Bulk import rooms & labs (FR-2.2)."""
    success_count = 0
    errors = []

    existing_rooms_q = await db.execute(select(Room).where(Room.tenant_id == tenantId))
    existing_names = {r.name.lower() for r in existing_rooms_q.scalars().all()}

    for row in body.rows:
        if not row.name:
            errors.append({"row": "Unknown", "error": "Room name is required"})
            continue

        if row.name.lower() in existing_names:
            continue

        r = Room(
            tenant_id=tenantId,
            name=row.name,
            type=row.room_type if row.room_type in ["lecture_hall", "lab", "seminar", "auditorium"] else "lecture_hall",
            capacity=row.capacity,
            equipment_tags=row.equipment_tags or []
        )
        db.add(r)
        existing_names.add(row.name.lower())
        success_count += 1

    await db.commit()
    return ImportResult(success_count=success_count, errors=errors)

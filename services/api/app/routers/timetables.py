"""Timetables router — generate + GET under /api/v1/tenants/{tenantId}/timetables."""

from uuid import UUID

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_jwt
from app.core.tenant_context import set_tenant_context
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
from app.schemas.timetable import (
    AssignmentRead, EditAssignmentRequest, EditAssignmentResponse,
    GenerateRequest, GenerateResponse, TimetableRead, StateTransitionRequest
)

# Import solver — it lives in a sibling package, imported at call time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "solver"))

from app.rbac.dependencies import require_role
router = APIRouter(prefix="/api/v1/tenants/{tenantId}/timetables", tags=["timetables"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_timetable(
    tenantId: UUID,
    body: GenerateRequest,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
):
    """Phase 1: synchronous single-cohort generation."""
    from solver.data_types import (
        SolverInput, FacultyData, CourseData, CohortData,
        BatchData, RoomData, EligibilityData, PeriodSlot, BlockedSlot,
    )
    from solver.model import solve
    from solver.conflict_checker import check_all

    # Load all master data for the tenant
    cohort_result = await db.execute(select(Cohort))
    cohorts = list(cohort_result.scalars().all())
    if not cohorts:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "No cohorts found for tenant"}})

    # Batches
    batch_result = await db.execute(select(Batch))
    batches = list(batch_result.scalars().all())

    # Eligibility for all cohorts/batches
    elig_result = await db.execute(select(Eligibility))
    eligibilities = list(elig_result.scalars().all())
    if not eligibilities:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "No eligibility records found"}})

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

    solver_cohorts = [CohortData(id=str(c.id), name=c.name) for c in cohorts]
    
    solver_batches = [BatchData(
        id=str(b.id),
        label=b.label,
        cohort_id=str(b.cohort_id),
        course_id=str(b.course_id),
    ) for b in batches]

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
            cohort_id=str(e.batch_id) if e.batch_id else str(e.cohort_id),
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

    room_type_counts = {}
    for r in rooms.values():
        room_type_counts[r.type] = room_type_counts.get(r.type, 0) + 1

    # Load Phase 3 Student Data
    from app.models.student_profile import StudentProfile
    from app.models.batch_membership import BatchMembership
    from app.models.enrollment_record import EnrollmentRecord
    from app.models.elective_section import ElectiveSection
    from solver.data_types import StudentData, StudentCourseData

    stud_result = await db.execute(select(StudentProfile))
    db_students = list(stud_result.scalars().all())

    bm_result = await db.execute(select(BatchMembership))
    db_batch_memberships = list(bm_result.scalars().all())

    enr_result = await db.execute(select(EnrollmentRecord))
    db_enrollments = list(enr_result.scalars().all())

    es_result = await db.execute(select(ElectiveSection))
    db_elective_sections = {es.id: es for es in es_result.scalars().all()}

    # Map student -> batches
    student_batches: dict[UUID, list[UUID]] = {}
    for bm in db_batch_memberships:
        student_batches.setdefault(bm.student_profile_id, []).append(bm.batch_id)

    # Map student -> elective courses
    student_electives: dict[UUID, list[UUID]] = {}
    for enr in db_enrollments:
        es = db_elective_sections.get(enr.elective_section_id)
        if es:
            student_electives.setdefault(enr.student_profile_id, []).append(es.course_id)

    # Build solver_students
    solver_students = []
    # Create a quick lookup for batch_id -> course_id to know which course the batch belongs to
    batch_to_course = {b.id: b.course_id for b in batches}
    
    for s in db_students:
        s_courses = []
        
        # 1. Core courses for this student's cohort
        # Any eligibility for this cohort that is NOT batch-level and NOT an elective the student ISN'T in
        # Actually, it's easier: check all eligibilities for this student's cohort.
        for e in eligibilities:
            # We only care about courses for this student's cohort
            # Wait, `e.cohort_id` could be the parent cohort.
            if e.cohort_id != s.cohort_id:
                continue

            course = courses.get(e.course_id)
            if not course:
                continue

            # If it's a batch-split course (there are batches for it in this cohort)
            # The student is only enrolled if they have a batch membership for it
            batches_for_course = [b for b in batches if b.course_id == e.course_id and b.cohort_id == s.cohort_id]
            
            if batches_for_course:
                # Student must be in one of these batches to take the course
                student_bms = student_batches.get(s.id, [])
                for b in batches_for_course:
                    if b.id in student_bms:
                        s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=str(b.id)))
                        break
            else:
                # It's a whole-cohort course
                if course.type == "elective":
                    # Check if student is enrolled
                    if course.id in student_electives.get(s.id, []):
                        s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=None))
                else:
                    # Core course
                    s_courses.append(StudentCourseData(course_id=str(course.id), cohort_id=str(s.cohort_id), batch_id=None))

        solver_students.append(StudentData(id=str(s.id), courses=s_courses))

    # Load locked assignments if generating based on a prior version (FR-9.2)
    locked_results = []
    
    if not getattr(body, "prior_version_id", None) and body.term_id:
        from app.models.timetable_version import TimetableVersion
        latest_version = await db.execute(
            select(TimetableVersion.id).where(
                TimetableVersion.tenant_id == tenantId,
                TimetableVersion.term_id == body.term_id
            ).order_by(TimetableVersion.version_no.desc()).limit(1)
        )
        body.prior_version_id = latest_version.scalar_one_or_none()

    if getattr(body, "prior_version_id", None):
        locked_query = await db.execute(
            select(Assignment).where(
                Assignment.timetable_version_id == body.prior_version_id,
                Assignment.is_locked == True
            )
        )
        for row in locked_query.scalars().all():
            locked_results.append(AssignmentResult(
                faculty_id=str(row.staff_profile_id),
                course_id=str(row.course_id),
                cohort_id=str(row.cohort_id),
                room_id=str(row.room_id),
                slot_index=row.slot_start,
                slot_span=row.slot_span,
                batch_id=str(row.batch_id) if row.batch_id else None
            ))

    # Fetch confirmed rules
    from app.models.constraint_rule import ConstraintRule
    from solver.data_types import RuleData
    rules_query = await db.execute(
        select(ConstraintRule).where(
            ConstraintRule.tenant_id == tenantId,
            ConstraintRule.status == "confirmed"
        )
    )
    solver_rules = [
        RuleData(
            rule_type=r.rule_type,
            scope=r.scope,
            target_id=str(r.target_id) if r.target_id else None,
            threshold=float(r.threshold) if r.threshold is not None else None,
            unit=r.unit,
            polarity=r.polarity,
            weight=float(r.weight) if r.weight is not None else None
        )
        for r in rules_query.scalars().all()
    ]
    
    solver_input = SolverInput(
        faculty=solver_faculty,
        courses=solver_courses,
        cohorts=solver_cohorts,
        batches=solver_batches,
        rooms=solver_rooms,
        eligibility=solver_elig,
        period_slots=period_slots,
        blocked_slots=solver_blocked,
        slots_per_day=slots_by_day,
        num_slots=slot_index,
        room_type_counts=room_type_counts,
        students=solver_students,
        locked_assignments=locked_results,
        rules=solver_rules,
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
            batch_id=UUID(a.batch_id) if a.batch_id else None,
        )
        db.add(assignment)

    await db.commit()

    return GenerateResponse(
        timetable_version_id=tv.id,
        status="draft",
        violations=[{"h_code": v.h_code, "message": v.message} for v in violations],
    )


@router.get("/{versionId}", response_model=TimetableRead)
async def get_timetable_version(
    tenantId: UUID,
    versionId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head", "reviewer", "faculty", "student"]))
):
    tv_result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = tv_result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})

    from app.services.schedule_mapper import get_dual_routed_schedules
    schedules = await get_dual_routed_schedules(db, versionId, tv.state, 'class')

    return TimetableRead(
        id=tv.id,
        tenant_id=tv.tenant_id,
        state=tv.state,
        version_no=tv.version_no,
        schedules=schedules,
    )


@router.post("/{versionId}/edit", response_model=EditAssignmentResponse)
async def edit_assignment(
    tenantId: UUID,
    versionId: UUID,
    body: EditAssignmentRequest,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
    identity_id: UUID = Depends(verify_jwt),
):
    """FR-9.1: Manual edit with live conflict re-validation.

    Delegates to app.services.edit_service.apply_assignment_edit which
    performs: version_no check → snapshot build → H1-H11 check_all →
    commit → audit_log write. The shared service is also called by
    substitution /confirm to avoid parallel reimplementation.
    """
    from app.services.edit_service import apply_assignment_edit

    new_version_no = await apply_assignment_edit(
        db,
        version_id=versionId,
        tenant_id=tenantId,
        assignment_id=body.assignment_id,
        version_no=body.version_no,
        new_staff_profile_id=body.staff_profile_id,
        new_room_id=body.room_id,
        new_slot_start=body.slot_start,
        actor_identity_id=identity_id,
        audit_action="edit",
        lock_cell=True,
    )
    
    await db.commit()
    return EditAssignmentResponse(
        assignment_id=body.assignment_id,
        new_version_no=new_version_no,
    )


@router.post("/{versionId}/approve")
async def approve_timetable(
    tenantId: UUID,
    versionId: UUID,
    body: StateTransitionRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["reviewer"])),
):
    from app.models.timetable_version import TimetableVersion
    from app.models.stubs import AuditLog

    result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})
    
    if tv.version_no != body.version_no:
        raise HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": f"Stale version_no. DB has {tv.version_no}"}})

    before_state = {"state": tv.state, "approved_by": str(tv.approved_by) if tv.approved_by else None}

    tv.approved_by = identity_id
    if tv.state == "draft":
        tv.state = "under_review"
    tv.version_no += 1

    after_state = {"state": tv.state, "approved_by": str(tv.approved_by)}

    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="approve",
        entity_type="timetable_version",
        entity_id=versionId,
        before=before_state,
        after=after_state,
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.commit()
    return {"status": "success", "new_version_no": tv.version_no}


@router.post("/{versionId}/publish")
async def publish_timetable(
    tenantId: UUID,
    versionId: UUID,
    body: StateTransitionRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["institution_admin"])),
):
    from app.models.timetable_version import TimetableVersion
    from app.models.stubs import AuditLog

    result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})
    
    if tv.version_no != body.version_no:
        raise HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": f"Stale version_no. DB has {tv.version_no}"}})

    if tv.approved_by is None:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "Must be approved before publish"}})

    before_state = {"state": tv.state}
    tv.state = "published"
    tv.version_no += 1
    after_state = {"state": tv.state}

    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="publish",
        entity_type="timetable_version",
        entity_id=versionId,
        before=before_state,
        after=after_state,
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    
    # "builds the CQRS-lite read models from the raw assignment rows per AGENTS.md §7"
    from app.models.assignment import Assignment
    from app.models.published_schedule import PublishedSchedule
    from app.models.staff_profile import StaffProfile
    from app.models.identity import Identity
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.room import Room

    # Delete any existing published records for this timetable_version_id
    await db.execute(
        PublishedSchedule.__table__.delete().where(PublishedSchedule.timetable_version_id == versionId)
    )

    # Fetch all assignments and denormalize
    assignments_query = await db.execute(
        select(Assignment).where(Assignment.timetable_version_id == versionId)
    )
    assignments = assignments_query.scalars().all()

    for assign in assignments:
        staff_q = await db.execute(
            select(Identity.full_name).join(StaffProfile, Identity.id == StaffProfile.identity_id)
            .where(StaffProfile.id == assign.staff_profile_id)
        )
        staff_name = staff_q.scalar_one_or_none()

        course_q = await db.execute(select(Course.name).where(Course.id == assign.course_id))
        course_name = course_q.scalar_one_or_none()

        cohort_q = await db.execute(select(Cohort.name).where(Cohort.id == assign.cohort_id))
        cohort_name = cohort_q.scalar_one_or_none()

        room_q = await db.execute(select(Room.name).where(Room.id == assign.room_id))
        room_name = room_q.scalar_one_or_none()

        batch_name = None
        if assign.batch_id:
            from app.models.batch import Batch
            batch_q = await db.execute(select(Batch.label).where(Batch.id == assign.batch_id))
            batch_name = batch_q.scalar_one_or_none()

        published_row = PublishedSchedule(
            tenant_id=tenantId,
            timetable_version_id=versionId,
            type='class',
            staff_profile_id=assign.staff_profile_id,
            cohort_id=assign.cohort_id,
            course_id=assign.course_id,
            room_id=assign.room_id,
            batch_id=assign.batch_id,
            staff_name=staff_name,
            cohort_name=cohort_name,
            course_name=course_name,
            room_name=room_name,
            batch_name=batch_name,
            slot_index=assign.slot_start,
            slot_span=assign.slot_span
        )
        db.add(published_row)
    
    # --- Notify all staff with assignments in this version (FR-11.1) ---
    from app.services.notifications import send_notification
    notified_identities: set = set()
    for assign in assignments:
        sp_identity_q = await db.execute(
            select(StaffProfile.identity_id).where(StaffProfile.id == assign.staff_profile_id)
        )
        sp_identity_id = sp_identity_q.scalar_one_or_none()
        if sp_identity_id and sp_identity_id not in notified_identities:
            notified_identities.add(sp_identity_id)
            await send_notification(
                db,
                tenant_id=tenantId,
                identity_id=sp_identity_id,
                subject="Timetable Published",
                body=f"The timetable (version {versionId}) has been published.",
            )

    await db.commit()
    return {"status": "success", "new_version_no": tv.version_no}

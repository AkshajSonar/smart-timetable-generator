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
    GenerateRequest, GenerateResponse, TimetableRead, StateTransitionRequest,
    WhatIfResponse
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
    from solver.model import solve
    from solver.conflict_checker import check_all
    from app.services.generation import build_solver_input

    solver_input, _, _, _, _, _ = await build_solver_input(
        db, tenantId, term_id=body.term_id, prior_version_id=getattr(body, "prior_version_id", None)
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


@router.post("/generate/what-if", response_model=WhatIfResponse)
async def what_if_simulation(
    tenantId: UUID,
    body: GenerateRequest,
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
):
    """Part 2: Synchronous what-if simulation (no DB persistence)."""
    from solver.model import solve
    from solver.conflict_checker import check_all
    from app.services.generation import build_solver_input
    from app.schemas.timetable import PublishedScheduleResponse

    solver_input, courses, cohorts, batches, rooms, faculty_names = await build_solver_input(
        db, tenantId, term_id=body.term_id, prior_version_id=getattr(body, "prior_version_id", None)
    )

    # Solve
    result = solve(solver_input)
    if result is None:
        raise HTTPException(status_code=422, detail={
            "error": {"code": "INFEASIBLE_CONFIGURATION", "message": "No feasible timetable found for this configuration", "details": {}}
        })

    # Verify independently (invariant #2)
    violations = check_all(result, solver_input)

    # Map solver output to PublishedScheduleResponse
    import uuid
    assignments = []
    for a in result:
        staff_id = UUID(a.faculty_id)
        course_id = UUID(a.course_id)
        cohort_id = UUID(a.cohort_id)
        room_id = UUID(a.room_id)
        batch_id = UUID(a.batch_id) if a.batch_id else None

        assignments.append(PublishedScheduleResponse(
            id=uuid.uuid4(),
            type="class",
            staff_profile_id=staff_id,
            cohort_id=cohort_id,
            course_id=course_id,
            room_id=room_id,
            batch_id=batch_id,
            staff_name=faculty_names.get(staff_id),
            cohort_name=cohorts[cohort_id].name if cohort_id in cohorts else None,
            course_name=courses[course_id].name if course_id in courses else None,
            room_name=rooms[room_id].name if room_id in rooms else None,
            batch_name=batches[batch_id].label if batch_id and batch_id in batches else None,
            slot_index=a.slot_index,
            slot_span=a.slot_span,
            is_locked=False
        ))

    return WhatIfResponse(
        status="success",
        violations=[{"h_code": v.h_code, "message": v.message} for v in violations],
        assignments=assignments
    )



@router.get("/{versionId}", response_model=TimetableRead)
async def get_timetable_version(
    tenantId: UUID,
    versionId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    _role: set[str] = Depends(require_role(["institution_admin", "department_head", "reviewer", "faculty", "student"]))
):
    tv_result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == versionId))
    tv = tv_result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Timetable version not found"}})
        
    if not ("institution_admin" in _role or "department_head" in _role or "reviewer" in _role):
        if tv.state != "published":
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Only admins can view draft schedules"}})

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

"""Substitutions router — FR-10.x two-step suggest/confirm flow.

POST /api/v1/tenants/{tenantId}/substitutions
    Records absence + returns ranked eligible substitutes; persists a
    SubstitutionLog row (status='suggested') so the confirm endpoint has a
    stable ID to reference.

POST /api/v1/tenants/{tenantId}/substitutions/{substitutionId}/confirm
    Confirms a suggested substitution. Re-validates availability at confirm
    time (not trusted from suggest snapshot — optimistic concurrency).
    Calls the shared apply_assignment_edit service to apply the edit with
    H1-H11 re-validation and version_no staleness check.

Tie-break rule (§31 free choice):
    Candidates are ranked least-loaded-first (fewest existing Assignment
    rows in the current TimetableVersion for the tenant). Rationale: spreads
    substitution load evenly across available staff rather than skewing toward
    most-familiar (which can't be measured from current schema alone).
"""

from __future__ import annotations

from datetime import datetime, timezone, date as date_type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_jwt
from app.core.tenant_context import set_tenant_context
from app.models.assignment import Assignment
from app.models.eligibility import Eligibility
from app.models.period_template import PeriodTemplate
from app.models.staff_availability_block import StaffAvailabilityBlock
from app.models.staff_profile import StaffProfile
from app.models.timetable_version import TimetableVersion
from app.models.stubs import AuditLog, SubstitutionLog
from app.rbac.dependencies import require_role

router = APIRouter(
    prefix="/api/v1/tenants/{tenantId}/substitutions",
    tags=["substitutions"],
)


# ---------- Schemas ----------

class SubstitutionSuggestRequest(BaseModel):
    absent_staff_profile_id: UUID
    assignment_id: UUID
    date: date_type
    version_no: int


class SubstitutionCandidate(BaseModel):
    staff_profile_id: UUID
    identity_id: UUID | None = None
    current_load: int  # number of existing assignments in version (least = best)


class SubstitutionSuggestResponse(BaseModel):
    substitution_id: UUID
    candidates: list[SubstitutionCandidate]


class SubstitutionConfirmRequest(BaseModel):
    substitute_staff_profile_id: UUID
    version_no: int


class SubstitutionConfirmResponse(BaseModel):
    substitution_id: UUID
    new_version_no: int


# ---------- Endpoints ----------

@router.post("", response_model=SubstitutionSuggestResponse)
async def suggest_substitution(
    tenantId: UUID,
    body: SubstitutionSuggestRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
):
    """FR-10.1 / FR-10.2: Record absence and return ranked eligible substitutes.

    Persists a SubstitutionLog(status='suggested') row. Its id is the
    substitutionId used in the confirm endpoint — prevents the path ID
    from pointing at a resource that nothing produced.
    """
    # 1. Load the assignment being covered
    assignment = (await db.execute(
        select(Assignment).where(Assignment.id == body.assignment_id)
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Assignment not found"}},
        )

    # Verify the absent staff is actually assigned to this slot
    if assignment.staff_profile_id != body.absent_staff_profile_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "absent_staff_profile_id does not match assignment's staff_profile_id",
                }
            },
        )

    # 2. Derive weekday from the assignment's slot_start → PeriodTemplate
    period_row = (await db.execute(
        select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index)
    )).scalars().all()

    if assignment.slot_start < len(period_row):
        slot_weekday = period_row[assignment.slot_start].weekday
    else:
        slot_weekday = 0  # fallback; edge case with no period templates

    # 3. Find eligible candidates (H5: eligibility for course+cohort)
    elig_rows = (await db.execute(
        select(Eligibility.staff_profile_id).where(
            Eligibility.course_id == assignment.course_id,
            Eligibility.cohort_id == assignment.cohort_id,
            Eligibility.staff_profile_id != body.absent_staff_profile_id,
        )
    )).scalars().all()
    eligible_ids = set(elig_rows)

    if not eligible_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "No eligible substitutes found for this course/cohort combination",
                }
            },
        )

    # 4. Filter: remove candidates blocked at this weekday slot (H4)
    blocked_ids = set((await db.execute(
        select(StaffAvailabilityBlock.staff_profile_id).where(
            StaffAvailabilityBlock.staff_profile_id.in_(eligible_ids),
            StaffAvailabilityBlock.weekday == slot_weekday,
        )
    )).scalars().all())
    eligible_ids -= blocked_ids

    # 5. Filter: remove candidates already assigned in this slot (H1)
    # Same slot_start on any assignment in the current version
    tv_result = (await db.execute(
        select(TimetableVersion).where(
            TimetableVersion.tenant_id == tenantId,
            TimetableVersion.state.in_(["draft", "under_review"]),
        ).order_by(TimetableVersion.version_no.desc())
    )).scalars().first()
    if tv_result:
        occupied_at_slot = set((await db.execute(
            select(Assignment.staff_profile_id).where(
                Assignment.timetable_version_id == tv_result.id,
                Assignment.staff_profile_id.in_(eligible_ids),
                Assignment.slot_start == assignment.slot_start,
            )
        )).scalars().all())
        eligible_ids -= occupied_at_slot

    if not eligible_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "All eligible substitutes are blocked or already assigned at this slot",
                }
            },
        )

    # 6. Rank by least-loaded-first (§31 tie-break: fewest existing assignments)
    load_rows = (await db.execute(
        select(Assignment.staff_profile_id, func.count().label("load")).where(
            Assignment.timetable_version_id == (tv_result.id if tv_result else None),
            Assignment.staff_profile_id.in_(eligible_ids),
        ).group_by(Assignment.staff_profile_id)
    )).all()
    load_map: dict[UUID, int] = {r.staff_profile_id: r.load for r in load_rows}

    all_profiles = (await db.execute(
        select(StaffProfile).where(StaffProfile.id.in_(eligible_ids))
    )).scalars().all()

    # H8: filter out candidates that would exceed workload caps
    # (simple check: daily cap — more precise weekly check omitted for now as week-wide load query
    #  would require date-scoped assignments which we don't store; daily cap is the binding constraint)
    candidates = []
    for sp in all_profiles:
        current_load = load_map.get(sp.id, 0)
        # Daily cap: count same-day assignments (rough proxy by slot_weekday)
        day_load_q = await db.execute(
            select(func.count()).select_from(Assignment).join(
                PeriodTemplate,
                Assignment.slot_start == PeriodTemplate.period_index,
            ).where(
                Assignment.staff_profile_id == sp.id,
                Assignment.timetable_version_id == (tv_result.id if tv_result else None),
                PeriodTemplate.weekday == slot_weekday,
            )
        )
        day_load = day_load_q.scalar() or 0
        if day_load >= sp.workload_cap_day:
            continue  # H8 violation — skip
        if current_load >= sp.workload_cap_week:
            continue  # H8 violation — skip
        candidates.append(SubstitutionCandidate(
            staff_profile_id=sp.id,
            identity_id=sp.identity_id,
            current_load=current_load,
        ))

    if not candidates:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "No eligible and available candidates found",
                }
            },
        )

    # Sort least-loaded-first
    candidates.sort(key=lambda c: c.current_load)

    # 7. Persist SubstitutionLog with status='suggested'
    sub_log = SubstitutionLog(
        tenant_id=tenantId,
        original_staff_profile_id=body.absent_staff_profile_id,
        substitute_staff_profile_id=None,  # set at confirm time
        assignment_id=body.assignment_id,
        date=body.date,
        status="suggested",
    )
    db.add(sub_log)

    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="suggest_substitution",
        entity_type="assignment",
        entity_id=body.assignment_id,
        before={"staff_profile_id": str(body.absent_staff_profile_id)},
        after={"status": "suggested"},
        at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)
    await db.commit()

    return SubstitutionSuggestResponse(
        substitution_id=sub_log.id,
        candidates=candidates,
    )


@router.post("/{substitutionId}/confirm", response_model=SubstitutionConfirmResponse)
async def confirm_substitution(
    tenantId: UUID,
    substitutionId: UUID,
    body: SubstitutionConfirmRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
):
    """FR-10.3: Confirm substitution, apply as live edit, notify both parties.

    Optimistic concurrency means:
      1. Re-run H4/H5/H8 availability checks at confirm time (not trusted from
         the suggest snapshot — state may have changed between suggest and confirm).
      2. version_no check in apply_assignment_edit catches concurrent timetable edits.
      3. SubstitutionLog.status='confirmed' check catches concurrent confirm attempts
         (double-confirm returns 409 CONFLICT).
    """
    from app.services.edit_service import apply_assignment_edit
    from app.services.notifications import send_notification

    # Load the suggested substitution
    sub_log = (await db.execute(
        select(SubstitutionLog).where(SubstitutionLog.id == substitutionId)
    )).scalar_one_or_none()
    if not sub_log:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Substitution suggestion not found"}},
        )
    # Guard against double-confirm (concurrent confirm race)
    if sub_log.status == "confirmed":
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "This substitution has already been confirmed",
                }
            },
        )
    if sub_log.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "This substitution has been cancelled",
                }
            },
        )

    # Load the assignment to get course/cohort/slot info
    assignment = (await db.execute(
        select(Assignment).where(Assignment.id == sub_log.assignment_id)
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Assignment no longer exists"}},
        )

    substitute_id = body.substitute_staff_profile_id

    # Re-validate H5: eligibility at confirm time
    elig = (await db.execute(
        select(Eligibility).where(
            Eligibility.staff_profile_id == substitute_id,
            Eligibility.course_id == assignment.course_id,
            Eligibility.cohort_id == assignment.cohort_id,
        )
    )).scalar_one_or_none()
    if not elig:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "Substitute is no longer eligible for this course/cohort",
                }
            },
        )

    # Re-validate H4: not blocked at confirm time
    period_row = (await db.execute(
        select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index)
    )).scalars().all()
    slot_weekday = period_row[assignment.slot_start].weekday if assignment.slot_start < len(period_row) else 0

    blocked = (await db.execute(
        select(StaffAvailabilityBlock).where(
            StaffAvailabilityBlock.staff_profile_id == substitute_id,
            StaffAvailabilityBlock.weekday == slot_weekday,
        )
    )).scalar_one_or_none()
    if blocked:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "Substitute is blocked at this slot at confirm time",
                }
            },
        )

    # Re-validate H1: not already assigned in this slot at confirm time
    occupied = (await db.execute(
        select(Assignment).where(
            Assignment.timetable_version_id == assignment.timetable_version_id,
            Assignment.staff_profile_id == substitute_id,
            Assignment.slot_start == assignment.slot_start,
            Assignment.id != assignment.id,
        )
    )).scalar_one_or_none()
    if occupied:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INFEASIBLE_CONFIGURATION",
                    "message": "Substitute is already assigned to another course in this slot",
                }
            },
        )

    # Apply the edit via shared service (version_no check + H1-H11 + audit_log + commit)
    new_version_no = await apply_assignment_edit(
        db,
        version_id=assignment.timetable_version_id,
        tenant_id=tenantId,
        assignment_id=assignment.id,
        version_no=body.version_no,
        new_staff_profile_id=substitute_id,
        actor_identity_id=identity_id,
        audit_action="confirm_substitution",
        lock_cell=False,  # substitution is a live patch; locking is not appropriate here
    )

    # Update SubstitutionLog: mark confirmed
    sub_log.status = "confirmed"
    sub_log.substitute_staff_profile_id = substitute_id
    db.add(sub_log)

    # Write substitution-specific audit entry
    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="confirm_substitution",
        entity_type="substitution_log",
        entity_id=substitutionId,
        before={"status": "suggested"},
        after={"status": "confirmed", "substitute_staff_profile_id": str(substitute_id)},
        at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)

    # Notify original and substitute staff (FR-11.1)
    orig_sp = (await db.execute(
        select(StaffProfile).where(StaffProfile.id == sub_log.original_staff_profile_id)
    )).scalar_one_or_none()
    sub_sp = (await db.execute(
        select(StaffProfile).where(StaffProfile.id == substitute_id)
    )).scalar_one_or_none()

    if orig_sp and orig_sp.identity_id:
        await send_notification(
            db,
            tenant_id=tenantId,
            identity_id=orig_sp.identity_id,
            subject="Substitution Arranged",
            body=f"Your absence on {sub_log.date} has been covered by a substitute.",
        )
    if sub_sp and sub_sp.identity_id:
        await send_notification(
            db,
            tenant_id=tenantId,
            identity_id=sub_sp.identity_id,
            subject="You Have Been Assigned as Substitute",
            body=f"You have been assigned as a substitute on {sub_log.date}.",
        )

    await db.commit()
    return SubstitutionConfirmResponse(
        substitution_id=substitutionId,
        new_version_no=new_version_no,
    )

@router.get("")
async def list_substitutions(
    tenantId: UUID,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _role: None = Depends(require_role(["institution_admin", "department_head"])),
):
    """List all substitutions."""
    res = await db.execute(select(SubstitutionLog).order_by(SubstitutionLog.date.desc()))
    items = list(res.scalars().all())
    return {"items": items}

"""StaffProfiles router — CRUD under /api/v1/tenants/{tenantId}/staff-profiles."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.staff_profile import StaffProfile
from app.schemas.common import PaginatedResponse
from app.schemas.staff_profile import StaffProfileCreate, StaffProfileRead, StaffProfileUpdate
from app.schemas.timetable import PublishedScheduleResponse
from app.core.auth import verify_jwt

from app.rbac.dependencies import require_role
router = APIRouter(
    prefix="/api/v1/tenants/{tenantId}/staff-profiles", tags=["staff-profiles"])


@router.get("/{spId}/timetable", response_model=list[PublishedScheduleResponse])
async def get_staff_timetable(
    tenantId: UUID,
    spId: UUID,
    version_id: UUID | None = Query(None, description="The timetable version ID to fetch assignments for. Defaults to the active published version."),
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _role: None = Depends(require_role(["institution_admin", "department_head", "reviewer", "faculty"]))
):
    # Verify staff exists
    staff_res = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    staff = staff_res.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})

    # Ownership check: if caller is faculty, check if accessing own profile
    if staff.identity_id != identity_id:
        caller_res = await db.execute(
            select(StaffProfile.roles).where(
                StaffProfile.identity_id == identity_id,
                StaffProfile.tenant_id == tenantId
            )
        )
        roles = caller_res.scalar_one_or_none() or []
        allowed_admin = {"institution_admin", "department_head", "reviewer"}
        if not allowed_admin.intersection(roles):
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Cannot access another faculty's timetable"}})

    # Fetch version state
    from app.models.timetable_version import TimetableVersion
    if version_id:
        tv_result = await db.execute(select(TimetableVersion).where(TimetableVersion.id == version_id))
    else:
        tv_result = await db.execute(
            select(TimetableVersion)
            .where(TimetableVersion.tenant_id == tenantId)
            .where(TimetableVersion.state == 'published')
            .order_by(TimetableVersion.version_no.desc())
            .limit(1)
        )
    tv = tv_result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Version not found or no published version exists"}})
    
    version_id = tv.id

    if tv.state not in ("published", "archived"):
        caller_res = await db.execute(
            select(StaffProfile.roles).where(
                StaffProfile.identity_id == identity_id,
                StaffProfile.tenant_id == tenantId
            )
        )
        roles = caller_res.scalar_one_or_none() or []
        allowed_admin = {"institution_admin", "department_head", "reviewer"}
        if not allowed_admin.intersection(roles):
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Can only view published timetables"}})

    # Fetch dual-routed schedules
    from app.services.schedule_mapper import get_dual_routed_schedules
    all_schedules = await get_dual_routed_schedules(db, version_id, tv.state, 'class')

    # Filter to schedules where the staff member is assigned
    staff_schedules = [s for s in all_schedules if s.staff_profile_id == spId]
    return staff_schedules


@router.post("", response_model=StaffProfileRead, status_code=201)
async def create_staff_profile(
    tenantId: UUID, 
    body: StaffProfileCreate, 
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    sp = StaffProfile(tenant_id=tenantId, **body.model_dump())
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


@router.get("", response_model=PaginatedResponse[StaffProfileRead])
async def list_staff_profiles(
    tenantId: UUID, 
    cursor: str | None = None, 
    limit: int = 50, 
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    from app.models.identity import Identity
    
    q = (
        select(StaffProfile, Identity.full_name, Identity.email)
        .join(Identity, StaffProfile.identity_id == Identity.id)
        .order_by(StaffProfile.id)
        .limit(limit + 1)
    )
    if cursor:
        from uuid import UUID as _UUID
        q = q.where(StaffProfile.id > _UUID(cursor))
        
    result = await db.execute(q)
    rows = result.all()
    
    items = []
    for sp, fname, email in rows:
        items.append(StaffProfileRead(
            id=sp.id,
            tenant_id=sp.tenant_id,
            identity_id=sp.identity_id,
            employment_type=sp.employment_type,
            workload_cap_week=sp.workload_cap_week,
            workload_cap_day=sp.workload_cap_day,
            roles=sp.roles,
            full_name=fname,
            email=email
        ))
        
    next_cursor = str(items[-1].id) if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{spId}", response_model=StaffProfileRead)
async def get_staff_profile(
    tenantId: UUID, 
    spId: UUID, 
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    result = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})
    return sp


@router.patch("/{spId}", response_model=StaffProfileRead)
async def update_staff_profile(
    tenantId: UUID, 
    spId: UUID, 
    body: StaffProfileUpdate, 
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    result = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sp, field, value)
    await db.commit()
    await db.refresh(sp)
    return sp


@router.delete("/{spId}", status_code=204)
async def delete_staff_profile(
    tenantId: UUID, 
    spId: UUID, 
    db: AsyncSession = Depends(set_tenant_context),
    _role: None = Depends(require_role(["institution_admin", "department_head"]))
):
    result = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})
    await db.delete(sp)
    await db.commit()

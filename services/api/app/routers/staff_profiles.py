"""StaffProfiles router — CRUD under /api/v1/tenants/{tenantId}/staff-profiles."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.staff_profile import StaffProfile
from app.schemas.common import PaginatedResponse
from app.schemas.staff_profile import StaffProfileCreate, StaffProfileRead, StaffProfileUpdate

from app.rbac.dependencies import require_role
router = APIRouter(
    dependencies=[Depends(require_role(["institution_admin", "department_head"]))],
    prefix="/api/v1/tenants/{tenantId}/staff-profiles", tags=["staff-profiles"])


@router.post("", response_model=StaffProfileRead, status_code=201)
async def create_staff_profile(tenantId: UUID, body: StaffProfileCreate, db: AsyncSession = Depends(set_tenant_context)):
    sp = StaffProfile(tenant_id=tenantId, **body.model_dump())
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


@router.get("", response_model=PaginatedResponse[StaffProfileRead])
async def list_staff_profiles(tenantId: UUID, cursor: str | None = None, limit: int = 50, db: AsyncSession = Depends(set_tenant_context)):
    q = select(StaffProfile).order_by(StaffProfile.id).limit(limit + 1)
    if cursor:
        from uuid import UUID as _UUID
        q = q.where(StaffProfile.id > _UUID(cursor))
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = str(items[-1].id) if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{spId}", response_model=StaffProfileRead)
async def get_staff_profile(tenantId: UUID, spId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})
    return sp


@router.patch("/{spId}", response_model=StaffProfileRead)
async def update_staff_profile(tenantId: UUID, spId: UUID, body: StaffProfileUpdate, db: AsyncSession = Depends(set_tenant_context)):
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
async def delete_staff_profile(tenantId: UUID, spId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(StaffProfile).where(StaffProfile.id == spId))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Staff profile not found"}})
    await db.delete(sp)
    await db.commit()

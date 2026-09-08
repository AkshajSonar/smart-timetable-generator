"""Eligibility router — Create/Delete/List under /api/v1/tenants/{tenantId}/eligibility."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.eligibility import Eligibility
from app.schemas.common import PaginatedResponse
from app.schemas.eligibility import EligibilityCreate, EligibilityRead

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/eligibility", tags=["eligibility"])


@router.post("", response_model=EligibilityRead, status_code=201)
async def create_eligibility(tenantId: UUID, body: EligibilityCreate, db: AsyncSession = Depends(set_tenant_context)):
    elig = Eligibility(tenant_id=tenantId, **body.model_dump())
    db.add(elig)
    await db.commit()
    await db.refresh(elig)
    return elig


@router.get("", response_model=PaginatedResponse[EligibilityRead])
async def list_eligibility(tenantId: UUID, cursor: str | None = None, limit: int = 50, db: AsyncSession = Depends(set_tenant_context)):
    q = select(Eligibility).order_by(Eligibility.id).limit(limit + 1)
    if cursor:
        q = q.where(Eligibility.id > UUID(cursor))
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = str(items[-1].id) if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.delete("/{eligId}", status_code=204)
async def delete_eligibility(tenantId: UUID, eligId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Eligibility).where(Eligibility.id == eligId))
    elig = result.scalar_one_or_none()
    if not elig:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Eligibility not found"}})
    await db.delete(elig)
    await db.commit()

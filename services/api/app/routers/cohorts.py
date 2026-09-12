"""Cohorts router — CRUD under /api/v1/tenants/{tenantId}/cohorts."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.cohort import Cohort
from app.schemas.common import PaginatedResponse
from app.schemas.cohort import CohortCreate, CohortRead, CohortUpdate

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/cohorts", tags=["cohorts"])


@router.post("", response_model=CohortRead, status_code=201)
async def create_cohort(tenantId: UUID, body: CohortCreate, db: AsyncSession = Depends(set_tenant_context)):
    cohort = Cohort(tenant_id=tenantId, **body.model_dump())
    db.add(cohort)
    await db.commit()
    await db.refresh(cohort)
    return cohort


@router.get("", response_model=PaginatedResponse[CohortRead])
async def list_cohorts(tenantId: UUID, cursor: str | None = None, limit: int = 50, db: AsyncSession = Depends(set_tenant_context)):
    q = select(Cohort).order_by(Cohort.name).limit(limit + 1)
    if cursor:
        q = q.where(Cohort.name > cursor)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = items[-1].name if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.get("/{cohortId}", response_model=CohortRead)
async def get_cohort(tenantId: UUID, cohortId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Cohort).where(Cohort.id == cohortId))
    cohort = result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Cohort not found"}})
    return cohort


@router.patch("/{cohortId}", response_model=CohortRead)
async def update_cohort(tenantId: UUID, cohortId: UUID, body: CohortUpdate, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Cohort).where(Cohort.id == cohortId))
    cohort = result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Cohort not found"}})
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cohort, field, value)
    await db.commit()
    await db.refresh(cohort)
    return cohort


@router.delete("/{cohortId}", status_code=204)
async def delete_cohort(tenantId: UUID, cohortId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(Cohort).where(Cohort.id == cohortId))
    cohort = result.scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Cohort not found"}})
    await db.delete(cohort)
    await db.commit()

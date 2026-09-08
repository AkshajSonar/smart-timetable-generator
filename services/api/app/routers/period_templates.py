"""PeriodTemplates router — CRUD under /api/v1/tenants/{tenantId}/period-templates."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.models.period_template import PeriodTemplate
from app.schemas.common import PaginatedResponse
from app.schemas.period_template import PeriodTemplateCreate, PeriodTemplateRead

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/period-templates", tags=["period-templates"])


@router.post("", response_model=PeriodTemplateRead, status_code=201)
async def create_period_template(tenantId: UUID, body: PeriodTemplateCreate, db: AsyncSession = Depends(set_tenant_context)):
    pt = PeriodTemplate(tenant_id=tenantId, **body.model_dump())
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    return pt


@router.get("", response_model=PaginatedResponse[PeriodTemplateRead])
async def list_period_templates(tenantId: UUID, cursor: str | None = None, limit: int = 50, db: AsyncSession = Depends(set_tenant_context)):
    q = select(PeriodTemplate).order_by(PeriodTemplate.weekday, PeriodTemplate.period_index).limit(limit + 1)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = str(items[-1].id) if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)


@router.delete("/{ptId}", status_code=204)
async def delete_period_template(tenantId: UUID, ptId: UUID, db: AsyncSession = Depends(set_tenant_context)):
    result = await db.execute(select(PeriodTemplate).where(PeriodTemplate.id == ptId))
    pt = result.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Period template not found"}})
    await db.delete(pt)
    await db.commit()

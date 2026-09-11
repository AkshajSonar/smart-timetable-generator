"""Terms router — read under /api/v1/tenants/{tenantId}/terms."""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.core.tenant_context import set_tenant_context
from app.models.academic_term import AcademicTerm
from app.schemas.common import PaginatedResponse
from app.rbac.dependencies import require_role

router = APIRouter(
    prefix="/api/v1/tenants/{tenantId}/terms",
    tags=["terms"],
)


class TermRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    start_date: date
    end_date: date

    model_config = {"from_attributes": True}


@router.get(
    "",
    response_model=PaginatedResponse[TermRead],
    dependencies=[Depends(require_role(["institution_admin", "department_head", "reviewer", "faculty", "student"]))],
)
async def list_terms(
    tenantId: UUID,
    cursor: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(set_tenant_context),
):
    q = select(AcademicTerm).order_by(AcademicTerm.name).limit(limit + 1)
    if cursor:
        q = q.where(AcademicTerm.name > cursor)
    result = await db.execute(q)
    items = list(result.scalars().all())
    next_cursor = items[-1].name if len(items) > limit else None
    return PaginatedResponse(items=items[:limit], next_cursor=next_cursor)

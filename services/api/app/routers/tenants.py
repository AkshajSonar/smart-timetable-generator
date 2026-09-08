"""Tenants router — POST /api/v1/tenants for seeding in Phase 1."""

from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.identity import Identity

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


class TenantCreate(BaseModel):
    name: str
    institution_type: str = "college"
    timezone: str = "UTC"


class TenantRead(BaseModel):
    id: UUID
    name: str
    institution_type: str
    timezone: str
    model_config = {"from_attributes": True}


@router.post("", response_model=TenantRead, status_code=201)
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)):
    """Create a tenant. Phase 1: no auth check (platform_super_admin only in prod)."""
    tenant = Tenant(
        name=body.name,
        institution_type=body.institution_type,
        timezone=body.timezone,
    )
    # tenant.tenant_id = tenant.id for RLS self-referencing
    import uuid
    tid = uuid.uuid4()
    tenant.id = tid
    tenant.tenant_id = tid
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth import verify_jwt
from app.models.staff_profile import StaffProfile
from app.models.tenant import Tenant
from pydantic import BaseModel

router = APIRouter()

class TenantRead(BaseModel):
    id: UUID
    name: str

class MeTenantsResponse(BaseModel):
    tenants: list[TenantRead]

@router.get("/me/tenants", response_model=MeTenantsResponse)
async def get_me_tenants(
    identity_id: UUID = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists every tenant the current Identity holds a staff_profile at.
    Without this, there's no way for a logged-in identity to discover
    which tenant(s) it can operate in.
    """
    # Find all staff_profile rows for this identity
    result = await db.execute(select(StaffProfile.tenant_id).where(StaffProfile.identity_id == identity_id))
    tenant_ids = result.scalars().all()

    if not tenant_ids:
        return MeTenantsResponse(tenants=[])

    # Fetch tenant details
    tenant_result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
    tenants = tenant_result.scalars().all()

    return MeTenantsResponse(
        tenants=[TenantRead(id=t.id, name=t.name) for t in tenants]
    )

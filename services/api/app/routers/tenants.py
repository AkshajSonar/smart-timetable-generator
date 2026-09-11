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
    isolation_mode: str = "row"


class TenantRead(BaseModel):
    id: UUID
    name: str
    institution_type: str
    timezone: str
    isolation_mode: str
    model_config = {"from_attributes": True}


from app.rbac.dependencies import require_platform_super_admin

@router.post("", response_model=TenantRead, status_code=201)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _super_admin: None = Depends(require_platform_super_admin)
):
    """Create a tenant. Phase 1: no auth check (platform_super_admin only in prod)."""
    tenant = Tenant(
        name=body.name,
        institution_type=body.institution_type,
        timezone=body.timezone,
        isolation_mode=body.isolation_mode,
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


from app.schemas.staff_profile import StaffInviteRequest, StaffInviteResponse
from app.models.staff_profile import StaffProfile
from app.rbac.dependencies import require_role
from app.core.tenant_context import set_tenant_context
from fastapi import HTTPException

@router.post("/{tenantId}/staff/invite", response_model=StaffInviteResponse, status_code=201)
async def invite_staff(
    tenantId: UUID,
    body: StaffInviteRequest,
    db: AsyncSession = Depends(set_tenant_context),
    _roles: None = Depends(require_role(["institution_admin", "department_head"]))
):
    """Invite a new staff member to the tenant."""
    from sqlalchemy.future import select
    result = await db.execute(select(Identity).where(Identity.email == body.email))
    identity = result.scalars().first()
    
    status = "linked_existing_identity"
    if not identity:
        # Create stub
        import uuid
        identity = Identity(
            id=uuid.uuid4(),
            email=body.email,
            auth_provider_ref=None,
            platform_role=None
        )
        db.add(identity)
        status = "stub_identity_created_pending_first_login"
        
    # Check if staff profile already exists
    sp_res = await db.execute(select(StaffProfile).where(
        StaffProfile.identity_id == identity.id, 
        StaffProfile.tenant_id == tenantId
    ))
    if sp_res.scalars().first():
        raise HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": "Staff profile already exists for this email"}})
        
    sp = StaffProfile(
        tenant_id=tenantId,
        identity_id=identity.id,
        employment_type=body.employment_type,
        workload_cap_week=body.workload_cap_week,
        workload_cap_day=body.workload_cap_day,
        roles=body.roles
    )
    db.add(sp)
    await db.commit()
    
    return StaffInviteResponse(staff_profile=sp, status=status)

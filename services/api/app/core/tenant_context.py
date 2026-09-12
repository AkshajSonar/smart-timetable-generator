"""Tenant-context middleware: SET LOCAL app.tenant_id per §29.2.

Implemented as a FastAPI dependency, not a global middleware, so it
wraps only tenant-scoped routes (those with {tenantId} in the path).
"""

from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth import verify_jwt
from app.models.staff_profile import StaffProfile
from app.models.student_profile import StudentProfile
from app.models.identity import Identity


async def _check_tenant_membership(
    tenantId: UUID,
    identity_id: UUID,
    db: AsyncSession
) -> None:
    """Validates the JWT's identity_id against staff_profile/student_profile at this tenant."""
    staff_result = await db.execute(select(StaffProfile.id).where(StaffProfile.identity_id == identity_id, StaffProfile.tenant_id == tenantId))
    has_staff = staff_result.scalars().first() is not None

    is_authorized = has_staff
    if not is_authorized:
        student_result = await db.execute(select(StudentProfile.id).where(StudentProfile.identity_id == identity_id, StudentProfile.tenant_id == tenantId))
        has_student = student_result.scalar_one_or_none() is not None
        if has_student:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Identity has no access to this tenant"}}
        )

async def set_tenant_context(
    tenantId: UUID,
    identity_id: UUID = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """Execute SET LOCAL for RLS within the current transaction.

    Validates the JWT's identity_id against staff_profile/student_profile at this tenant.
    """
    await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenantId)})
    await db.execute(text("SELECT set_config('app.identity_id', :iid, true)"), {"iid": str(identity_id)})
    
    await _check_tenant_membership(tenantId, identity_id, db)

    return db

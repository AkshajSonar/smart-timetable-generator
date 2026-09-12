"""Tenant-context middleware: SET LOCAL app.tenant_id per §29.2.

Implemented as a FastAPI dependency, not a global middleware, so it
wraps only tenant-scoped routes (those with {tenantId} in the path).
"""

from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


async def set_tenant_context(
    tenantId: UUID,
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """Execute SET LOCAL for RLS within the current transaction.

    Phase 1: no JWT — tenant context comes from the path param only.
    When auth is wired (Phase 5+), this will also validate the JWT's
    identity_id against staff_profile/student_profile at this tenant.
    """
    await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenantId)})
    return db

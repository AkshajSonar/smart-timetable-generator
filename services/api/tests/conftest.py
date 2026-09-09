import pytest
import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.main import app
from app.core.auth import verify_jwt
from app.core.tenant_context import set_tenant_context
from app.core.database import get_db

TEST_IDENTITY_ID = uuid.uuid4()

async def mock_verify_jwt():
    return TEST_IDENTITY_ID

async def mock_set_tenant_context(
    tenantId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # Just set the context without doing the RBAC DB lookups which would fail in tests
    # without a seeded database.
    await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenantId)})
    await db.execute(text("SELECT set_config('app.identity_id', :iid, true)"), {"iid": str(TEST_IDENTITY_ID)})
    return db

app.dependency_overrides[verify_jwt] = mock_verify_jwt
app.dependency_overrides[set_tenant_context] = mock_set_tenant_context

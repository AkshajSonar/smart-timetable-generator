import pytest
import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.main import app
from app.core.auth import verify_jwt
from app.core.tenant_context import _check_tenant_membership
from app.rbac.dependencies import _get_user_roles

TEST_IDENTITY_ID = uuid.uuid4()

async def mock_verify_jwt():
    return TEST_IDENTITY_ID

async def mock_check_tenant_membership(
    tenantId: uuid.UUID,
    identity_id: uuid.UUID,
    db: AsyncSession
):
    pass

# By default, mock tests as institution_admin
# By default, mock tests as institution_admin
MOCK_ROLES = {"institution_admin"}

import pytest
import pytest_asyncio
from app.core.database import get_db, settings, engine, engine_superuser
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

@pytest_asyncio.fixture(autouse=True)
async def dispose_engines():
    yield
    await engine.dispose()
    await engine_superuser.dispose()

@pytest_asyncio.fixture
async def superuser_session() -> AsyncSession:
    local_engine = create_async_engine(settings.database_url_superuser, echo=False, pool_pre_ping=True)
    SessionMaker = async_sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session
    await local_engine.dispose()

async def mock_get_user_roles(
    tenantId: uuid.UUID,
    identity_id: uuid.UUID = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db)
) -> set[str]:
    return MOCK_ROLES

from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def patch_check_tenant_membership():
    with patch("app.core.tenant_context._check_tenant_membership", new_callable=AsyncMock) as mock:
        yield mock

app.dependency_overrides[verify_jwt] = mock_verify_jwt
app.dependency_overrides[_get_user_roles] = mock_get_user_roles

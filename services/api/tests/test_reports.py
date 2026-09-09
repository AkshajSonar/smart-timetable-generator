import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from app.main import app
from app.schemas.report import LoadVerificationReport

@pytest.mark.asyncio
async def test_load_verification_report_not_found():
    """Test that requesting a report for a non-existent version returns 404."""
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    
    from tests.conftest import MOCK_ROLES
    MOCK_ROLES.clear()
    MOCK_ROLES.update({"institution_admin"})
    
    from app.core.database import get_db
    from unittest.mock import AsyncMock, MagicMock
    db = AsyncMock()
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_scalar
    
    async def _get_mock_db():
        yield db
    app.dependency_overrides[get_db] = _get_mock_db
    
    # We use httpx AsyncClient for FastAPI testing
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={version_id}")
    
    del app.dependency_overrides[get_db]
    
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"

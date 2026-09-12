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
    
    # We use httpx AsyncClient for FastAPI testing
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={version_id}")
        
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"

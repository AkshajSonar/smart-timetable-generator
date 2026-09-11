import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from sqlalchemy import text
from app.main import app

@pytest.mark.asyncio
async def test_load_verification_report_not_found():
    """Test that requesting a report for a non-existent version returns 404."""
    from app.core.database import SuperuserAsyncSessionLocal
    from app.models.tenant import Tenant
    from app.models.identity import Identity
    from app.models.staff_profile import StaffProfile
    
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    
    async with SuperuserAsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
        await session.execute(text("TRUNCATE TABLE identity CASCADE;"))
        session.add(Tenant(id=tenant_id, name="Report Test", institution_type="college", timezone="UTC"))
        session.add(Identity(id=identity_id, email="report@test.com", auth_provider_ref="kc|report", platform_role=None))
        session.add(StaffProfile(
            id=staff_id, identity_id=identity_id, tenant_id=tenant_id,
            employment_type="full_time", workload_cap_week=40, workload_cap_day=8,
            roles=["institution_admin"]
        ))
        await session.commit()
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return identity_id
        app.dependency_overrides[verify_jwt] = mock_verify
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={version_id}")
        assert response.status_code == 404
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt
    
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "NOT_FOUND"

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.future import select

from app.models.tenant import Tenant
from app.models.identity import Identity
from app.models.staff_profile import StaffProfile

from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_staff_invite_creates_stub(superuser_session):
    # 1. Setup tenant
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Invite Test", institution_type="college", isolation_mode="row", timezone="UTC")
    tenant.tenant_id = tenant_id
    superuser_session.add(tenant)
    await superuser_session.commit()

    invite_email = f"new.staff.{uuid.uuid4()}@example.com"
    payload = {
        "email": invite_email,
        "employment_type": "full_time",
        "workload_cap_week": 40,
        "workload_cap_day": 8,
        "roles": ["faculty"]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/tenants/{tenant_id}/staff/invite", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "stub_identity_created_pending_first_login"
    assert data["staff_profile"]["employment_type"] == "full_time"
    
    # 2. Verify identity was created
    res = await superuser_session.execute(select(Identity).where(Identity.email == invite_email))
    identity = res.scalars().first()
    assert identity is not None
    assert identity.auth_provider_ref is None  # It's a stub

    # 3. Verify staff profile was created
    from sqlalchemy import text
    await superuser_session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
    res_sp = await superuser_session.execute(
        select(StaffProfile).where(StaffProfile.identity_id == identity.id, StaffProfile.tenant_id == tenant_id)
    )
    sp = res_sp.scalars().first()
    assert sp is not None
    assert sp.roles == ["faculty"]

@pytest.mark.asyncio
async def test_staff_invite_links_existing_identity(superuser_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Invite Test 2", institution_type="college", isolation_mode="row", timezone="UTC")
    tenant.tenant_id = tenant_id
    superuser_session.add(tenant)
    
    # Create an existing identity (not a stub)
    invite_email = f"existing.staff.{uuid.uuid4()}@example.com"
    identity_id = uuid.uuid4()
    identity = Identity(
        id=identity_id, 
        email=invite_email, 
        auth_provider_ref=str(uuid.uuid4()), 
        platform_role=None
    )
    superuser_session.add(identity)
    await superuser_session.commit()

    payload = {
        "email": invite_email,
        "employment_type": "part_time",
        "workload_cap_week": 20,
        "workload_cap_day": 4,
        "roles": ["faculty"]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/tenants/{tenant_id}/staff/invite", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "linked_existing_identity"
    assert data["staff_profile"]["identity_id"] == str(identity_id)

@pytest.mark.asyncio
async def test_cross_tenant_get_me(superuser_session):
    from unittest.mock import patch
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Invite Test 3", institution_type="college", isolation_mode="row", timezone="UTC")
    tenant.tenant_id = tenant_id
    superuser_session.add(tenant)
    
    invite_email = f"multi.staff.{uuid.uuid4()}@example.com"
    identity_id = uuid.uuid4()
    identity = Identity(
        id=identity_id, 
        email=invite_email, 
        auth_provider_ref=str(uuid.uuid4()), 
        platform_role=None
    )
    superuser_session.add(identity)
    await superuser_session.commit()

    payload = {
        "email": invite_email,
        "employment_type": "full_time",
        "workload_cap_week": 40,
        "workload_cap_day": 8,
        "roles": ["faculty"]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/tenants/{tenant_id}/staff/invite", json=payload)
        assert response.status_code == 201

        # Now GET /me/tenants acting as the user
        async def mock_verify_jwt_local():
            return identity_id
        
        from app.core.auth import verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt_local
        try:
            resp = await client.get("/api/v1/me/tenants", headers={"Authorization": "Bearer token"})
            assert resp.status_code == 200
            data = resp.json()
            print("DATA:", data)
            assert any(t["id"] == str(tenant_id) for t in data["tenants"])
        finally:
            from tests.conftest import mock_verify_jwt
            app.dependency_overrides[verify_jwt] = mock_verify_jwt

import pytest

@pytest.mark.asyncio
async def test_invited_stub_identity_activates_on_first_login(superuser_session):
    """
    Invite by email (creating a stub), then simulate that person's first real login,
    assert exactly one identity row exists afterward and staff_profile.identity_id still correctly points to it.
    """
    from app.models.identity import Identity
    from app.models.staff_profile import StaffProfile
    from app.models.tenant import Tenant
    from app.core.auth import verify_jwt
    import uuid
    from unittest.mock import patch, AsyncMock
    
    # 1. Create tenant and stub identity
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Test Tenant", institution_type="college", isolation_mode="row")
    superuser_session.add(tenant)
    
    stub_email = f"stub.invite.{uuid.uuid4()}@example.com"
    stub_id = uuid.uuid4()
    stub = Identity(id=stub_id, email=stub_email, auth_provider_ref=None)
    superuser_session.add(stub)
    
    staff = StaffProfile(
        identity_id=stub_id, 
        tenant_id=tenant_id, 
        employment_type="full_time",
        workload_cap_week=20,
        workload_cap_day=4,
        roles=["faculty"]
    )
    superuser_session.add(staff)
    await superuser_session.commit()
    
    # 2. Simulate first login (JWT sub is Keycloak's UUID)
    keycloak_sub = uuid.uuid4()
    
    with patch('app.core.auth.jwks_client') as mock_jwks_client:
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "fake_key"
        with patch('app.core.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "sub": str(keycloak_sub),
                "email": stub_email
            }
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake_token")
            # Run the verify_jwt function
            result_id = await verify_jwt(credentials, db=superuser_session)
            
            # Should return the stub_id, NOT keycloak_sub
            assert result_id == stub_id
                
    # 3. Assert exactly one identity row exists for this email
    from sqlalchemy.future import select
    res = await superuser_session.execute(select(Identity).where(Identity.email == stub_email))
    identities = res.scalars().all()
    assert len(identities) == 1
    
    # Assert auth_provider_ref is now the keycloak sub
    assert identities[0].auth_provider_ref == str(keycloak_sub)
    
    # Assert staff profile still points to it
    res_staff = await superuser_session.execute(select(StaffProfile).where(StaffProfile.identity_id == stub_id))
    assert res_staff.scalars().first() is not None


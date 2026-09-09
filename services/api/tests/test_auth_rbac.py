import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.main import app
import tests.conftest as conftest

@pytest.fixture
def override_role():
    original = conftest.MOCK_ROLES.copy()
    def _set(roles: set[str]):
        conftest.MOCK_ROLES.clear()
        conftest.MOCK_ROLES.update(roles)
    try:
        yield _set
    finally:
        conftest.MOCK_ROLES.clear()
        conftest.MOCK_ROLES.update(original)

@pytest.fixture
def mock_db():
    from app.core.database import get_db
    db = AsyncMock()
    
    async def _get_mock_db():
        yield db
        
    app.dependency_overrides[get_db] = _get_mock_db
    yield db
    del app.dependency_overrides[get_db]

def _setup_mock_db(mock_db):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_scalar.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_scalar

@pytest.mark.asyncio
async def test_departments_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/departments")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_departments_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/departments")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_departments_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/departments")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_courses_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/courses")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_courses_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/courses")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_rooms_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/rooms")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_rooms_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/rooms")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_staff_profiles_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/staff-profiles")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_staff_profiles_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/staff-profiles")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_eligibility_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/eligibility")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_eligibility_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/eligibility")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_cohorts_rbac_403_reviewer(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"reviewer"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/cohorts")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_cohorts_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/cohorts")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_period_templates_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/period-templates")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_period_templates_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/period-templates")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_timetables_generate_rbac_403_reviewer(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"reviewer"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_timetables_generate_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate", json={})
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_timetables_view_rbac_403(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role(set())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_timetables_view_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_exams_generate_rbac_403_reviewer(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"reviewer"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/generate")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_generate_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/generate")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_generate_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/generate", json={})
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_exams_sessions_rbac_403_faculty(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/exams/sessions")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_sessions_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/exams/sessions")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_sessions_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/exams/sessions")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_import_data_rbac_403_department_head(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"department_head"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/import/enrollment")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_import_data_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/import/enrollment", json={})
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_reports_verification_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={version_id}")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_reports_verification_rbac_200_institution_admin(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    _setup_mock_db(mock_db)
    override_role({"institution_admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={version_id}")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_users_me_tenants_unguarded(override_role, mock_db):
    override_role(set())
    _setup_mock_db(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/me/tenants")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_student_timetable_ownership(override_role, mock_db):
    tenant_id = uuid.uuid4()
    student_id = uuid.uuid4()
    version_id = uuid.uuid4()
    other_identity_id = uuid.uuid4()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        override_role({"student"})
        mock_student = MagicMock()
        mock_student.identity_id = conftest.TEST_IDENTITY_ID
        mock_student.cohort_id = uuid.uuid4()
        
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_student
        mock_db.execute.return_value = mock_res
        
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/students/{student_id}/timetable?versionId={version_id}")
        assert res.status_code != 403
        
        mock_student.identity_id = other_identity_id
        def db_side_effect(query, *args, **kwargs):
            m = MagicMock()
            if "StaffProfile.roles" in str(query):
                m.scalar_one_or_none.return_value = None
            else:
                m.scalar_one_or_none.return_value = mock_student
            return m
        mock_db.execute.side_effect = db_side_effect
        
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/students/{student_id}/timetable?versionId={version_id}")
        assert res.status_code == 403
        
        override_role({"institution_admin"})
        def db_side_effect_admin(query, *args, **kwargs):
            m = MagicMock()
            if "roles" in str(query).lower():
                m.scalar_one_or_none.return_value = ["institution_admin"]
            else:
                m.scalar_one_or_none.return_value = mock_student
            return m
        mock_db.execute.side_effect = db_side_effect_admin
        
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/students/{student_id}/timetable?versionId={version_id}")
        assert res.status_code != 403

@pytest.mark.asyncio
async def test_platform_super_admin():
    from app.rbac.dependencies import require_platform_super_admin
    async def mock_super_admin_pass(): pass
    async def mock_super_admin_fail():
        from fastapi import HTTPException
        raise HTTPException(status_code=403)
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        app.dependency_overrides[require_platform_super_admin] = mock_super_admin_fail
        res = await ac.post("/api/v1/tenants", json={"name": "Test"})
        assert res.status_code == 403
        
        app.dependency_overrides[require_platform_super_admin] = mock_super_admin_pass
        from app.core.database import get_db
        db = AsyncMock()
        async def _get_mock_db(): yield db
        app.dependency_overrides[get_db] = _get_mock_db
        
        res = await ac.post("/api/v1/tenants", json={"name": "Test"})
        assert res.status_code != 403
        
        del app.dependency_overrides[require_platform_super_admin]
        del app.dependency_overrides[get_db]

@pytest.mark.asyncio
async def test_roles_db_lookup_end_to_end():
    from app.rbac.dependencies import _get_user_roles
    from app.core.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from app.models.staff_profile import StaffProfile
    from app.models.identity import Identity
    from sqlalchemy import text
    
    tenant_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    
    if _get_user_roles in app.dependency_overrides:
        del app.dependency_overrides[_get_user_roles]
        
    async with AsyncSessionLocal() as session:
        session.add(Identity(id=identity_id, email=f"test_{identity_id}@test.com", auth_provider_ref="auth0|123", platform_role=None))
        session.add(Tenant(id=tenant_id, name="Test End-to-End Tenant", institution_type="college", timezone="UTC"))
        session.add(StaffProfile(id=uuid.uuid4(), identity_id=identity_id, tenant_id=tenant_id, employment_type="full_time", workload_cap_week=40, workload_cap_day=8, roles=["reviewer"]))
        await session.commit()
    
    from app.core.auth import verify_jwt
    async def mock_verify(): return identity_id
    app.dependency_overrides[verify_jwt] = mock_verify
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/reports/verification?version_id={uuid.uuid4()}")
        assert res.status_code != 403
        
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate", json={"term_id": "Fall"})
        assert res.status_code == 403
        
    async with AsyncSessionLocal() as session:
        await session.execute(text(f"DELETE FROM staff_profile WHERE identity_id = '{identity_id}'"))
        await session.execute(text(f"DELETE FROM tenant WHERE id = '{tenant_id}'"))
        await session.execute(text(f"DELETE FROM identity WHERE id = '{identity_id}'"))
        await session.commit()
        
    from app.core.database import engine
    await engine.dispose()
    
    from tests.conftest import mock_get_user_roles
    app.dependency_overrides[_get_user_roles] = mock_get_user_roles

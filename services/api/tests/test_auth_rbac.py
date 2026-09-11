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
    """No roles → 403 on GET /timetables/{id}."""
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
    
    # Mock a draft version
    mock_version = MagicMock()
    mock_version.state = "draft"
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = mock_version
    mock_db.execute.return_value = mock_scalar
    
    override_role({"faculty"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/exams/sessions?versionId={version_id}")
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_sessions_rbac_403_student(override_role, mock_db):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    
    mock_version = MagicMock()
    mock_version.state = "draft"
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = mock_version
    mock_db.execute.return_value = mock_scalar
    
    override_role({"student"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/tenants/{tenant_id}/exams/sessions?versionId={version_id}")
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



"""Tests for Phase 5 Step 2: RBAC Enforcement"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app

def _set_roles(roles: set) -> None:
    from tests.conftest import MOCK_ROLES
    MOCK_ROLES.clear()
    MOCK_ROLES.update(roles)

@pytest.mark.asyncio
async def test_roles_db_lookup_end_to_end(superuser_session):
    """Verify the real DB join (staff_profile + identity + tenant) works, not just a mocked return."""
    
    tenant_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    
    from app.models.tenant import Tenant
    from app.models.identity import Identity
    from app.models.staff_profile import StaffProfile
    
    await superuser_session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    await superuser_session.execute(text("TRUNCATE TABLE identity CASCADE;"))
    
    superuser_session.add(Tenant(id=tenant_id, name="Test Tenant", institution_type="college", timezone="UTC"))
    superuser_session.add(Identity(id=identity_id, email="real_lookup@test.com", auth_provider_ref="kc|real", platform_role=None))
    superuser_session.add(StaffProfile(
        id=staff_id,
        identity_id=identity_id,
        tenant_id=tenant_id,
        employment_type="full_time",
        workload_cap_week=40,
        workload_cap_day=8,
        roles=["reviewer"]
    ))
    await superuser_session.commit()
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return identity_id
        app.dependency_overrides[verify_jwt] = mock_verify
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/tenants/{tenant_id}/students/{uuid.uuid4()}/timetable?versionId={uuid.uuid4()}")
        assert res.status_code != 403
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt

@pytest.mark.asyncio
async def test_platform_super_admin(superuser_session):
    tenant_id = uuid.uuid4()
    from app.models.tenant import Tenant
    superuser_session.add(Tenant(id=tenant_id, name="Temp", institution_type="college", timezone="UTC"))
    await superuser_session.commit()
    
    from app.core.database import get_db
    from unittest.mock import AsyncMock, MagicMock
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "some_other_role"
    db.execute.return_value = mock_result
    async def _mock_db(): yield db
    app.dependency_overrides[get_db] = _mock_db
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return uuid.uuid4()
        app.dependency_overrides[verify_jwt] = mock_verify
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/tenants", json={"name": "New", "institution_type": "college", "timezone": "UTC"})
        assert res.status_code == 403
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt
        if get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]

@pytest.mark.asyncio
async def test_student_timetable_ownership(superuser_session):
    tenant_id = uuid.uuid4()
    student_id = uuid.uuid4()
    other_student_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    
    from app.models.tenant import Tenant
    from app.models.identity import Identity
    from app.models.student_profile import StudentProfile
    from app.models.cohort import Cohort
    
    await superuser_session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    await superuser_session.execute(text("TRUNCATE TABLE identity CASCADE;"))
    
    cohort_id = uuid.uuid4()
    other_identity_id = uuid.uuid4()
    superuser_session.add(Tenant(id=tenant_id, name="Test Tenant", institution_type="college", timezone="UTC"))
    superuser_session.add(Identity(id=identity_id, email="student@test.com", auth_provider_ref="kc|student", platform_role=None))
    superuser_session.add(Identity(id=other_identity_id, email="other@test.com", auth_provider_ref="kc|other", platform_role=None))
    await superuser_session.flush()
    superuser_session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="C1", type="fixed"))
    superuser_session.add(StudentProfile(id=student_id, identity_id=identity_id, tenant_id=tenant_id, external_student_code="S1", cohort_id=cohort_id))
    superuser_session.add(StudentProfile(id=other_student_id, identity_id=other_identity_id, tenant_id=tenant_id, external_student_code="S2", cohort_id=cohort_id))
    await superuser_session.commit()
    
    _set_roles({"student"})
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return identity_id
        app.dependency_overrides[verify_jwt] = mock_verify
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/tenants/{tenant_id}/students/{other_student_id}/timetable?versionId={uuid.uuid4()}")
        assert res.status_code == 403
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt

@pytest.mark.asyncio
async def test_get_timetable_rbac_403_faculty(superuser_session):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    
    from app.models.tenant import Tenant
    from app.models.identity import Identity
    from app.models.staff_profile import StaffProfile
    from app.models.timetable_version import TimetableVersion
    from app.models.academic_term import AcademicTerm
    
    await superuser_session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    await superuser_session.execute(text("TRUNCATE TABLE identity CASCADE;"))
    
    import datetime
    term_id = uuid.uuid4()
    superuser_session.add(Tenant(id=tenant_id, name="Test Tenant", institution_type="college", timezone="UTC"))
    superuser_session.add(Identity(id=identity_id, email="faculty@test.com", auth_provider_ref="kc|faculty", platform_role=None))
    await superuser_session.flush()
    superuser_session.add(AcademicTerm(id=term_id, tenant_id=tenant_id, name="Fall", start_date=datetime.date(2023, 9, 1), end_date=datetime.date(2023, 12, 15)))
    superuser_session.add(StaffProfile(id=staff_id, identity_id=identity_id, tenant_id=tenant_id, employment_type="full_time", workload_cap_week=40, workload_cap_day=8, roles=["faculty"]))
    superuser_session.add(TimetableVersion(id=version_id, tenant_id=tenant_id, term_id=term_id, state="draft"))
    await superuser_session.commit()
    
    _set_roles({"faculty"})
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return identity_id
        app.dependency_overrides[verify_jwt] = mock_verify
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res.status_code == 403
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt

@pytest.mark.asyncio
async def test_platform_super_admin_no_blanket_access(superuser_session):
    tenant_id = uuid.uuid4()
    version_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    
    from app.models.tenant import Tenant
    from app.models.identity import Identity
    from app.models.timetable_version import TimetableVersion
    from app.models.academic_term import AcademicTerm
    
    await superuser_session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    await superuser_session.execute(text("TRUNCATE TABLE identity CASCADE;"))
    
    import datetime
    term_id = uuid.uuid4()
    superuser_session.add(Tenant(id=tenant_id, name="Test Tenant", institution_type="college", timezone="UTC"))
    superuser_session.add(Identity(id=identity_id, email="super@test.com", auth_provider_ref="kc|super", platform_role="platform_super_admin"))
    await superuser_session.flush()
    superuser_session.add(AcademicTerm(id=term_id, tenant_id=tenant_id, name="Fall", start_date=datetime.date(2023, 9, 1), end_date=datetime.date(2023, 12, 15)))
    superuser_session.add(TimetableVersion(id=version_id, tenant_id=tenant_id, term_id=term_id, state="draft"))
    await superuser_session.commit()
    
    _set_roles(set())  # No tenant-level roles
    
    try:
        from app.core.auth import verify_jwt
        async def mock_verify(): return identity_id
        app.dependency_overrides[verify_jwt] = mock_verify
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res.status_code == 403
    finally:
        from tests.conftest import mock_verify_jwt
        app.dependency_overrides[verify_jwt] = mock_verify_jwt

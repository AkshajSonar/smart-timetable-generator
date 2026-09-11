"""Tests for POST /timetables/{versionId}/edit — FR-9.1 manual edit."""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select as _select

from app.main import app
import tests.conftest as conftest

def _set_roles(roles: set) -> None:
    conftest.MOCK_ROLES.clear()
    conftest.MOCK_ROLES.update(roles)

async def _seed_base(session, tenant_id, identity_id, version_id, assignment_id):
    from app.models.identity import Identity
    from app.models.tenant import Tenant
    from app.models.department import Department
    from app.models.timetable_version import TimetableVersion
    from app.models.assignment import Assignment as AssignmentModel
    from app.models.staff_profile import StaffProfile
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.room import Room
    from app.models.eligibility import Eligibility
    from app.models.period_template import PeriodTemplate

    staff_id = uuid.uuid4()
    dept_id = uuid.uuid4()
    course_id = uuid.uuid4()
    cohort_id = uuid.uuid4()
    room_id = uuid.uuid4()
    room2_id = uuid.uuid4()

    await session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    await session.execute(text("TRUNCATE TABLE identity CASCADE;"))
    
    session.add(Identity(id=identity_id, email=f"edit_{identity_id}@t.com", auth_provider_ref="kc|e", platform_role=None))
    session.add(Tenant(id=tenant_id, name=f"Edit-{tenant_id}", institution_type="college", timezone="UTC"))
    await session.flush()
    session.add(Department(id=dept_id, tenant_id=tenant_id, name="CS"))
    await session.flush()
    session.add(StaffProfile(id=staff_id, identity_id=identity_id, tenant_id=tenant_id, employment_type="full_time", workload_cap_week=40, workload_cap_day=8, roles=["institution_admin"]))
    session.add(Course(id=course_id, tenant_id=tenant_id, department_id=dept_id, name="Math", type="core", credit_value=4, hours_per_week=1))
    session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="CS-A", type="fixed"))
    session.add(Room(id=room_id, tenant_id=tenant_id, name="Room-A", type="classroom", capacity=40, accessible=True))
    session.add(Room(id=room2_id, tenant_id=tenant_id, name="Room-B", type="classroom", capacity=40, accessible=True))
    await session.flush()
    session.add(Eligibility(tenant_id=tenant_id, staff_profile_id=staff_id, course_id=course_id, cohort_id=cohort_id))
    import datetime
    for i in range(10):
        session.add(PeriodTemplate(id=uuid.uuid4(), tenant_id=tenant_id, weekday=1, period_index=i, start_time=datetime.time(9, 0), end_time=datetime.time(10, 0), shift="Morning"))
    await session.flush()
    session.add(TimetableVersion(id=version_id, tenant_id=tenant_id, state="draft", version_no=1))
    await session.flush()
    session.add(AssignmentModel(
        id=assignment_id,
        timetable_version_id=version_id,
        tenant_id=tenant_id,
        staff_profile_id=staff_id,
        course_id=course_id,
        cohort_id=cohort_id,
        room_id=room_id,
        slot_start=0,
        slot_span=1,
    ))
    await session.commit()
    return {"staff_id": staff_id, "course_id": course_id, "cohort_id": cohort_id, "room_id": room_id, "room2_id": room2_id}


import pytest_asyncio

@pytest_asyncio.fixture
async def seeded_env(superuser_session):
    tenant_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    version_id = uuid.uuid4()
    assignment_id = uuid.uuid4()
    data = await _seed_base(superuser_session, tenant_id, identity_id, version_id, assignment_id)
    data.update({"tenant_id": tenant_id, "identity_id": identity_id, "version_id": version_id, "assignment_id": assignment_id})
    
    from app.core.auth import verify_jwt
    from tests.conftest import mock_verify_jwt
    async def mock_verify(): return identity_id
    app.dependency_overrides[verify_jwt] = mock_verify
    
    yield data
    
    app.dependency_overrides[verify_jwt] = mock_verify_jwt

@pytest.mark.asyncio
async def test_edit_rbac_403_faculty(seeded_env):
    _set_roles({"faculty"})
    tenant_id = seeded_env["tenant_id"]
    version_id = seeded_env["version_id"]
    assignment_id = seeded_env["assignment_id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/edit",
            json={"version_no": 1, "assignment_id": str(assignment_id), "slot_start": 5},
        )
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_edit_rbac_200_department_head(seeded_env):
    _set_roles({"department_head"})
    tenant_id = seeded_env["tenant_id"]
    version_id = seeded_env["version_id"]
    assignment_id = seeded_env["assignment_id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/edit",
            json={"version_no": 1, "assignment_id": str(assignment_id), "slot_start": 2},
        )
    assert res.status_code != 403

@pytest.mark.asyncio
async def test_edit_conflict_stale_version_no(seeded_env):
    _set_roles({"institution_admin"})
    tenant_id = seeded_env["tenant_id"]
    version_id = seeded_env["version_id"]
    assignment_id = seeded_env["assignment_id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/edit",
            json={"version_no": 999, "assignment_id": str(assignment_id), "slot_start": 5},
        )
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "CONFLICT"

@pytest.mark.asyncio
async def test_edit_rejects_infeasible_change(seeded_env, superuser_session):
    _set_roles({"institution_admin"})
    tenant_id = seeded_env["tenant_id"]
    version_id = seeded_env["version_id"]
    second_id = uuid.uuid4()
    
    from app.models.assignment import Assignment as AssignmentModel
    superuser_session.add(AssignmentModel(
        id=second_id, timetable_version_id=version_id, tenant_id=tenant_id,
        staff_profile_id=seeded_env["staff_id"], course_id=seeded_env["course_id"], cohort_id=seeded_env["cohort_id"],
        room_id=seeded_env["room2_id"], slot_start=3, slot_span=1,
    ))
    await superuser_session.commit()
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/edit",
            json={"version_no": 1, "assignment_id": str(second_id), "slot_start": 0},
        )
    assert res.status_code == 422
    assert res.json()["detail"]["error"]["code"] == "INFEASIBLE_CONFIGURATION"

@pytest.mark.asyncio
async def test_edit_applies_and_increments_version(seeded_env, superuser_session):
    _set_roles({"institution_admin"})
    tenant_id = seeded_env["tenant_id"]
    version_id = seeded_env["version_id"]
    assignment_id = seeded_env["assignment_id"]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/edit",
            json={"version_no": 1, "assignment_id": str(assignment_id), "slot_start": 7},
        )
    assert res.status_code == 200
    assert res.json()["new_version_no"] == 2

    from app.models.assignment import Assignment as AssignmentModel
    from app.models.timetable_version import TimetableVersion as TV
    
    r = await superuser_session.execute(_select(AssignmentModel).where(AssignmentModel.id == assignment_id))
    row = r.scalar_one()
    assert row.slot_start == 7
    assert row.is_locked is True
    r = await superuser_session.execute(_select(TV).where(TV.id == version_id))
    tv = r.scalar_one()
    assert tv.version_no == 2

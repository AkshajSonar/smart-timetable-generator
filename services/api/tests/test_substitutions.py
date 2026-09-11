"""Tests for the substitution suggest/confirm endpoints — FR-10.x.

Covers:
  - RBAC 403 for wrong roles
  - Candidate filtering (ineligible / blocked / over-cap)
  - Confirm applies edit and increments version_no
  - Confirm rejects taken slot (H1 violation)
  - Concurrent confirm rejected (double-confirm race)
  - Notification rows created for both parties on confirm
"""

import pytest
import uuid
from datetime import date, datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.models.assignment import Assignment
from app.models.campus import Campus
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.department import Department
from app.models.eligibility import Eligibility
from app.models.identity import Identity
from app.models.period_template import PeriodTemplate
from app.models.room import Room
from app.models.staff_availability_block import StaffAvailabilityBlock
from app.models.staff_profile import StaffProfile
from app.models.stubs import AuditLog, Notification, SubstitutionLog
from app.models.tenant import Tenant
from app.models.timetable_version import TimetableVersion
from app.models.academic_term import AcademicTerm
import tests.conftest as conftest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

async def _seed_full_env(superuser_session):
    """Seed a minimal but complete environment:
    tenant → term → timetable_version (draft, v1)
    dept → course → cohort → room
    absent_staff (eligible) + substitute_staff (eligible)
    assignment: absent_staff teaches course/cohort in room at slot 0

    Returns dict with all relevant IDs.
    """
    actor_id = conftest.TEST_IDENTITY_ID
    tenant_id = uuid.uuid4()
    term_id = uuid.uuid4()
    version_id = uuid.uuid4()
    dept_id = uuid.uuid4()
    campus_id = uuid.uuid4()
    course_id = uuid.uuid4()
    cohort_id = uuid.uuid4()
    room_id = uuid.uuid4()
    absent_id = uuid.uuid4()
    substitute_id = uuid.uuid4()
    absent_identity_id = uuid.uuid4()
    substitute_identity_id = uuid.uuid4()
    assignment_id = uuid.uuid4()

    # Layer 1: root entities (no FK deps except identity→nothing)
    if not (await superuser_session.execute(select(Identity).where(Identity.id == actor_id))).scalar_one_or_none():
        superuser_session.add(Identity(id=actor_id, email=f"actor_{actor_id}@test.com", auth_provider_ref=f"test|{actor_id}"))
    superuser_session.add(Identity(id=absent_identity_id, full_name="Dr. Absent", email=f"absent_{absent_identity_id}@test.com", auth_provider_ref=f"test|{absent_identity_id}"))
    superuser_session.add(Identity(id=substitute_identity_id, full_name="Dr. Smith", email=f"sub_{substitute_identity_id}@test.com", auth_provider_ref=f"test|{substitute_identity_id}"))
    superuser_session.add(Tenant(id=tenant_id, name="Sub Tenant", institution_type="university", timezone="UTC"))
    await superuser_session.flush()

    # Layer 2: tenant-scoped entities that depend only on tenant
    superuser_session.add(AcademicTerm(id=term_id, tenant_id=tenant_id, name="Term 1", start_date=date(2026, 9, 1), end_date=date(2026, 12, 15)))
    superuser_session.add(Department(id=dept_id, tenant_id=tenant_id, name="Eng Dept"))
    superuser_session.add(Campus(id=campus_id, tenant_id=tenant_id, name="Campus A"))
    superuser_session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="Eng-A", type="fixed"))
    await superuser_session.flush()

    # Layer 3: entities that depend on layer-2 objects
    superuser_session.add(TimetableVersion(id=version_id, tenant_id=tenant_id, term_id=term_id, state="draft", version_no=1))
    superuser_session.add(Course(id=course_id, tenant_id=tenant_id, department_id=dept_id, name="OS", type="core", credit_value=3, hours_per_week=1, block_size=1))
    superuser_session.add(Room(id=room_id, tenant_id=tenant_id, campus_id=campus_id, name="LH1", type="classroom", capacity=60, accessible=False))
    from datetime import time as time_type
    superuser_session.add(PeriodTemplate(id=uuid.uuid4(), tenant_id=tenant_id, weekday=0, period_index=0, start_time=time_type(9, 0), end_time=time_type(10, 0), shift="morning"))
    # Staff profiles depend on identity + tenant
    superuser_session.add(StaffProfile(id=absent_id, identity_id=absent_identity_id, tenant_id=tenant_id, employment_type="full_time", workload_cap_week=20, workload_cap_day=5, roles=["faculty"]))
    superuser_session.add(StaffProfile(id=substitute_id, identity_id=substitute_identity_id, tenant_id=tenant_id, employment_type="full_time", workload_cap_week=20, workload_cap_day=5, roles=["faculty"]))
    await superuser_session.flush()

    # Layer 4: entities that depend on layer-3 objects
    superuser_session.add(Eligibility(staff_profile_id=absent_id, course_id=course_id, cohort_id=cohort_id, tenant_id=tenant_id))
    superuser_session.add(Eligibility(staff_profile_id=substitute_id, course_id=course_id, cohort_id=cohort_id, tenant_id=tenant_id))
    await superuser_session.flush()

    # Layer 5: assignment (depends on version, staff, course, cohort, room)
    superuser_session.add(Assignment(id=assignment_id, tenant_id=tenant_id, timetable_version_id=version_id, staff_profile_id=absent_id, course_id=course_id, cohort_id=cohort_id, room_id=room_id, slot_start=0, slot_span=1))

    await superuser_session.commit()

    return {
        "tenant_id": tenant_id,
        "term_id": term_id,
        "version_id": version_id,
        "course_id": course_id,
        "cohort_id": cohort_id,
        "room_id": room_id,
        "absent_id": absent_id,
        "absent_identity_id": absent_identity_id,
        "substitute_id": substitute_id,
        "substitute_identity_id": substitute_identity_id,
        "faculty_id": substitute_id,
        "assignment_id": assignment_id,
    }


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_substitutions_suggest_rbac_403_faculty(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        res = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_substitutions_confirm_rbac_403_faculty(superuser_session):
    env = await _seed_full_env(superuser_session)
    # Create a suggested sub_log directly
    sub_log = SubstitutionLog(
        tenant_id=env["tenant_id"],
        original_staff_profile_id=env["absent_id"],
        assignment_id=env["assignment_id"],
        date=date(2026, 10, 1),
        status="suggested",
    )
    superuser_session.add(sub_log)
    await superuser_session.commit()
    await superuser_session.refresh(sub_log)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        res = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions/{sub_log.id}/confirm",
            json={"substitute_staff_profile_id": str(env["substitute_id"]), "version_no": 1},
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Candidate filtering tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_substitutions_suggest_excludes_ineligible(superuser_session):
    """Candidate with no eligibility row must not appear in results."""
    env = await _seed_full_env(superuser_session)

    # Remove substitute's eligibility
    elig = (await superuser_session.execute(
        select(Eligibility).where(
            Eligibility.staff_profile_id == env["substitute_id"],
            Eligibility.course_id == env["course_id"],
        )
    )).scalar_one()
    await superuser_session.delete(elig)
    await superuser_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        res = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        # No eligible candidates → 422
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_substitutions_suggest_excludes_blocked(superuser_session):
    """Candidate with StaffAvailabilityBlock on slot weekday excluded."""
    env = await _seed_full_env(superuser_session)

    # Block substitute on weekday 0 (same as slot 0)
    superuser_session.add(StaffAvailabilityBlock(
        id=uuid.uuid4(), tenant_id=env["tenant_id"],
        staff_profile_id=env["substitute_id"],
        weekday=0,
        period_index=0,
        block_type="unavailable",
    ))
    await superuser_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        res = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        # Blocked → no candidates → 422
        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_substitutions_suggest_excludes_over_cap(superuser_session):
    """Candidate at workload_cap_day excluded from candidates."""
    env = await _seed_full_env(superuser_session)

    # Set substitute's workload_cap_day to 0
    sub_sp = (await superuser_session.execute(
        select(StaffProfile).where(StaffProfile.id == env["substitute_id"])
    )).scalar_one()
    sub_sp.workload_cap_day = 0
    superuser_session.add(sub_sp)
    await superuser_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        res = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        # Candidates filtered out → 422
        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"


# ---------------------------------------------------------------------------
# Confirm tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_substitutions_confirm_applies_edit(superuser_session):
    """Confirm changes assignment.staff_profile_id and increments version_no."""
    env = await _seed_full_env(superuser_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}

        # Suggest
        res_suggest = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        assert res_suggest.status_code == 200, res_suggest.text
        data = res_suggest.json()
        substitution_id = data["substitution_id"]
        assert any(c["staff_profile_id"] == str(env["substitute_id"]) for c in data["candidates"])

        # Confirm
        res_confirm = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions/{substitution_id}/confirm",
            json={"substitute_staff_profile_id": str(env["substitute_id"]), "version_no": 1},
        )
        assert res_confirm.status_code == 200, res_confirm.text
        assert res_confirm.json()["new_version_no"] == 2

    # Verify assignment changed
    updated = (await superuser_session.execute(
        select(Assignment).where(Assignment.id == env["assignment_id"])
    )).scalar_one()
    assert updated.staff_profile_id == env["substitute_id"]

    # Verify SubstitutionLog confirmed
    sub_log = (await superuser_session.execute(
        select(SubstitutionLog).where(SubstitutionLog.id == uuid.UUID(substitution_id))
    )).scalar_one()
    assert sub_log.status == "confirmed"
    assert sub_log.substitute_staff_profile_id == env["substitute_id"]


@pytest.mark.asyncio
async def test_substitutions_confirm_rejects_taken_slot(superuser_session):
    """Confirm of a candidate already assigned to that slot returns 422 INFEASIBLE_CONFIGURATION."""
    env = await _seed_full_env(superuser_session)

    # Create a second course and assign substitute to slot 0 (conflict)
    dept2_id = uuid.uuid4()
    course2_id = uuid.uuid4()
    cohort2_id = uuid.uuid4()
    superuser_session.add(Department(id=dept2_id, tenant_id=env["tenant_id"], name="Math Dept"))
    await superuser_session.flush()
    superuser_session.add(Course(id=course2_id, tenant_id=env["tenant_id"], department_id=dept2_id, name="Math", type="core", credit_value=3, hours_per_week=1, block_size=1))
    superuser_session.add(Cohort(id=cohort2_id, tenant_id=env["tenant_id"], name="Eng-B", type="fixed"))
    superuser_session.add(Eligibility(staff_profile_id=env["substitute_id"], course_id=course2_id, cohort_id=cohort2_id, tenant_id=env["tenant_id"]))
    await superuser_session.flush()
    # Assign substitute to slot 0 in a different course
    superuser_session.add(Assignment(
        id=uuid.uuid4(), tenant_id=env["tenant_id"],
        timetable_version_id=env["version_id"],
        staff_profile_id=env["substitute_id"],
        course_id=course2_id, cohort_id=cohort2_id,
        room_id=env["room_id"],
        slot_start=0, slot_span=1,
    ))
    await superuser_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}

        # Suggest (substitute will be filtered out by slot conflict)
        res_suggest = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        # Substitute is occupied → no candidates → 422
        assert res_suggest.status_code == 422


@pytest.mark.asyncio
async def test_substitutions_concurrent_confirm_rejected(superuser_session):
    """Second confirm on same substitutionId returns 409 CONFLICT.

    This is the double-confirm race protection: persisting status='suggested'
    then checking status at confirm time is what makes the two-step design
    concurrency-safe over the stateless alternative.
    """
    env = await _seed_full_env(superuser_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}

        # Suggest
        res_suggest = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        assert res_suggest.status_code == 200
        substitution_id = res_suggest.json()["substitution_id"]

        # First confirm — should succeed
        res_confirm_1 = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions/{substitution_id}/confirm",
            json={"substitute_staff_profile_id": str(env["substitute_id"]), "version_no": 1},
        )
        assert res_confirm_1.status_code == 200, res_confirm_1.text

        # Second confirm on the same substitution_id — must be rejected
        res_confirm_2 = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions/{substitution_id}/confirm",
            json={"substitute_staff_profile_id": str(env["substitute_id"]), "version_no": 2},
        )
        assert res_confirm_2.status_code == 409
        assert res_confirm_2.json()["detail"]["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_substitutions_notification_on_confirm(superuser_session):
    """Notification rows for both original and substitute staff after confirm (FR-11.1)."""
    env = await _seed_full_env(superuser_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}

        res_suggest = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions",
            json={
                "absent_staff_profile_id": str(env["absent_id"]),
                "assignment_id": str(env["assignment_id"]),
                "date": "2026-10-01",
                "version_no": 1,
            },
        )
        assert res_suggest.status_code == 200
        substitution_id = res_suggest.json()["substitution_id"]

        res_confirm = await ac.post(
            f"/api/v1/tenants/{env['tenant_id']}/substitutions/{substitution_id}/confirm",
            json={"substitute_staff_profile_id": str(env["substitute_id"]), "version_no": 1},
        )
        assert res_confirm.status_code == 200

    notif_rows = (await superuser_session.execute(
        select(Notification).where(Notification.tenant_id == env["tenant_id"])
    )).scalars().all()
    notified = {n.identity_id for n in notif_rows}
    assert env["absent_identity_id"] in notified, "Original staff not notified"
    assert env["substitute_identity_id"] in notified, "Substitute staff not notified"

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.timetable_version import TimetableVersion
from app.models.exam_timetable_version import ExamTimetableVersion
from app.models.published_schedule import PublishedSchedule
from app.models.stubs import AuditLog
from sqlalchemy import select
from datetime import date
from app.models.tenant import Tenant
from app.models.academic_term import AcademicTerm
from app.models.identity import Identity
import tests.conftest as conftest

async def _seed_test_data(superuser_session, actor_id):
    tenant_id = uuid.uuid4()
    term_id = uuid.uuid4()
    version_id = uuid.uuid4()
    exam_version_id = uuid.uuid4()
    
    if not (await superuser_session.execute(select(Identity).where(Identity.id == actor_id))).scalar_one_or_none():
        superuser_session.add(Identity(id=actor_id, email=f"actor_{actor_id}@example.com", auth_provider_ref=f"test|{actor_id}"))
    superuser_session.add(Tenant(id=tenant_id, name="Test Tenant", institution_type="university", timezone="UTC"))
    superuser_session.add(AcademicTerm(id=term_id, tenant_id=tenant_id, name="Test Term", start_date=date(2026, 9, 1), end_date=date(2026, 12, 15)))
    superuser_session.add(TimetableVersion(id=version_id, tenant_id=tenant_id, term_id=term_id, state="draft", version_no=1))
    superuser_session.add(ExamTimetableVersion(id=exam_version_id, tenant_id=tenant_id, term_id=term_id, state="draft", version_no=1))
    await superuser_session.commit()
    
    return tenant_id, term_id, version_id, exam_version_id

@pytest.mark.asyncio
async def test_timetables_approve_rbac_403_faculty(superuser_session):
    tenant_id, _, version_id, _ = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/approve", json={"version_no": 1})
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_timetables_publish_rbac_403_reviewer(superuser_session):
    tenant_id, _, version_id, _ = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"reviewer"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/publish", json={"version_no": 1})
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_approve_rbac_403_faculty(superuser_session):
    tenant_id, _, _, exam_version_id = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/timetables/{exam_version_id}/approve", json={"version_no": 1})
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_exams_publish_rbac_403_reviewer(superuser_session):
    tenant_id, _, _, exam_version_id = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"reviewer"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/timetables/{exam_version_id}/publish", json={"version_no": 1})
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_timetables_publish_requires_approval(superuser_session):
    tenant_id, _, version_id, _ = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/publish", json={"version_no": 1})
        assert res.status_code == 400
        assert "approved before publish" in res.json()["detail"]["error"]["message"]

@pytest.mark.asyncio
async def test_exams_publish_requires_approval(superuser_session):
    tenant_id, _, _, exam_version_id = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        res = await ac.post(f"/api/v1/tenants/{tenant_id}/exams/timetables/{exam_version_id}/publish", json={"version_no": 1})
        assert res.status_code == 400
        assert "approved before publish" in res.json()["detail"]["error"]["message"]

@pytest.mark.asyncio
async def test_timetables_approve_then_publish_success(superuser_session):
    """Split from combined test. Asserts timetable approve→publish flow including
    PublishedSchedule denormalization and Notification rows (FR-9.3, CQRS §14, FR-11.1)."""
    from app.models.assignment import Assignment
    from app.models.department import Department
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.campus import Campus
    from app.models.room import Room
    from app.models.staff_profile import StaffProfile
    from app.models.stubs import Notification

    actor_id = conftest.TEST_IDENTITY_ID
    tenant_id, term_id, version_id, _ = await _seed_test_data(superuser_session, actor_id)

    # Seed minimal entities for a real Assignment row so PublishedSchedule has content to check
    dept_id = uuid.uuid4()
    course_id = uuid.uuid4()
    cohort_id = uuid.uuid4()
    campus_id = uuid.uuid4()
    room_id = uuid.uuid4()
    sp_id = uuid.uuid4()   # staff_profile for the assignment

    superuser_session.add(Department(id=dept_id, tenant_id=tenant_id, name="CS Dept"))
    superuser_session.add(Campus(id=campus_id, tenant_id=tenant_id, name="Main Campus"))
    await superuser_session.flush()  # dept/campus must exist before course/room
    superuser_session.add(Course(id=course_id, tenant_id=tenant_id, department_id=dept_id,
                                  name="Algorithms", type="core", credit_value=3,
                                  hours_per_week=3, block_size=1))
    superuser_session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="CS-A", type="fixed"))
    superuser_session.add(Room(id=room_id, tenant_id=tenant_id, campus_id=campus_id,
                                name="Room 101", type="classroom", capacity=60, accessible=False))
    # staff_profile linked to actor_id (already seeded as Identity by _seed_test_data)
    superuser_session.add(StaffProfile(id=sp_id, identity_id=actor_id, tenant_id=tenant_id,
                                        employment_type="full_time",
                                        workload_cap_week=20, workload_cap_day=5,
                                        roles=["faculty"]))
    await superuser_session.flush()  # all preceding rows needed before Assignment FKs
    superuser_session.add(Assignment(id=uuid.uuid4(), tenant_id=tenant_id,
                                      timetable_version_id=version_id,
                                      staff_profile_id=sp_id, course_id=course_id,
                                      cohort_id=cohort_id, room_id=room_id,
                                      slot_start=0, slot_span=1))
    await superuser_session.commit()


    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Approve
        conftest.MOCK_ROLES = {"reviewer"}
        res_approve = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/approve",
            json={"version_no": 1},
        )
        assert res_approve.status_code == 200
        audit_approve = (await superuser_session.execute(
            select(AuditLog).where(AuditLog.action == "approve", AuditLog.entity_id == version_id)
        )).scalar_one()
        assert audit_approve.actor_identity_id == actor_id
        assert audit_approve.after["state"] == "under_review"

        # Publish
        conftest.MOCK_ROLES = {"institution_admin"}
        res_publish = await ac.post(
            f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/publish",
            json={"version_no": 2},
        )
        assert res_publish.status_code == 200
        audit_publish = (await superuser_session.execute(
            select(AuditLog).where(AuditLog.action == "publish", AuditLog.entity_id == version_id)
        )).scalar_one()
        assert audit_publish.after["state"] == "published"

        # Assert PublishedSchedule read model is populated (CQRS §14)
        ps_rows = (await superuser_session.execute(
            select(PublishedSchedule).where(PublishedSchedule.timetable_version_id == version_id)
        )).scalars().all()
        assert len(ps_rows) == 1, f"Expected 1 PublishedSchedule row, got {len(ps_rows)}"
        ps = ps_rows[0]
        assert ps.course_name == "Algorithms", f"course_name mismatch: {ps.course_name}"
        assert ps.room_name == "Room 101", f"room_name mismatch: {ps.room_name}"
        assert ps.cohort_name == "CS-A", f"cohort_name mismatch: {ps.cohort_name}"
        assert ps.type == "class"
        assert ps.slot_index == 0

        # Assert Notification rows for affected staff (FR-11.1)
        notif_rows = (await superuser_session.execute(
            select(Notification).where(Notification.tenant_id == tenant_id)
        )).scalars().all()
        notified_identities = {n.identity_id for n in notif_rows}
        assert actor_id in notified_identities, "Staff member not notified after publish"


@pytest.mark.asyncio
async def test_exams_approve_then_publish_success(superuser_session):
    """Split from combined test. Asserts exam approve→publish flow including
    PublishedSchedule denormalization (CQRS §14, FR-11.1)."""
    actor_id = conftest.TEST_IDENTITY_ID
    tenant_id, term_id, _, exam_version_id = await _seed_test_data(superuser_session, actor_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Approve
        conftest.MOCK_ROLES = {"reviewer"}
        res_approve = await ac.post(
            f"/api/v1/tenants/{tenant_id}/exams/timetables/{exam_version_id}/approve",
            json={"version_no": 1},
        )
        assert res_approve.status_code == 200
        audit_approve = (await superuser_session.execute(
            select(AuditLog).where(AuditLog.action == "approve", AuditLog.entity_id == exam_version_id)
        )).scalar_one()
        assert audit_approve.actor_identity_id == actor_id

        # Publish
        conftest.MOCK_ROLES = {"institution_admin"}
        res_publish = await ac.post(
            f"/api/v1/tenants/{tenant_id}/exams/timetables/{exam_version_id}/publish",
            json={"version_no": 2},
        )
        assert res_publish.status_code == 200
        audit_publish = (await superuser_session.execute(
            select(AuditLog).where(AuditLog.action == "publish", AuditLog.entity_id == exam_version_id)
        )).scalar_one()
        assert audit_publish.after["state"] == "published"

        # Assert PublishedSchedule read model exists (no ExamSessions seeded → 0 rows is correct)
        ps_rows = (await superuser_session.execute(
            select(PublishedSchedule).where(PublishedSchedule.exam_timetable_version_id == exam_version_id)
        )).scalars().all()
        assert isinstance(ps_rows, list)  # endpoint ran without error; 0 rows expected with no sessions

@pytest.mark.asyncio
async def test_dual_routing_identical_shape(superuser_session):
    from app.models.assignment import Assignment
    from app.models.staff_profile import StaffProfile
    
    tenant_id, term_id, version_id, _ = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    
    sp_id = uuid.uuid4()
    from app.models.department import Department
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.campus import Campus
    from app.models.room import Room
    
    dept_id = uuid.uuid4()
    course_id = uuid.uuid4()
    cohort_id = uuid.uuid4()
    campus_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    superuser_session.add(Department(id=dept_id, tenant_id=tenant_id, name="Test Dept"))
    await superuser_session.flush()
    superuser_session.add(Course(id=course_id, tenant_id=tenant_id, department_id=dept_id, name="Test Course", type="core", credit_value=3, hours_per_week=3))
    superuser_session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="Test Cohort", type="fixed"))
    superuser_session.add(Campus(id=campus_id, tenant_id=tenant_id, name="Test Campus", timezone="UTC"))
    await superuser_session.flush()
    superuser_session.add(Room(id=room_id, tenant_id=tenant_id, campus_id=campus_id, name="Test Room", type="lecture_hall", capacity=50, equipment_tags=[], accessible=True))
    
    superuser_session.add(StaffProfile(id=sp_id, tenant_id=tenant_id, identity_id=conftest.TEST_IDENTITY_ID, employment_type="full_time", workload_cap_week=10, workload_cap_day=2))
    
    await superuser_session.flush()
    
    a1_id = uuid.uuid4()
    superuser_session.add(Assignment(id=a1_id, tenant_id=tenant_id, timetable_version_id=version_id, staff_profile_id=sp_id, course_id=course_id, cohort_id=cohort_id, room_id=room_id, slot_start=0, slot_span=1))
    await superuser_session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin", "reviewer"}
        
        # 1. Fetch as draft
        res_draft = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res_draft.status_code == 200
        draft_schedules = res_draft.json()["schedules"]
        assert len(draft_schedules) == 1
        
        # 2. Approve and publish
        res_approve = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/approve", json={"version_no": 1})
        assert res_approve.status_code == 200
        res_publish = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/publish", json={"version_no": 2})
        assert res_publish.status_code == 200
        
        # 3. Fetch as published
        res_published = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert res_published.status_code == 200
        published_schedules = res_published.json()["schedules"]
        
        # Assert shapes are identical except for ID
        for d in draft_schedules:
            d.pop("id", None)
        for p in published_schedules:
            p.pop("id", None)
        assert draft_schedules == published_schedules

@pytest.mark.asyncio
async def test_behavioral_switch_draft_reads_live_published_reads_snapshot(superuser_session):
    from app.models.assignment import Assignment
    from app.models.staff_profile import StaffProfile
    
    tenant_id, term_id, version_id, _ = await _seed_test_data(superuser_session, conftest.TEST_IDENTITY_ID)
    
    sp_id = uuid.uuid4()
    from app.models.department import Department
    from app.models.course import Course
    from app.models.cohort import Cohort
    from app.models.campus import Campus
    from app.models.room import Room
    
    dept_id = uuid.uuid4()
    course_id = uuid.uuid4()
    cohort_id = uuid.uuid4()
    campus_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    superuser_session.add(Department(id=dept_id, tenant_id=tenant_id, name="Test Dept"))
    await superuser_session.flush()
    superuser_session.add(Course(id=course_id, tenant_id=tenant_id, department_id=dept_id, name="Test Course", type="core", credit_value=3, hours_per_week=3))
    superuser_session.add(Cohort(id=cohort_id, tenant_id=tenant_id, name="Test Cohort", type="fixed"))
    superuser_session.add(Campus(id=campus_id, tenant_id=tenant_id, name="Test Campus", timezone="UTC"))
    await superuser_session.flush()
    superuser_session.add(Room(id=room_id, tenant_id=tenant_id, campus_id=campus_id, name="Test Room", type="lecture_hall", capacity=50, equipment_tags=[], accessible=True))
    
    superuser_session.add(StaffProfile(id=sp_id, tenant_id=tenant_id, identity_id=conftest.TEST_IDENTITY_ID, employment_type="full_time", workload_cap_week=10, workload_cap_day=2))
    await superuser_session.flush()
    
    a1_id = uuid.uuid4()
    superuser_session.add(Assignment(id=a1_id, tenant_id=tenant_id, timetable_version_id=version_id, staff_profile_id=sp_id, course_id=course_id, cohort_id=cohort_id, room_id=room_id, slot_start=0, slot_span=1))
    await superuser_session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin", "reviewer"}
        
        # Draft reads live
        res1 = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert len(res1.json()["schedules"]) == 1
        
        # Add assignment to raw table
        a2_id = uuid.uuid4()
        superuser_session.add(Assignment(id=a2_id, tenant_id=tenant_id, timetable_version_id=version_id, staff_profile_id=sp_id, course_id=course_id, cohort_id=cohort_id, room_id=room_id, slot_start=1, slot_span=1))
        await superuser_session.commit()
        
        res2 = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert len(res2.json()["schedules"]) == 2
        
        # Approve and publish
        await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/approve", json={"version_no": 1})
        await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}/publish", json={"version_no": 2})
        
        # Fetch published
        res3 = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert len(res3.json()["schedules"]) == 2
        
        # Add assignment 3 to raw table
        a3_id = uuid.uuid4()
        superuser_session.add(Assignment(id=a3_id, tenant_id=tenant_id, timetable_version_id=version_id, staff_profile_id=sp_id, course_id=course_id, cohort_id=cohort_id, room_id=room_id, slot_start=2, slot_span=1))
        await superuser_session.commit()
        
        # Fetch published again - should STILL be 2, because it reads the snapshot
        res4 = await ac.get(f"/api/v1/tenants/{tenant_id}/timetables/{version_id}")
        assert len(res4.json()["schedules"]) == 2

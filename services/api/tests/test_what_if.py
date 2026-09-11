import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.main import app
import tests.conftest as conftest

@pytest.mark.asyncio
async def test_what_if_leaves_db_unchanged(superuser_session: AsyncSession):
    # Setup test env
    from tests.test_rules import _seed_full_env
    env = await _seed_full_env(superuser_session)
    tenant_id = env["tenant_id"]

    conftest.MOCK_ROLES = {"institution_admin"}
    conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID

    # Count rows before
    async def get_row_counts():
        counts = {}
        for table in ["assignment", "timetable_version"]:
            res = await superuser_session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid").bindparams(tid=tenant_id))
            counts[table] = res.scalar()
        return counts

    counts_before = await get_row_counts()

    # Call what-if
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        gen_payload = {"term_id": str(env["term_id"])}
        resp = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate/what-if", json=gen_payload)
        assert resp.status_code == 200, resp.json()
        data = resp.json()

        # Should return assignments in the response directly
        assert data["status"] == "success"
        assert "assignments" in data
        assert len(data["assignments"]) > 0

    # Count rows after
    counts_after = await get_row_counts()

    assert counts_before == counts_after, "DB should be unchanged by what-if simulation"

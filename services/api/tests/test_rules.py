import pytest
from httpx import AsyncClient, ASGITransport
from uuid import UUID

from app.main import app
from tests.test_substitutions import _seed_full_env
from tests import conftest
from app.models.constraint_rule import ConstraintRule
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


# --- Mocking the LLM ---
class MockChoice:
    def __init__(self, parsed):
        self.message = MockMessage(parsed)

class MockMessage:
    def __init__(self, parsed):
        self.parsed = parsed

class MockResponse:
    def __init__(self, parsed):
        self.choices = [MockChoice(parsed)]

class MockAsyncOpenAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.beta = MockBeta()

class MockBeta:
    def __init__(self):
        self.chat = MockChat()

class MockChat:
    def __init__(self):
        self.completions = MockCompletions()

class MockCompletions:
    async def parse(self, model, messages, response_format):
        text = messages[1]["content"]
        if "invalid" in text:
            parsed = response_format(
                rule_type="unsupported",
                scope="tenant",
            )
        else:
            parsed = response_format(
                rule_type="max_periods_per_day",
                scope="faculty",
                target_id="Dr. Smith",
                threshold=4.0,
                unit="periods",
                polarity="max"
            )
        return MockResponse(parsed)


@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    import app.rule_parser.llm_client
    monkeypatch.setattr(app.rule_parser.llm_client, "AsyncOpenAI", MockAsyncOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-no-real-calls")
    import app.core.config
    monkeypatch.setattr(app.core.config.settings, "openai_api_key", "test-key-no-real-calls")


@pytest.mark.asyncio
async def test_rule_parse_never_auto_confirms(superuser_session):
    """
    test_rule_parse_never_auto_confirms:
    parse alone leaves status='pending_confirmation'.
    It only flips to 'confirmed' after /confirm.
    NOTE: The DB-level contract is verified here. Generation-level assertion (Step 2) deferred.
    """
    env = await _seed_full_env(superuser_session)
    tenant_id = env["tenant_id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID
        
        # 1. Parse
        resp = await ac.post(
            f"/api/v1/tenants/{tenant_id}/rules/parse",
            json={"text": "no faculty teaches more than 4 periods a day for Dr. Smith"}
        )
        assert resp.status_code == 200, resp.json()
        data = resp.json()
        rule_id = data["id"]

        # Verify it's pending in DB
        q = await superuser_session.execute(select(ConstraintRule).where(ConstraintRule.id == UUID(rule_id)))
        rule = q.scalar_one()
        assert rule.status == "pending_confirmation"

        # 2. Generation before confirm (rule is pending, should have no effect)
        faculty_id = env["substitute_id"]
        # Wait, the rule is "max 4 periods a day for Dr. Smith". To make it fail, we should set it to 0.
        # But the mock LLM returns threshold=4. We can update it in DB to 0 for the test.
        rule.threshold = 0
        
        # Also remove f_absent's eligibility so f_substitute is the ONLY one who can teach the course.
        # Otherwise CP-SAT will just assign the course to f_absent and return FEASIBLE!
        await superuser_session.execute(
            text("DELETE FROM eligibility WHERE staff_profile_id = :fid").bindparams(fid=env["absent_id"])
        )
        await superuser_session.commit()
        
        gen_payload = {"term_id": str(env["term_id"])}
        gen_resp1 = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate", json=gen_payload)
        assert gen_resp1.status_code == 200

        # 3. Confirm
        conf_resp = await ac.post(f"/api/v1/tenants/{tenant_id}/rules/{rule_id}/confirm", json={})
        print("CONFIRM RESP:", conf_resp.json())
        assert conf_resp.status_code == 200

        # Verify it's confirmed in DB
        await superuser_session.refresh(rule)
        assert rule.status == "confirmed"

        # 4. Generation after confirm (rule is active, 0 threshold makes it infeasible)
        gen_resp2 = await ac.post(f"/api/v1/tenants/{tenant_id}/timetables/generate", json=gen_payload)
        assert gen_resp2.status_code == 422, "Generation should fail because the rule is now active and infeasible"
        assert gen_resp2.json()["detail"]["error"]["code"] == "INFEASIBLE_CONFIGURATION"


@pytest.mark.asyncio
async def test_rule_confirmation_text_is_templated_not_llm_output(superuser_session):
    """
    Mocks the LLM. Asserts the returned confirmation text matches the template's exact output
    and contains none of the LLM's own justification/explanation phrases.
    Since we use structured output (Pydantic), the LLM *can't* return extra text in the `parsed` object anyway.
    """
    env = await _seed_full_env(superuser_session)
    tenant_id = env["tenant_id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID

        raw_text = "no faculty teaches more than 4 periods a day for Dr. Smith"
        resp = await ac.post(
            f"/api/v1/tenants/{tenant_id}/rules/parse",
            json={"text": raw_text}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Exact templated text
        expected_text = f"You said: '{raw_text}'. I'll apply this as: Limit faculty to a maximum of 4 periods per day."
        assert data["confirmation_text"] == expected_text


@pytest.mark.asyncio
async def test_rule_type_rejects_out_of_enum(superuser_session):
    """
    If LLM maps to unsupported (simulated via 'invalid' in text), it returns 422 and doesn't persist.
    """
    env = await _seed_full_env(superuser_session)
    tenant_id = env["tenant_id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID

        resp = await ac.post(
            f"/api/v1/tenants/{tenant_id}/rules/parse",
            json={"text": "invalid rule string"}
        )
        assert resp.status_code == 422
        assert "Unsupported rule type" in resp.json()["detail"]


# --- RBAC Atomic Tests ---

@pytest.mark.asyncio
async def test_rule_parse_rbac_403_faculty(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        resp = await ac.post(f"/api/v1/tenants/{env['tenant_id']}/rules/parse", json={"text": "test"})
        assert resp.status_code == 403

@pytest.mark.asyncio
async def test_rule_parse_rbac_200_admin(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID
        resp = await ac.post(f"/api/v1/tenants/{env['tenant_id']}/rules/parse", json={"text": "no faculty teaches more than 4 periods a day for Dr. Smith"})
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_rule_confirm_rbac_403_faculty(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        # fake ruleId is fine, it will 403 before 404
        resp = await ac.post(f"/api/v1/tenants/{env['tenant_id']}/rules/00000000-0000-0000-0000-000000000000/confirm", json={})
        assert resp.status_code == 403

@pytest.mark.asyncio
async def test_rule_confirm_rbac_200_admin(superuser_session):
    env = await _seed_full_env(superuser_session)
    tenant_id = env["tenant_id"]

    # manually insert a rule
    rule = ConstraintRule(tenant_id=tenant_id, rule_type="max_periods_per_day", scope="faculty", status="pending_confirmation")
    superuser_session.add(rule)
    await superuser_session.commit()
    await superuser_session.refresh(rule)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID
        resp = await ac.post(f"/api/v1/tenants/{tenant_id}/rules/{rule.id}/confirm", json={})
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_rule_create_structured_rbac_403_faculty(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"faculty"}
        resp = await ac.post(f"/api/v1/tenants/{env['tenant_id']}/rules", json={"rule_type": "max_periods_per_day", "scope": "tenant"})
        assert resp.status_code == 403

@pytest.mark.asyncio
async def test_rule_create_structured_rbac_200_admin(superuser_session):
    env = await _seed_full_env(superuser_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        conftest.MOCK_ROLES = {"institution_admin"}
        conftest.MOCK_IDENTITY_ID = conftest.TEST_IDENTITY_ID
        resp = await ac.post(f"/api/v1/tenants/{env['tenant_id']}/rules", json={"rule_type": "max_periods_per_day", "scope": "tenant"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"


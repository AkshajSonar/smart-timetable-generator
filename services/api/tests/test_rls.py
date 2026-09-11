import pytest
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_rls_sql_enforcement(superuser_session):
    """Prove RLS is enforced natively by Postgres for app_user."""
    
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    course_a = uuid.uuid4()
    course_b = uuid.uuid4()
    
    dept_a = uuid.uuid4()
    dept_b = uuid.uuid4()
    
    await superuser_session.execute(text("TRUNCATE TABLE tenant CASCADE;"))
    
    await superuser_session.execute(text(f"INSERT INTO tenant (id, name, institution_type, timezone) VALUES ('{tenant_a}', 'A', 'college', 'UTC')"))
    await superuser_session.execute(text(f"INSERT INTO tenant (id, name, institution_type, timezone) VALUES ('{tenant_b}', 'B', 'college', 'UTC')"))
    
    await superuser_session.execute(text(f"INSERT INTO department (id, tenant_id, name) VALUES ('{dept_a}', '{tenant_a}', 'Dept A')"))
    await superuser_session.execute(text(f"INSERT INTO course (id, tenant_id, department_id, name, type, credit_value, hours_per_week) VALUES ('{course_a}', '{tenant_a}', '{dept_a}', 'Course A', 'core', 3, 3)"))
    
    await superuser_session.execute(text(f"INSERT INTO department (id, tenant_id, name) VALUES ('{dept_b}', '{tenant_b}', 'Dept B')"))
    await superuser_session.execute(text(f"INSERT INTO course (id, tenant_id, department_id, name, type, credit_value, hours_per_week) VALUES ('{course_b}', '{tenant_b}', '{dept_b}', 'Course B', 'core', 3, 3)"))
    await superuser_session.commit()
        
    async with AsyncSessionLocal() as session:
        await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_a}'"))
        res = await session.execute(text("SELECT id FROM course"))
        rows = res.fetchall()
        
        assert len(rows) == 1
        assert str(rows[0][0]) == str(course_a)
        
        await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_b}'"))
        res = await session.execute(text("SELECT id FROM course"))
        rows = res.fetchall()
        
        assert len(rows) == 1
        assert str(rows[0][0]) == str(course_b)

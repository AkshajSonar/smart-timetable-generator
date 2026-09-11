import asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import settings
from tests.conftest import _seed_test_data
from app.main import app

async def run():
    engine = create_async_engine(settings.database_url_superuser)
    Session = async_sessionmaker(engine)
    async with Session() as session:
        from tests.test_substitutions import _seed_full_env
        env = await _seed_full_env(session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            from tests.conftest import MOCK_ROLES
            # We can't easily mock the Depends locally like this without importing app and overrides
            # Let's just use pytest and modify test_substitutions.py to print!
            pass

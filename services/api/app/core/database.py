"""Async SQLAlchemy engine, session factory, and base model."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
engine_superuser = create_async_engine(settings.database_url_superuser, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
SuperuserAsyncSessionLocal = async_sessionmaker(engine_superuser, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_superuser() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async DB session that bypasses RLS."""
    async with SuperuserAsyncSessionLocal() as session:
        yield session

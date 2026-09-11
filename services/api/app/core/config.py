from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app_user:app_password@127.0.0.1:5433/timetable_db"
    # Synchronous URL for Alembic migrations
    database_url_sync: str = "postgresql://timetable:timetable@127.0.0.1:5433/timetable_db"
    database_url_superuser: str = "postgresql+asyncpg://timetable:timetable@127.0.0.1:5433/timetable_db"
    redis_url: str = "redis://localhost:6379/0"
    solver_timeout_seconds: int = 30
    JWT_ISSUER_URL: str | None = None
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

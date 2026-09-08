from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://timetable:timetable@127.0.0.1:5433/timetable_db"
    # Synchronous URL for Alembic migrations
    database_url_sync: str = "postgresql://timetable:timetable@127.0.0.1:5433/timetable_db"
    redis_url: str = "redis://localhost:6379/0"
    solver_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

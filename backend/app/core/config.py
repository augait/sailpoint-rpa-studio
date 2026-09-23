from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = Field(min_length=32)
    encryption_key: str
    jwt_minutes: int = Field(default=30, ge=1, le=120)
    artifact_dir: Path = Path("artifacts")
    allowed_origins: list[str] = []
    queue_name: str = "rpa"


@lru_cache
def settings() -> Settings:
    return Settings()

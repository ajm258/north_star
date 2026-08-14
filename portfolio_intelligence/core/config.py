from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://portfolio:portfolio@localhost:5432/portfolio_intelligence"
    admin_username: str = "admin"
    admin_password: str | None = None
    log_level: str = "INFO"
    upload_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    default_portfolio_timezone: str = "Europe/London"


@lru_cache
def get_settings() -> Settings:
    return Settings()

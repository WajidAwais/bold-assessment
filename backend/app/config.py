from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from the environment (or the repo-root .env)."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Owner role: runs migrations and the import.
    database_url: str = "postgresql+asyncpg://techforce:techforce@localhost:5433/techforce"
    # techforce_app: non-owner, no BYPASSRLS. Every Candidate read goes through it
    # (ADR-0002). The migration creates the role with this URL's password.
    app_database_url: str = (
        "postgresql+asyncpg://techforce_app:techforce_app@localhost:5433/techforce"
    )

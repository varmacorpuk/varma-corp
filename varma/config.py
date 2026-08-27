"""Runtime configuration. Secrets belong in .env (gitignored), never in git."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VARMA_",
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    env: str = "development"
    # SQLite under data/ is TEMPORARY DEVELOPMENT storage (StoragePort).
    database_url: str = f"sqlite:///{DATA_DIR / 'varma.db'}"
    timezone: str = "Europe/London"
    llm_provider: str = "fake"
    llm_api_key: str | None = None  # unused by default; never commit a live key
    board_member_stub_token: str = "dev-board-member"
    # Encrypted-at-rest backup key. Never commit. Not a live broker credential.
    backup_encryption_key: str | None = None
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # TEMPORARY DEVELOPMENT DEFAULTS — not Board-approved numbers (Doc 18 OPEN).
    temporary_brief_cost_cap_units: int = 100
    temporary_news_fresh_hours: int = 18
    temporary_price_fresh_hours: int = 26


def get_settings() -> Settings:
    return Settings()

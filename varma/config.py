"""Runtime configuration. Secrets belong in .env (gitignored), never in git."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PAPER_OPEN_DB_FILENAME = "varma_paper_open.db"
# Operational runtime ledger on the firm box. Never committed. Never overwritten
# by this repository's tests or PRs. Used only when the file already exists.
CANONICAL_PAPER_OPEN_DB = Path("/workspace/varma-canonical/varma_paper_open.db")


def operational_paper_open_db() -> Path:
    """Prefer the canonical runtime ledger when it is already present.

    Does not create or overwrite that file. Falls back to the repo data/
    practice book so tests and fresh checkouts stay isolated.
    """
    if CANONICAL_PAPER_OPEN_DB.is_file():
        return CANONICAL_PAPER_OPEN_DB
    return DATA_DIR / PAPER_OPEN_DB_FILENAME


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VARMA_",
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    env: str = "development"
    # SQLite under data/ is TEMPORARY DEVELOPMENT storage (StoragePort).
    # Operational box: /workspace/varma-canonical/varma_paper_open.db when present.
    database_url: str = f"sqlite:///{DATA_DIR / PAPER_OPEN_DB_FILENAME}"
    canonical_paper_open_db: str = str(CANONICAL_PAPER_OPEN_DB)
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

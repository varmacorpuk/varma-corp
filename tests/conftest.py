from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("VARMA_LLM_PROVIDER", "fake")
os.environ.setdefault("VARMA_BOARD_MEMBER_STUB_TOKEN", "dev-board-member")
os.environ.setdefault(
    "VARMA_BACKUP_ENCRYPTION_KEY",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
)

from varma.clock import LONDON
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.kernel.app import create_app

# Thursday 27 Aug 2026, 10:00 Europe/London — inside Addendum C window (UK open, before US close).
SESSION_OPEN = datetime(2026, 8, 27, 10, 0, tzinfo=LONDON)
LONDON_CASH_CLOSE = datetime(2026, 8, 27, 16, 30, tzinfo=LONDON)
BEFORE_UK_OPEN = datetime(2026, 8, 27, 7, 59, tzinfo=LONDON)
WEEKEND = datetime(2026, 8, 29, 10, 0, tzinfo=LONDON)


@pytest.fixture()
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def session(db_url: str) -> Session:
    init_db(db_url, reset=True)
    factory = get_session_factory(db_url, reset=False)
    s = factory()
    seed_if_empty(s)
    yield s
    s.close()
    init_db("sqlite:///:memory:", reset=True)  # drop global engine between tests


@pytest.fixture()
def client(db_url: str) -> TestClient:
    init_db(db_url, reset=True)
    factory = get_session_factory(db_url)
    s = factory()
    seed_if_empty(s)
    s.close()
    app = create_app()
    with TestClient(app) as c:
        yield c
    init_db("sqlite:///:memory:", reset=True)


BOARD_HEADERS = {"Authorization": "Bearer dev-board-member"}
EMPLOYEE_HEADERS = {"X-Varma-Employee": "market-intelligence-research"}
CEO_HEADERS = {"X-Varma-Employee": "ceo"}
CHALLENGE_HEADERS = {"X-Varma-Employee": "challenge"}
RISK_HEADERS = {"X-Varma-Employee": "risk"}
TRADER_HEADERS = {"X-Varma-Employee": "trader"}
QUANT_HEADERS = {"X-Varma-Employee": "quant-strategy"}
TECH_HEADERS = {"X-Varma-Employee": "technology"}

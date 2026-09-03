"""Tracked paper-OPEN ledger. Practice book only. LIVE stays blocked."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import SESSION_OPEN
from varma.db.models import PaperAccount, PaperFill, PaperPosition
from varma.observability.board import BoardObservability
from varma.paper.persist import (
    LEDGER_KIND,
    dump_paper_ledger,
    existing_shel_l_buy_5_fill,
    is_paper_open_book_session,
    maybe_restore_tracked_paper_ledger,
    restore_paper_ledger,
)
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.run_paper_trade_path import (
    DEFAULT_DEV_DB_FILENAME,
    PAPER_OPEN_DB_FILENAME,
    run_paper_trade_path,
)
from varma.skills.propose_paper_ticket import PAPER_20260903_02, PAPER_20260903_02_AT


def test_test_session_is_not_the_paper_open_book(session):
    assert is_paper_open_book_session(session) is False
    assert maybe_restore_tracked_paper_ledger(session) is None
    bind = str(session.get_bind().url)
    assert not bind.endswith(PAPER_OPEN_DB_FILENAME)
    assert DEFAULT_DEV_DB_FILENAME not in bind or "test" in bind


def _add_lse_to_allow_list(session):
    from varma.clock import now_london as _now
    from varma.db.models import AllowListInstrument
    now = _now()
    for sym in ("SHEL.L", "AZN.L", "ULVR.L"):
        if session.query(AllowListInstrument).filter_by(symbol=sym).one_or_none() is None:
            session.add(AllowListInstrument(symbol=sym, venue="LSE", approved_by="test-only", approved_at=now))
    session.commit()


def test_dump_restore_roundtrip_keeps_shel_l_fill(session):
    _add_lse_to_allow_list(session)
    result = run_paper_trade_path(
        session,
        started_by="cli",
        at=PAPER_20260903_02_AT,
        order=dict(PAPER_20260903_02),
    )
    assert result["filled"] is True
    assert result["live_fills"] is False
    assert result["trading_mode"] == "LIVE_BLOCKED"
    fill = session.query(PaperFill).one()
    fill_id = fill.id
    cash = session.get(PaperAccount, 1).cash
    payload = dump_paper_ledger(session, ticket_id="PAPER-20260903-02")
    assert payload["kind"] == LEDGER_KIND
    assert payload["is_live"] is False
    assert payload["trading_mode"] == "LIVE_BLOCKED"
    assert payload["fills"][0]["id"] == fill_id
    assert payload["fills"][0]["symbol"] == "SHEL.L"
    assert payload["fills"][0]["quantity"] == 5.0
    assert abs(payload["fills"][0]["price"] - 34.127093) < 1e-6
    assert abs(cash - 829.279217) < 1e-4

    session.query(PaperFill).delete()
    session.query(PaperPosition).delete()
    acc = session.get(PaperAccount, 1)
    acc.cash = 1000.0
    session.commit()
    assert session.query(PaperFill).count() == 0

    restored = restore_paper_ledger(session, payload)
    assert restored["fills"] == 1
    assert abs(restored["cash_gbp"] - 829.279217) < 1e-4
    again = session.query(PaperFill).one()
    assert again.id == fill_id
    pos = session.get(PaperPosition, "SHEL.L")
    assert pos is not None
    assert pos.quantity == 5.0
    assert existing_shel_l_buy_5_fill(session).id == fill_id
    assert LIVE_PORT_LOADED is False
    assert BROKER_PAPER_LOADED is False


def test_observability_floor_book_shows_fill_rows(session):
    _add_lse_to_allow_list(session)
    run_paper_trade_path(
        session,
        started_by="cli",
        at=SESSION_OPEN,
        order=dict(PAPER_20260903_02),
    )
    snap = BoardObservability(session).snapshot()
    ledger = snap["paper_ledger"]
    assert ledger["fills"] == 1
    assert abs(ledger["cash_gbp"] - 829.279217) < 1e-4
    assert ledger["open_positions"][0]["symbol"] == "SHEL.L"
    assert ledger["open_positions"][0]["quantity"] == 5.0
    assert ledger["fill_rows"][0]["symbol"] == "SHEL.L"
    assert abs(ledger["fill_rows"][0]["price"] - 34.127093) < 1e-6
    assert ledger["fill_rows"][0]["is_live"] is False
    assert snap["trading_mode"] == "LIVE_BLOCKED"


def test_gitignore_tracks_paper_open_book():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "!data/varma_paper_open.db" in text
    assert "!data/paper_open_ledger.json" in text
    assert "data/varma.db" in text or "Never commit data/varma.db" in text


def test_tracked_paper_open_ledger_has_shel_l_buy_5():
    path = Path("data/paper_open_ledger.json")
    assert path.is_file()
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["kind"] == LEDGER_KIND
    assert payload["ticket_id"] == "PAPER-20260903-02"
    assert payload["trading_mode"] == "LIVE_BLOCKED"
    assert payload["is_live"] is False
    assert abs(payload["account"]["cash"] - 829.279217) < 1e-4
    pos = payload["positions"][0]
    assert pos["symbol"] == "SHEL.L"
    assert pos["quantity"] == 5.0
    fill = payload["fills"][0]
    assert fill["symbol"] == "SHEL.L"
    assert fill["quantity"] == 5.0
    assert abs(fill["price"] - 34.127093) < 1e-6
    assert fill["is_live"] is False
    assert fill["id"]

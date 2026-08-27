from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
)
from varma.clock import now_london
from varma.controls.addendum_a import ADDENDUM_A_LIMITS
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_f import ALL_STAFF_SLUGS, TECH_SLUG, TRADER_SLUG, staff_display_for_slug
from varma.controls.addendum_i import (
    FIRM_CLOSED_REASON,
    PAPER_EXECUTION_CLOSED_REASON,
)
from varma.controls.engine import ControlEngine
from varma.db.engine import get_session_factory, init_db
from varma.db.models import (
    AllowListInstrument,
    ControlSetting,
    ControlState,
    Employee,
    NumericLimit,
    PaperFill,
    Permission,
)
from varma.db.seed import seed_if_empty
from varma.observability.board import BoardObservability
from varma.ports.llm import get_llm


EXPECTED_DISPLAY = {
    "ceo": "Jordan Hale · CEO",
    "market-intelligence-research": "Asha Patel · Research",
    "challenge": "Sam Okeke · Challenge",
    "risk": "Elena Voss · Risk",
    "trader": "Chris Adeyemi · Trader",
    "quant-strategy": "Nina Kapoor · Quant",
    "technology": "Owen Blake · Technology",
}


def test_default_seed_has_seven_named_employees_and_board_addenda(session):
    rows = {e.slug: e for e in session.query(Employee).all()}
    assert set(rows) == set(ALL_STAFF_SLUGS) == set(EXPECTED_DISPLAY)
    for slug, display in EXPECTED_DISPLAY.items():
        assert rows[slug].display_name == display
        assert rows[slug].display_name == staff_display_for_slug(slug)
    assert set(ControlEngine(session).allow_list_symbols()) == set(ADDENDUM_E_SYMBOLS)
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert session.get(ControlSetting, "paper_execution").value == "CLOSED"
    for key, value, _unit in ADDENDUM_A_LIMITS:
        assert session.get(NumericLimit, key).value == value
    trader = rows[TRADER_SLUG]
    place = (
        session.query(Permission)
        .filter_by(subject_id=trader.id, action="place_order")
        .one()
    )
    assert place.allowed is True
    ceo = rows["ceo"]
    assert (
        session.query(Permission)
        .filter_by(subject_id=ceo.id, action="place_order")
        .one()
        .allowed
        is False
    )
    assert (
        session.query(Permission)
        .filter_by(subject_id=ceo.id, action="write_controls")
        .one()
        .allowed
        is False
    )
    assert get_llm().provider_name == "fake"


def test_trader_may_propose_but_fill_is_paper_execution_closed(session):
    trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
    d = ControlEngine(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == PAPER_EXECUTION_CLOSED_REASON
    assert d.reason != "NO_PERMISSION"
    assert d.details["alias"] == FIRM_CLOSED_REASON
    assert d.details["firm_closed"] is True
    assert session.query(PaperFill).count() == 0
    live = ControlEngine(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
        at=SESSION_OPEN,
    )
    assert live.allowed is False
    assert live.reason == "LIVE_BLOCKED"


def test_stale_sqlite_is_reconciled_to_board_encoded(db_url):
    init_db(db_url, reset=True)
    factory = get_session_factory(db_url, reset=False)
    session = factory()
    try:
        session.add(
            ControlState(
                id=1,
                trading_mode="EVALUATION",
                kill_switch=False,
                updated_at=now_london(),
                updated_by="stale-sqlite",
            )
        )
        session.commit()
        assert session.query(Employee).count() == 0
        assert session.query(AllowListInstrument).count() == 0
        assert session.query(NumericLimit).count() == 0
        assert session.get(ControlSetting, "paper_execution") is None

        seed_if_empty(session)

        assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
        names = {e.slug: e.display_name for e in session.query(Employee).all()}
        assert names[TRADER_SLUG] == "Chris Adeyemi · Trader"
        assert set(names) == set(EXPECTED_DISPLAY)
        assert names == EXPECTED_DISPLAY
        assert set(r.symbol for r in session.query(AllowListInstrument).all()) == set(ADDENDUM_E_SYMBOLS)
        for key, value, _unit in ADDENDUM_A_LIMITS:
            assert session.get(NumericLimit, key).value == value
        assert session.get(ControlSetting, "paper_execution").value == "CLOSED"

        trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
        assert (
            session.query(Permission)
            .filter_by(subject_id=trader.id, action="place_order")
            .one()
            .allowed
            is True
        )
        d = ControlEngine(session).place_order(
            actor_id=trader.id,
            actor_type="employee",
            order={"symbol": "MSFT", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert d.reason == PAPER_EXECUTION_CLOSED_REASON
        assert d.reason != "NO_PERMISSION"
        assert session.query(PaperFill).count() == 0
        snap = BoardObservability(session).snapshot()
        assert snap["kill_switch"]["board_member_can_trigger"] is True
        assert snap["kill_switch"]["employees_cannot_reset"] is True
        assert snap["paper_gate"]["paper_execution"] == "CLOSED"
    finally:
        session.close()
        init_db("sqlite:///:memory:", reset=True)


def test_employees_still_cannot_write_locks_or_open_the_firm(client):
    for headers in (CEO_HEADERS, TRADER_HEADERS, TECH_HEADERS):
        for field, value in (
            ("trading_mode", "LIVE"),
            ("allow_list", list(ADDENDUM_E_SYMBOLS)),
            ("paper_execution", "OPEN"),
            ("open_firm", True),
        ):
            r = client.post(
                "/controls/write",
                headers=headers,
                json={"field": field, "value": value},
            )
            assert r.status_code == 403
    halt = client.post("/controls/kill-switch", headers=TRADER_HEADERS, json={"halt": True})
    assert halt.status_code == 401
    board_halt = client.post("/controls/kill-switch", headers=BOARD_HEADERS, json={"halt": True})
    assert board_halt.status_code == 200
    assert board_halt.json()["halted"] is True
    after = client.get("/controls").json()
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["paper_execution"] == "CLOSED"
    assert after["kill_switch"] is True
    reset = client.post("/controls/kill-switch/reset", headers=CEO_HEADERS)
    assert reset.status_code == 403
    board_reset = client.post("/controls/kill-switch/reset", headers=BOARD_HEADERS)
    assert board_reset.status_code == 200

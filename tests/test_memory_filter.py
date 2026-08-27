from tests.conftest import BOARD_HEADERS, EMPLOYEE_HEADERS
from varma.clock import describe_nightly_memory_filter
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ControlState,
    Employee,
    Evidence,
    MemoryEmployee,
    MemoryFilterRun,
    MemoryWorking,
    MemoryWorkingArchive,
    Permission,
)
from varma.db.seed import MI_SLUG
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG
from varma.memory.stores import MemoryStores
from varma.ports.execution import ExecutionPort
from varma.routines.run_brief import run_brief
from varma.routines.run_nightly_filter import run_nightly_filter


def test_working_context_archived_evidence_kept(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    stores = MemoryStores(session)
    stores.working_put(emp.id, "scratch", "overnight notes")
    stores.working_put(emp.id, "last_chat", "hello")
    prior_evidence = stores.append_evidence("unit_test_marker", emp.slug, '{"ok": true}')
    prior_id = prior_evidence.id
    evidence_ids_before = {r.id for r in session.query(Evidence).all()}
    lesson_ids_before = {r.id for r in session.query(MemoryEmployee).all()}
    working_before = session.query(MemoryWorking).count()
    assert working_before >= 2

    result = run_nightly_filter(session)

    assert result["archived_count"] >= 2
    assert result["working_remaining"] == 0
    assert session.query(MemoryWorking).count() == 0
    archived = session.query(MemoryWorkingArchive).filter_by(filter_run_id=result["id"]).all()
    keys = {a.key for a in archived}
    assert "scratch" in keys
    assert "last_chat" in keys
    assert session.get(Evidence, prior_id) is not None
    evidence_ids_after = {r.id for r in session.query(Evidence).all()}
    assert evidence_ids_before <= evidence_ids_after
    assert result["evidence_count_after"] == result["evidence_count_before"] + 1
    assert result["evidence_deleted"] is False
    assert {r.id for r in session.query(MemoryEmployee).all()} == lesson_ids_before
    assert session.query(Evidence).filter_by(kind="nightly_filter_ran").count() >= 1


def test_filter_cannot_write_controls(session):
    before_mode = session.get(ControlState, 1).trading_mode
    before_allow = [r.symbol for r in session.query(AllowListInstrument).all()]
    before_perms = [
        (p.subject_id, p.action, p.allowed)
        for p in session.query(Permission).order_by(Permission.subject_id, Permission.action)
    ]
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    MemoryStores(session).working_put(emp.id, "scratch", "x")

    result = run_nightly_filter(session)

    assert result["controls_written"] is False
    assert session.get(ControlState, 1).trading_mode == before_mode == "LIVE_BLOCKED"
    assert [r.symbol for r in session.query(AllowListInstrument).all()] == before_allow
    after_perms = [
        (p.subject_id, p.action, p.allowed)
        for p in session.query(Permission).order_by(Permission.subject_id, Permission.action)
    ]
    assert after_perms == before_perms
    assert LIVE_ADAPTER_LOADED is False
    assert ControlEngine(session).live_adapter_loaded() is False


def test_live_still_blocked_after_filter(session):
    run_brief(session)
    run_nightly_filter(session)
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    d = ExecutionPort(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "LIVE"},
    )
    assert d.allowed is False
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert ControlEngine(session).allow_list_symbols()


def test_evidence_is_append_only(session):
    stores = MemoryStores(session)
    row = stores.append_evidence("keep_me", "test", "{}")
    try:
        stores.delete_evidence(row.id)
        raise AssertionError("delete_evidence must refuse")
    except RuntimeError as exc:
        assert "APPEND_ONLY" in str(exc)
    try:
        stores.overwrite_evidence(row.id, "mutated")
        raise AssertionError("overwrite_evidence must refuse")
    except RuntimeError as exc:
        assert "APPEND_ONLY" in str(exc)
    assert session.get(Evidence, row.id).payload == "{}"


def test_employees_remain_after_filter(session):
    run_nightly_filter(session)
    slugs = {e.slug for e in session.query(Employee).all()}
    assert {MI_SLUG, CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG} <= slugs


def test_nightly_filter_api(client):
    schedule = client.get("/routines/nightly-filter-schedule").json()
    assert schedule["timezone"] == "Europe/London"
    assert schedule["schedule"] == "nightly"
    assert schedule["daemon"] is False
    assert schedule["writes_controls"] is False
    assert schedule["deletes_evidence"] is False
    assert "Europe/London" in describe_nightly_memory_filter()
    denied = client.post("/routines/run-nightly-filter")
    assert denied.status_code == 401
    employee = client.post("/routines/run-nightly-filter", headers=EMPLOYEE_HEADERS)
    assert employee.status_code == 401
    ok = client.post("/routines/run-nightly-filter", headers=BOARD_HEADERS)
    assert ok.status_code == 200
    body = ok.json()
    assert body["controls_written"] is False
    assert body["evidence_deleted"] is False
    assert body["daemon"] is False
    assert body["live_still_blocked"] is True
    latest = client.get("/memory/filter/latest").json()
    assert latest["run"]["id"] == body["id"]
    health = client.get("/health").json()
    assert health["trading_mode"] == "LIVE_BLOCKED"
    assert health["nightly_filter"]["daemon"] is False
    assert health["nightly_filter"]["timezone"] == "Europe/London"


def test_filter_run_stored_in_database(session):
    emp = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    MemoryStores(session).working_put(emp.id, "pack", "meeting notes")
    result = run_nightly_filter(session)
    row = session.get(MemoryFilterRun, result["id"])
    assert row is not None
    assert row.timezone == "Europe/London"
    assert row.cadence == "nightly"
    assert row.daemon is False
    assert row.controls_written is False
    assert row.trading_mode_after == "LIVE_BLOCKED"

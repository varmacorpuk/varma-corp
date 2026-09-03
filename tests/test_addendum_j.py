import json
import subprocess
from pathlib import Path

from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    QUANT_HEADERS,
    RISK_HEADERS,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
)
from varma.backup.crypto import decrypt_bytes, load_or_create_backup_key
from varma.backup.job import run_company_backup
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_i import (
    GRAND_OPENING_NOT_IMPLEMENTED_REASON,
    PAPER_EXECUTION_CLOSED_REASON,
)
from varma.controls.addendum_j import (
    ADDENDUM_J_LABEL,
    BACKUP_EXCLUDED,
    BACKUP_INCLUDED,
    BACKUP_OWNER_DISPLAY,
    BACKUP_OWNER_SLUG,
    BACKUP_ROUTINE_NAME,
    EMPLOYEE_CANNOT_DOWNLOAD_SECRETS_REASON,
    SECRETS_ARE_NOT_DOWNLOADABLE_REASON,
    live_broker_credentials_exist,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import (
    BackupRun,
    ControlState,
    Employee,
    PaperFill,
    PaperPosition,
    Permission,
    Routine,
)
from varma.observability.board import BoardObservability
from varma.paper.simulator import PaperFillSimulator
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.ports.llm import get_llm
from varma.db.seed import MI_SLUG

ROOT = Path(__file__).resolve().parents[1]
EMPLOYEE_SETS = (
    EMPLOYEE_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    RISK_HEADERS,
    TRADER_HEADERS,
    QUANT_HEADERS,
    TECH_HEADERS,
)
OPEN_FIELDS = (
    ("paper_execution", "OPEN"),
    ("grand_opening_paper", "yes"),
    ("grand_opening_live", "yes"),
    ("firm_open", True),
    ("open_firm", True),
    ("trading_mode", "LIVE"),
    ("allow_list", ["AAPL"]),
)


def _grant_place(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    return emp


def test_addendum_j_backup_status_before_run(session):
    snap = ControlEngine(session).snapshot()
    assert snap["addendum_j"]["label"] == ADDENDUM_J_LABEL
    assert snap["addendum_j"]["github_is_code_only"] is True
    assert snap["addendum_j"]["on_board_member_laptop"] is False
    assert snap["addendum_j"]["system_of_record"] == "database"
    assert snap["addendum_j"]["second_store_invented"] is False
    assert snap["addendum_j"]["owner_display_name"] == BACKUP_OWNER_DISPLAY
    assert snap["addendum_j"]["included"] == list(BACKUP_INCLUDED)
    assert snap["addendum_j"]["excluded"] == list(BACKUP_EXCLUDED)
    assert snap["addendum_j"]["encrypted_at_rest"] is True
    assert snap["addendum_j"]["daemon"] is False
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["paper_execution"] == "OPEN"
    obs = BoardObservability(session).snapshot()
    backup = obs["backup"]
    assert backup["last_successful_backup_at"] is None
    assert backup["last_failure_at"] is None
    assert backup["included"] == list(BACKUP_INCLUDED)
    assert backup["excluded"] == list(BACKUP_EXCLUDED)
    assert backup["ciphertext_shown"] is False
    assert backup["encryption_key_shown"] is False
    assert backup["get_observability_runs_backup"] is False
    assert live_broker_credentials_exist() is False
    tech = session.query(Employee).filter_by(slug=BACKUP_OWNER_SLUG).one()
    assert tech.display_name == "Owen Blake · Technology"
    routine = session.query(Routine).filter_by(name=BACKUP_ROUTINE_NAME).one()
    assert routine.employee_id == tech.id
    assert routine.schedule == "daily after US close / end of London evening"
    assert ":" not in routine.schedule.split("after")[0]
    assert get_llm().provider_name == "fake"


def test_paper_open_allow_listed_ticker_may_fill(session):
    emp = _grant_place(session)
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"
    assert session.query(PaperFill).count() == 1
    assert session.query(PaperPosition).count() == 1
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_live_denied_and_backup_does_not_fill(client):
    live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["allowed"] is False
    empty = client.get("/observability", headers=BOARD_HEADERS).json()
    assert empty["backup"]["last_successful_backup_at"] is None
    ran = client.post("/routines/run-backup", headers=BOARD_HEADERS)
    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "success"
    assert body["fills"] is False
    assert body["paper_fills"] is False
    assert body["live_fills"] is False
    assert body["paper_fill_count"] == 0
    assert body["paper_fills_unchanged"] is True
    assert body["job_safety"]["fills"] is False
    assert body["job_safety"]["paper_fills"] is False
    assert body["encrypted_at_rest"] is True
    assert body["git_committed"] is False
    assert body["on_board_member_laptop"] is False
    assert body["in_github"] is False
    assert body["secrets_included"] is False
    assert body["live_broker_credentials_exist"] is False
    assert body["owner_display_name"] == "Owen Blake · Technology"
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after["backup"]["last_successful_backup_at"] == body["ran_at"]
    assert after["backup"]["last_failure_at"] is None
    assert after["backup"].get("ciphertext") is None
    assert after["backup"]["ciphertext_shown"] is False
    assert after["backup"]["encryption_key_shown"] is False
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["paper_gate"]["paper_execution"] == "OPEN"
    paper = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert paper.status_code == 403
    assert paper.json()["detail"]["reason"] in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_backup_artefact_not_committed_to_git(session):
    before = subprocess.check_output(["git", "ls-files"], cwd=ROOT).decode().splitlines()
    result = run_company_backup(session, started_by="cli")
    after = subprocess.check_output(["git", "ls-files"], cwd=ROOT).decode().splitlines()
    assert after == before
    row = session.query(BackupRun).filter_by(id=result["id"]).one()
    assert row.status == "success"
    assert row.git_committed is False
    assert row.in_github is False
    assert row.on_board_member_laptop is False
    assert row.store == "database"
    assert row.ciphertext
    tracked = "\n".join(after)
    assert row.ciphertext not in tracked
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/" in gitignore
    assert "*.key" in gitignore
    assert "*.dump" in gitignore
    assert not list(ROOT.glob("*.dump"))
    assert not list(ROOT.glob("*.bak"))
    plaintext = decrypt_bytes(row.ciphertext, load_or_create_backup_key())
    payload = json.loads(plaintext.decode("utf-8"))
    assert payload["included"] == list(BACKUP_INCLUDED)
    assert "paper_ledger" in payload
    assert "evidence" in payload
    assert "organisational_memory" in payload
    assert "control_snapshots" in payload
    assert payload["secrets_included"] is False
    assert payload["live_broker_credentials_exist"] is False
    assert row.ciphertext != plaintext.decode("utf-8")


def test_employees_cannot_open_the_firm_or_download_secrets(client):
    for headers in EMPLOYEE_SETS:
        for field, value in OPEN_FIELDS:
            r = client.post(
                "/controls/write",
                headers=headers,
                json={"field": field, "value": value},
            )
            assert r.status_code == 403
            assert r.json()["detail"] in {
                "EMPLOYEE_CANNOT_WRITE_CONTROLS",
                GRAND_OPENING_NOT_IMPLEMENTED_REASON,
            }
        denied = client.post("/routines/run-backup", headers=headers)
        assert denied.status_code == 401
        secrets = client.get("/backup/secrets", headers=headers)
        assert secrets.status_code == 403
        assert secrets.json()["detail"] == EMPLOYEE_CANNOT_DOWNLOAD_SECRETS_REASON
        key = client.get("/backup/key", headers=headers)
        assert key.status_code == 403
        download = client.get("/backup/download", headers=headers)
        assert download.status_code == 403
    ceo_open = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "paper_execution", "value": "OPEN"},
    )
    assert ceo_open.status_code == 403
    assert ceo_open.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    ceo_secrets = client.get("/backup/secrets", headers=CEO_HEADERS)
    assert ceo_secrets.status_code == 403
    after = client.get("/controls").json()
    assert after["paper_execution"] == "OPEN"
    assert after["trading_mode"] == "LIVE_BLOCKED"


def test_technology_owns_backup_cannot_write_controls(client, session):
    tech = session.query(Employee).filter_by(slug="technology").one()
    assert tech.display_name == "Owen Blake · Technology"
    for action in (
        "place_order",
        "write_controls",
        "approve_live",
        "transition_to_live",
        "download_secrets",
        "open_firm",
    ):
        perm = (
            session.query(Permission)
            .filter_by(subject_id=tech.id, action=action)
            .one()
        )
        assert perm.allowed is False
    for field, value in (
        ("trading_mode", "PAPER"),
        ("trading_mode", "LIVE"),
        ("allow_list", ["AAPL"]),
        ("paper_execution", "OPEN"),
        ("open_firm", True),
    ):
        r = client.post(
            "/controls/write",
            headers=TECH_HEADERS,
            json={"field": field, "value": value},
        )
        assert r.status_code == 403
    run = client.post("/routines/run-backup", headers=TECH_HEADERS)
    assert run.status_code == 401
    board = client.get("/backup/secrets", headers=BOARD_HEADERS)
    assert board.status_code == 403
    assert board.json()["detail"] == SECRETS_ARE_NOT_DOWNLOADABLE_REASON
    sched = client.get("/routines/backup-schedule").json()
    assert sched["timezone"] == "Europe/London"
    assert sched["schedule"] == "daily after US close / end of London evening"
    assert sched["daemon"] is False
    assert sched["encrypted_at_rest"] is True
    assert sched["owner_display_name"] == "Owen Blake · Technology"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert set(ControlEngine(session).allow_list_symbols()) == set(ADDENDUM_E_SYMBOLS)


def test_last_failure_visible_and_does_not_fill(session, monkeypatch):
    def boom(_session):
        raise RuntimeError("TEST_BACKUP_FAILURE")

    monkeypatch.setattr("varma.backup.job._snapshot_payload", boom)
    result = run_company_backup(session, started_by="cli")
    assert result["status"] == "failure"
    assert result["failure_reason"] == "TEST_BACKUP_FAILURE"
    assert result["fills"] is False
    assert session.query(PaperFill).count() == 0
    obs = BoardObservability(session).snapshot()
    assert obs["backup"]["last_failure_reason"] == "TEST_BACKUP_FAILURE"
    assert obs["backup"]["last_successful_backup_at"] is None
    assert obs["backup"]["last_failure_at"] == result["ran_at"]
    assert obs["writes_controls"] is False
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"

from tests.conftest import BOARD_HEADERS
from varma.db.models import Employee, IntelligenceBrief
from varma.ports.data import FakeMarketData
from varma.routines.run_brief import run_brief
from varma.skills.prepare_daily_intelligence_brief import PrepareDailyIntelligenceBrief
from varma.verification.brief import REQUIRED_FIELDS, verify_brief


def test_run_brief_stores_verified_artefact_in_database(session):
    result = run_brief(session)
    assert result["verification_passed"] is True
    for field in (
        "headline",
        "summary",
        "items",
        "watchlist_snapshot",
        "freshness_flag",
        "produced_at",
        "employee_id",
        "cost_units",
    ):
        assert result.get(field) not in (None, "", [])
    assert result["no_execution_authority"] is True
    assert result["trading_mode_at_production"] == "LIVE_BLOCKED"
    assert result["freshness_flag"] in {"FRESH", "MIXED", "STALE"}
    row = session.get(IntelligenceBrief, result["id"])
    assert row is not None
    assert row.verification_passed is True
    for item in result["items"]:
        if item.get("material"):
            assert item.get("source")
            assert item.get("published_at")


def test_independent_verification_rejects_missing_source():
    artefact = {
        "headline": "x",
        "summary": "y",
        "items": [{"claim": "z", "source": "", "published_at": "", "material": True}],
        "watchlist_snapshot": [],
        "freshness_flag": "STALE",
        "produced_at": "2026-08-27T06:30:00+01:00",
        "as_of": "2026-08-27T06:30:00+01:00",
        "employee_id": "x",
        "skill_name": "prepare_daily_intelligence_brief",
        "skill_version": "0.1.0",
        "trading_mode_at_production": "LIVE_BLOCKED",
        "no_execution_authority": True,
        "cost_units": 1,
    }
    v = verify_brief(artefact, cost_cap=100)
    assert v["passed"] is False


def test_cost_cap_temporary(session):
    emp = session.query(Employee).filter_by(slug="market-intelligence-research").one()
    skill = PrepareDailyIntelligenceBrief(session)
    brief = skill.run(emp)
    assert brief.cost_units <= 100
    assert "TEMPORARY" in brief.freshness_notes


def test_stale_feed_flags_stale(session):
    emp = session.query(Employee).filter_by(slug="market-intelligence-research").one()
    skill = PrepareDailyIntelligenceBrief(session, data=FakeMarketData(stale=True))
    brief = skill.run(emp)
    assert brief.freshness_flag == "STALE"
    assert brief.verification_passed is True


def test_brief_via_api(client):
    r = client.post("/routines/run-brief", headers=BOARD_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["verification_passed"] is True
    latest = client.get("/employees/market-intelligence-research/brief/latest")
    assert latest.json()["brief"]["id"] == body["id"]


def test_required_fields_constant():
    assert "headline" in REQUIRED_FIELDS
    assert "items" in REQUIRED_FIELDS

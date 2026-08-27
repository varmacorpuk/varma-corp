from varma.clock import describe_0630_weekday_routine
from varma.db.models import Employee, Routine, Skill
from varma.db.seed import MI_SLUG
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG


def test_persistent_market_intelligence_employee(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    assert emp.display_name == "Research"
    assert emp.person_name == "Asha Patel"
    assert emp.slug == MI_SLUG
    assert "Market Intelligence" in emp.role_title
    assert emp.is_primary_agent == 1
    skill = session.query(Skill).filter_by(employee_id=emp.id).one()
    assert skill.name == "prepare_daily_intelligence_brief"
    assert skill.active is True
    routine = session.query(Routine).filter_by(employee_id=emp.id).one()
    assert "06:30" in routine.schedule
    assert routine.timezone == "Europe/London"
    assert "06:30" in describe_0630_weekday_routine()


def test_employee_list(client):
    r = client.get("/employees")
    assert r.status_code == 200
    slugs = [e["slug"] for e in r.json()]
    assert MI_SLUG in slugs
    assert CEO_SLUG in slugs
    assert CHALLENGE_SLUG in slugs
    assert RISK_SLUG in slugs
    by_slug = {e["slug"]: e for e in r.json()}
    assert by_slug[MI_SLUG]["display_name"] == "Research"
    assert by_slug[MI_SLUG]["display_name"] != "Asha Patel"
    assert by_slug[MI_SLUG]["person_name"] == "Asha Patel"
    assert by_slug[CEO_SLUG]["display_name"] == "CEO"
    assert by_slug[CHALLENGE_SLUG]["display_name"] == "Challenge"
    assert by_slug[RISK_SLUG]["display_name"] == "Risk"


def test_office_doors_are_research_ceo_challenge_risk(client):
    from tests.conftest import BOARD_HEADERS

    state = client.get("/office/state").json()
    doors = {e["slug"]: e["display_name"] for e in state["employees"]}
    assert doors[MI_SLUG] == "Research"
    assert set(doors.values()) == {"Research", "CEO", "Challenge", "Risk"}
    assert "Asha Patel" not in doors.values()
    assert state["talk_enabled"] is False
    assert client.get("/controls").json()["allow_list"] == []
    obs = client.get("/observability", headers=BOARD_HEADERS).json()
    bubble_names = {row["slug"]: row["display_name"] for row in obs["status_bubbles"]}
    assert bubble_names[MI_SLUG] == "Research"
    denied = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["reason"] == "EMPTY_ALLOW_LIST"
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"

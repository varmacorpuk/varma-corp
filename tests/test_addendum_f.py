from tests.conftest import BOARD_HEADERS, QUANT_HEADERS, TECH_HEADERS, TRADER_HEADERS
from varma.controls.addendum_f import (
    QUANT_SLUG,
    STAFF_PEOPLE,
    TECH_SLUG,
    TRADER_SLUG,
    format_staff_display,
    staff_display_for_slug,
)
from varma.controls.engine import ControlEngine
from varma.db.models import Employee, Permission
from varma.db.seed import MI_SLUG
from varma.employees.runtime import NO_LIVE_APPROVAL_SLUGS
from varma.meetings.company_meeting import ATTENDEE_SLUGS
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG


def test_display_name_is_person_dot_department(session):
    rows = {e.slug: e for e in session.query(Employee).all()}
    assert set(rows) == set(STAFF_PEOPLE)
    for slug, (person, department) in STAFF_PEOPLE.items():
        emp = rows[slug]
        assert emp.person_name == person
        assert emp.department == department
        assert emp.display_name == format_staff_display(person, department)
        assert emp.display_name != department
        assert " · " in emp.display_name
    assert rows[MI_SLUG].display_name == "Asha Patel · Research"
    assert rows[CEO_SLUG].display_name == "Jordan Hale · CEO"
    assert rows[CHALLENGE_SLUG].display_name == "Sam Okeke · Challenge"
    assert rows[RISK_SLUG].display_name == "Elena Voss · Risk"
    assert rows[TRADER_SLUG].display_name == "Chris Adeyemi · Trader"
    assert rows[QUANT_SLUG].display_name == "Nina Kapoor · Quant"
    assert rows[TECH_SLUG].display_name == "Owen Blake · Technology"


def test_office_and_observability_use_person_department(client):
    state = client.get("/office/state").json()
    names = {e["slug"]: e["display_name"] for e in state["employees"]}
    assert names[MI_SLUG] == "Asha Patel · Research"
    assert names[CEO_SLUG] == "Jordan Hale · CEO"
    assert "Research" not in names.values()
    assert "CEO" not in names.values()
    obs = client.get("/observability", headers=BOARD_HEADERS).json()
    bubbles = {row["slug"]: row["display_name"] for row in obs["status_bubbles"]}
    assert bubbles[RISK_SLUG] == "Elena Voss · Risk"
    assert bubbles[TRADER_SLUG] == "Chris Adeyemi · Trader"
    assert len(obs["status_bubbles"]) == 7


def test_new_three_exist_and_cannot_write_or_approve_live(session, client):
    assert session.query(Employee).count() == 7
    for slug, headers in (
        (TRADER_SLUG, TRADER_HEADERS),
        (QUANT_SLUG, QUANT_HEADERS),
        (TECH_SLUG, TECH_HEADERS),
    ):
        emp = session.query(Employee).filter_by(slug=slug).one()
        assert emp.display_name == staff_display_for_slug(slug)
        assert slug in NO_LIVE_APPROVAL_SLUGS
        for action in ("place_order", "write_controls", "approve_live", "transition_to_live"):
            perm = (
                session.query(Permission)
                .filter_by(subject_id=emp.id, action=action)
                .one()
            )
            if slug == TRADER_SLUG and action == "place_order":
                assert perm.allowed is True
            else:
                assert perm.allowed is False
        denied = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "trading_mode", "value": "LIVE"},
        )
        assert denied.status_code == 403
        assert denied.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
        pub = client.get(f"/employees/{slug}").json()
        assert pub["cannot_approve_live_trading"] is True
        assert pub["display_name"] == emp.display_name


def test_challenge_independent_of_quant_risk_independent_of_trader(session):
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    quant = session.query(Employee).filter_by(slug=QUANT_SLUG).one()
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
    assert challenge.id != quant.id
    assert risk.id != trader.id
    assert "independent of Quant" in (quant.authority_boundaries or "")
    assert "independent of Trader" in (trader.authority_boundaries or "")
    assert ATTENDEE_SLUGS == (MI_SLUG, CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG)
    assert TRADER_SLUG not in ATTENDEE_SLUGS
    assert QUANT_SLUG not in ATTENDEE_SLUGS
    d = ControlEngine(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "LIVE", "quantity": 1},
    )
    assert d.allowed is False
    assert d.reason == "LIVE_BLOCKED"

from varma.clock import describe_0630_weekday_routine
from varma.db.models import Employee, Routine, Skill
from varma.db.seed import MI_SLUG


def test_persistent_market_intelligence_employee(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    assert emp.display_name
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

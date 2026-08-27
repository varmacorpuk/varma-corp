"""Skill prepare_daily_intelligence_brief (Document 18 first vertical slice)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.config import get_settings
from varma.controls.engine import ControlEngine
from varma.cost.ledger import CostLedger, TEMPORARY_BRIEF_COST_CAP_LABEL
from varma.db.models import Employee, IntelligenceBrief, WatchlistItem
from varma.memory.stores import MemoryStores
from varma.ports.data import DataPort, FakeMarketData
from varma.ports.llm import LLMPort, get_llm
from varma.verification.brief import expected_freshness, verify_brief

SKILL_NAME = "prepare_daily_intelligence_brief"
SKILL_VERSION = "0.1.0"


class PrepareDailyIntelligenceBrief:
    def __init__(
        self,
        session: Session,
        *,
        llm: LLMPort | None = None,
        data: DataPort | None = None,
    ) -> None:
        self.session = session
        self.llm = llm or get_llm()
        self.data = data or FakeMarketData()
        self.memory = MemoryStores(session)
        self.cost = CostLedger(session)
        self.controls = ControlEngine(session)

    def run(self, employee: Employee) -> IntelligenceBrief:
        settings = get_settings()
        now = now_london()
        watch = self.session.query(WatchlistItem).all()
        symbols = [w.symbol for w in watch]
        news = self.data.news(symbols)
        prices = self.data.delayed_prices(symbols)
        lessons = [m.content for m in self.memory.employee_lessons(employee.id)]
        state = self.controls.snapshot()

        context = {
            "employee": {
                "id": employee.id,
                "display_name": employee.display_name,
                "role_title": employee.role_title,
                "department": employee.department,
                "authority_boundaries": employee.authority_boundaries,
            },
            "lessons": lessons,
            "news": news,
            "prices": prices,
            "watchlist_label": "TEMPORARY DEVELOPMENT DEFAULT — NOT the execution allow-list",
            "controls": state,
        }
        raw = self.llm.complete(task=SKILL_NAME, context=context)
        llm_units = int(raw.get("cost_units") or 2)
        data_units = 2
        total_cost = llm_units + data_units
        items = raw.get("items") or []
        freshness = expected_freshness(items, prices)
        artefact = {
            "headline": raw.get("headline") or "Daily intelligence brief",
            "summary": raw.get("summary") or "",
            "items": items,
            "watchlist_snapshot": prices,
            "freshness_flag": freshness,
            "produced_at": now,
            "as_of": now,
            "employee_id": employee.id,
            "skill_name": SKILL_NAME,
            "skill_version": SKILL_VERSION,
            "trading_mode_at_production": state["trading_mode"],
            "no_execution_authority": True,
            "cost_units": total_cost,
        }
        verdict = verify_brief(artefact, cost_cap=settings.temporary_brief_cost_cap_units)

        brief = IntelligenceBrief(
            employee_id=employee.id,
            produced_at=now,
            as_of=now,
            timezone="Europe/London",
            headline=str(artefact["headline"])[:240],
            summary=str(artefact["summary"]),
            items_json=json.dumps(items, default=str),
            watchlist_snapshot_json=json.dumps(prices, default=str),
            freshness_flag=freshness,
            freshness_notes=(
                f"TEMPORARY freshness windows: news {settings.temporary_news_fresh_hours}h, "
                f"prices {settings.temporary_price_fresh_hours}h. Not Board-approved thresholds."
            ),
            intended_recipient="company_meeting",
            trading_mode_at_production=state["trading_mode"],
            skill_name=SKILL_NAME,
            skill_version=SKILL_VERSION,
            cost_units=total_cost,
            verification_passed=bool(verdict["passed"]),
            verification_notes="; ".join(verdict["notes"]),
            no_execution_authority=True,
        )
        self.session.add(brief)
        self.session.commit()

        self.cost.record(
            employee_id=employee.id,
            workflow=SKILL_NAME,
            kind="llm",
            units=llm_units,
            note=TEMPORARY_BRIEF_COST_CAP_LABEL,
        )
        self.cost.record(
            employee_id=employee.id,
            workflow=SKILL_NAME,
            kind="data",
            units=data_units,
            note="TEMPORARY fake data units",
        )
        self.memory.append_evidence(
            "brief_produced",
            employee.slug,
            json.dumps(
                {
                    "brief_id": brief.id,
                    "verification_passed": brief.verification_passed,
                    "freshness_flag": brief.freshness_flag,
                    "cost_units": total_cost,
                }
            ),
        )
        self.memory.working_put(employee.id, "last_brief_id", brief.id)
        employee.status = "PREPARING" if not brief.verification_passed else "AVAILABLE"
        employee.status_bubble = "BRIEF READY" if brief.verification_passed else "BRIEF FAILED"
        self.session.commit()
        return brief

    def to_dict(self, brief: IntelligenceBrief) -> dict[str, Any]:
        return brief_to_dict(brief)


def brief_to_dict(brief: IntelligenceBrief) -> dict[str, Any]:
    return {
        "id": brief.id,
        "employee_id": brief.employee_id,
        "produced_at": brief.produced_at.isoformat() if brief.produced_at else None,
        "as_of": brief.as_of.isoformat() if brief.as_of else None,
        "timezone": brief.timezone,
        "headline": brief.headline,
        "summary": brief.summary,
        "items": json.loads(brief.items_json),
        "watchlist_snapshot": json.loads(brief.watchlist_snapshot_json),
        "freshness_flag": brief.freshness_flag,
        "freshness_notes": brief.freshness_notes,
        "intended_recipient": brief.intended_recipient,
        "trading_mode_at_production": brief.trading_mode_at_production,
        "skill_name": brief.skill_name,
        "skill_version": brief.skill_version,
        "cost_units": brief.cost_units,
        "verification_passed": brief.verification_passed,
        "verification_notes": brief.verification_notes,
        "no_execution_authority": brief.no_execution_authority,
        "watchlist_disclaimer": (
            "Watchlist is a TEMPORARY DEVELOPMENT DEFAULT. It is NOT the execution allow-list. "
            "Gold is FUTURE SCOPE ONLY and is not present."
        ),
    }

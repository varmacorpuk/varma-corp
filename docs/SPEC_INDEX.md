# Varma Corp — Specification Index

Navigation aid only. The authoritative specifications are **Documents 00–18**, which live
**outside this Git repository** (per `ARCHITECTURE.md`, on the dev box at
`/workspace/varma-corp-specs/authoritative/`). This file does **not** copy or replace them and is
**not** a competing specification. It maps each document/addendum to the code and tests that
implement it, so an agent can open the one relevant area instead of re-reading the whole spec.

If this index disagrees with the code, the code (and the authoritative documents) win; correct
the index.

## Documents 00–18 → implementation areas

| Doc | Subject | Primary implementation | Related tests |
| --- | --- | --- | --- |
| 00 | Master roadmap | `README.md`, `ARCHITECTURE.md` | — |
| 01 | Vision | `README.md` | — |
| 02 | Trading org / operating model | `varma/db/seed.py`, `varma/employees/` | `tests/test_employee.py`, `test_seed_reconcile.py` |
| 03 | AI employee architecture | `varma/employees/brain.py`, `db/models.py` (Employee, EmployeeFoundation, EmployeeRelationship, Skill, SkillInvocation) | `tests/test_brains_and_people.py`, `test_employee.py` |
| 04 | Trading strategy / approach | `varma/controls/` (allow-list, limits) | `tests/test_addendum_e.py`, `test_watchlist.py` |
| 05 | Trading workflow / decision | `varma/skills/`, `varma/meetings/handoff.py` | `tests/test_challenge_risk.py` |
| 06 | Strategy / market universe | `varma/controls/addendum_e.py`, `db/seed.py` (watchlist) | `tests/test_watchlist.py`, `test_addendum_e.py` |
| 07 | Trade lifecycle / decisions | `varma/controls/engine.py`, `varma/paper/`, `varma/skills/propose_paper_ticket.py` | `tests/test_execution.py`, `test_paper_simulator.py`, `test_paper_trade_path.py` |
| 08 | Employee behaviour / memory / learning | `varma/memory/stores.py`, `varma/memory/filter.py` | `tests/test_memory_filter.py`, `test_brains_and_people.py` |
| 09 | Meetings / communication / office | `varma/meetings/`, `desktop/` | `tests/test_company_meeting.py`, `test_office_layout.py`, `test_chat.py` |
| 10 | CEO / management / governance | `varma/skills/`, `db/seed.py` (ceo) | `tests/test_ceo.py` |
| 11 | Risk / compliance / controls / approval | `varma/controls/engine.py`, `risk.py`, `kill_switch.py` | `tests/test_controls.py`, `test_kill_switch.py`, `test_challenge_risk.py` |
| 12 | Paper trading / evaluation / live transition | `varma/paper/`, `varma/controls/addendum_i.py`, `varma/routines/run_paper_trade_path.py` | `tests/test_paper_simulator.py`, `test_addendum_i.py`, `test_paper_trade_path.py` |
| 13 | Technology / IT / self-maintenance | `varma/backup/`, `varma/controls/addendum_j.py` | `tests/test_addendum_j.py` |
| 14 | MVP technical architecture | `varma/kernel/app.py`, `varma/db/engine.py` | `tests/test_health.py` |
| 15 | Data / market intelligence / tools | `varma/ports/data.py`, `varma/verification/brief.py` | `tests/test_brief.py` |
| 16 | Virtual office / UX | `desktop/`, `varma/kernel/app.py` (`/office/state`) | `tests/test_office_layout.py` |
| 17 | Resource / cost / sustainability | `varma/cost/ledger.py`, `varma/observability/ai_usage.py` | `tests/test_ai_usage.py` |
| 18 | Final build package | whole `varma/` slice | full suite |

## Board Addenda → implementation

| Addendum | Subject | Module | Tests |
| --- | --- | --- | --- |
| A (2026-08-27) | Numeric paper limits (Board-set) | `varma/controls/addendum_a.py` | `tests/test_addendum_a.py` |
| C (2026-08-27) | Paper session / flatten-before-US-close | `varma/controls/addendum_c.py`, `varma/paper/flatten.py` | `tests/test_addendum_c.py` |
| E (2026-08-27) | PAPER execution allow-list | `varma/controls/addendum_e.py` | `tests/test_addendum_e.py` |
| F (2026-08-27) | Named staff (person · department) | `varma/controls/addendum_f.py`, `db/seed.py` | `tests/test_addendum_f.py` |
| I (2026-08-27) | Company CLOSED until Grand Opening | `varma/controls/addendum_i.py` | `tests/test_addendum_i.py` |
| J (2026-08-27) | Encrypted company backup | `varma/controls/addendum_j.py`, `varma/backup/` | `tests/test_addendum_j.py` |
| K (2026-09-03) | After London cash close, deny SHEL.L/AZN.L/ULVR.L only | `varma/controls/addendum_k.py`, `lse_session.py` | `tests/test_addendum_k.py`, `test_lse_session.py` |

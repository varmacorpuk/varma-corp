# Varma Corp — Glossary

Concise, shared vocabulary for coding agents and reviewers. Uses existing terminology only; this
file does not invent governance terms. Where a term maps to code, the code is authoritative.

- **Board Member** — the human authority (Hari). Approves LIVE/Grand Opening. Not an employee. Not
  "MD". Runs Board-only jobs and the kill switch. Actor type `board_member` (`varma/kernel/auth.py`).
- **AI CEO** — Jordan Hale · CEO, an AI employee. Holds the meeting pack. Cannot approve LIVE, place
  orders, or write controls. Slug `ceo`.
- **Employee** — a durable database identity (Document 03), not an LLM prompt. An LLM call is an
  *invocation* of that person. Seven employees; slugs in `varma/controls/addendum_f.py`.
- **Market Intelligence / Research** — Asha Patel · Research (slug `market-intelligence-research`).
  Produces the pre-07:30 intelligence brief.
- **Challenge** — Sam Okeke · Challenge (`challenge`). Stress-tests SAMPLE theses; independent of Quant.
- **Risk** — Elena Voss · Risk (`risk`). Deny-path reviews; independent of Trader; cannot approve LIVE.
- **Trader / Quant / Technology** — `trader`, `quant-strategy`, `technology`. Paper desk / analysis /
  backup owner. None can write controls or open the firm.
- **FakeLLM** — deterministic, offline stand-in for a language model (`varma/ports/llm.py`). Default
  provider. No network, no paid API. Returns fixed structured output per task string.
- **LLM task strings** — `prepare_daily_intelligence_brief`, `challenge_sample_thesis`,
  `review_unsafe_path`, `chat`. Stable identifiers; do not rename.
- **Control engine** — deterministic permit/deny authority (`varma/controls/engine.py`). AI never
  enforces controls. Employees cannot write control tables.
- **trading_mode = LIVE_BLOCKED** — live trading is off; the live adapter is not loaded.
- **PAPER execution CLOSED** — Board Addendum I: the firm is closed until Grand Opening; the internal
  simulator denies all fills, even for allow-listed tickers. The first paper-trade PATH exists
  (Trader proposal → ControlEngine → simulator) and is still gated CLOSED.
- **Allow-list (Addendum E)** — PAPER execution membership. Exists but cannot fill until open. Empty
  allow-list denies. Gold is never authorised. After London cash close, Addendum K denies the three
  LSE names (`SHEL.L`, `AZN.L`, `ULVR.L`) only; US names are not denied by K.
- **Addendum K** — Board record 2026-09-03 (Hari explicit yes). After London cash shuts, deny paper
  orders in the three LSE names only. Flatten remains US regular cash close (Addendum C not rewritten).
  PAPER stays CLOSED. Letter exists outside the repo. Chat is not the record.
- **Paper trading** — internal fill *simulator* only (`varma/paper/`). Not a broker. £1000 is a
  FUTURE starting book only. Board job: `run_paper_trade_path`.
- **BROKER_PAPER / LIVE ports** — external execution ports; remain UNLOADED. No broker fills.
- **Kill switch** — Board-only halt/reset (`varma/controls/kill_switch.py`). Employees cannot reset it.
- **Handoff** — a durable database artefact passing work between employees (`varma/meetings/handoff.py`),
  e.g. brief → CEO, challenge → Risk. Communication is via handoffs, not chatty AI-to-AI calls.
- **Memory stores (Document 08)** — four stores in `varma/memory/stores.py`: working context,
  employee persistent lessons, organisational knowledge (governed promotion), append-only evidence.
- **Nightly filter** — on-demand Europe/London job that archives working context; never deletes
  evidence or writes controls (`varma/memory/filter.py`).
- **Observability** — read-only Board projection of the database (`varma/observability/board.py`).
  `GET /observability` runs no jobs and writes nothing.
- **Grand Opening** — the Board-gated transition to PAPER (then, much later, LIVE). Not performed.
  The paper-trade path is wired; flipping the existing CLOSED gate is the remaining human step
  for practice fills. Silence is not approval.
- **AICallLog** — non-invasive AI-usage measurement record (PR #1, `varma/observability/ai_usage.py`).
  Records deterministic call metadata and estimates; does not change AI behaviour.

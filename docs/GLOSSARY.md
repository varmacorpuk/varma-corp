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
- **PAPER execution OPEN** — Grand Opening PAPER (Hari explicit yes, 3 Sep 2026, word: Open).
  Practice / paper only on the £1000 book. Internal simulator may fill a legal allow-list order
  when in session and within Addendum A limits. Addendum I still exists as the two-opening rule;
  live opening has not happened. The CLOSED gate remains (`PAPER_EXECUTION_CLOSED`) if the Board
  closes paper again.
- **Allow-list (Addendum E)** — PAPER execution membership. After Grand Opening PAPER these names
  may fill in the simulator (subject to session, limits, kill switch, Addendum K). Listing venues:
  US tech (`AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`) NASDAQ; `JPM` and `JNJ` NYSE; `SHEL.L`,
  `AZN.L`, `ULVR.L` LSE. Empty allow-list denies. Gold is never authorised. After London cash
  close, Addendum K denies the three LSE names only; US names are not denied by K.
- **02F / venue-split flatten** — CEO desk rule bound in `ControlEngine`. `SHEL.L`, `AZN.L`,
  `ULVR.L` flatten in the London closing auction 16:30–16:35 Europe/London; that exit cannot be
  dropped independently of the opening buy. US names flatten at US regular cash close. Firm day
  still runs to NY close. `split_flatten_clocks` is true. Readable from engine snapshot as `risk_02f`.
- **Addendum K** — Board record 2026-09-03 (Hari explicit yes). After London cash shuts, deny paper
  orders in the three LSE names only. Letter exists outside the repo. Chat is not the record.
- **Paper trading** — internal fill *simulator* only (`varma/paper/`). Not a broker. £1000 is the
  paper starting book. Board job: `run_paper_trade_path`.
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
- **Grand Opening** — two openings, both Board-gated. PAPER happened (3 Sep 2026). LIVE later only
  if Hari says so after paper evidence. Silence is not approval. Never auto-switch.
- **AICallLog** — non-invasive AI-usage measurement record (PR #1, `varma/observability/ai_usage.py`).
  Records deterministic call metadata and estimates; does not change AI behaviour.

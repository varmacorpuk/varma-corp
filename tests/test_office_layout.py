from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "desktop" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "desktop" / "src" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "desktop" / "src" / "office.js").read_text(encoding="utf-8")
FLOOR = (ROOT / "desktop" / "src" / "office-floor.js").read_text(encoding="utf-8")
APP = (ROOT / "varma" / "kernel" / "app.py").read_text(encoding="utf-8")

SITCOM = ("Michael", "Jim", "Pam", "Dwight", "Angela", "Kevin", "Oscar", "Stanley")


def test_right_hand_panel_not_overlay():
    assert 'id="office-floor"' in HTML
    assert 'id="right-panel"' in HTML
    assert 'id="chat-form"' in HTML
    assert 'id="board-observability-btn"' in HTML
    assert "Talk" not in HTML or "talk-disabled" in HTML
    assert "overlay" not in CSS.lower() or "not an overlay" in CSS.lower()
    assert "position: fixed" not in CSS.lower()
    assert "display: flex" in CSS or "display:flex" in CSS.replace(" ", "")
    assert "#right-panel" in CSS
    assert "Board Member" in HTML
    assert "Board observability" in HTML
    assert "covering overlay" in HTML.lower() or "no covering overlay" in HTML.lower()
    assert "#chat-form[hidden]" in CSS
    assert "display: none" in CSS


def test_office_click_opens_panel_logic():
    assert "right-panel" in JS
    assert "status" in JS.lower() or "bubble" in JS.lower()
    assert "ceo" in JS
    assert "challenge" in JS
    assert "risk" in JS
    assert "market-intelligence-research" in JS
    assert "Ask the CEO" in JS or "ceo" in JS
    assert "right-panel" in HTML
    assert "covering overlay" in HTML.lower() or "no covering overlay" in HTML.lower()
    assert "showBoardObservability" in JS
    assert "/observability" in JS
    assert "board-observability-btn" in JS
    assert "writes controls" in JS.lower() or "does not write controls" in JS.lower()
    assert "chatForm.hidden = true" in JS.replace(" ", "") or "chatForm.hidden=true" in JS.replace(" ", "")
    assert "nightly" in JS.lower()
    assert "07:30" in JS
    assert "meeting artefacts" in JS.lower() or "meeting_artefacts" in JS
    assert "Documented routines" in JS
    assert "06:30 weekday brief" in JS
    assert "invented clock hour" in JS
    assert "organisation memory" in JS.lower() or "organisation_memory" in JS
    assert "status_bubbles" in JS or "status bubbles" in JS.lower()
    assert "data-employee-slug" in JS
    assert "/employees/" in JS and "/chat" in JS
    assert "Chat history" in JS or "chat history" in JS.lower()
    assert "Missing numeric limits" in JS
    assert "OPEN BOARD DECISION" in JS
    assert "Control snapshot" in JS
    assert "employees cannot write controls" in JS.lower()
    assert "unset_keys" in JS
    assert "allow_list" in JS
    assert "Paper gate" in JS
    assert "not started" in JS
    assert "paper_status" in JS
    assert "Board Addendum A" in JS
    assert "Halt paper" in JS
    assert "data-kill-action" in JS
    assert "runKillSwitch" in JS
    assert "Evaluation ledger" in JS
    assert "Paper ledger" in JS
    assert "open_positions" in JS
    assert "fill_rows" in JS
    assert "kill-halt" in CSS
    assert "Execution ports" in JS
    assert "BROKER_PAPER" in JS
    assert "UNLOADED" in JS
    assert "execution_ports" in JS
    assert "07:30 company meeting record" in JS
    assert "company_meeting" in JS
    assert "cannot start LIVE" in JS
    assert "Attendance" in JS
    assert "not a 12-employee roster" in JS
    assert "attendees" in JS
    assert "#chat-form[hidden]" in CSS
    assert "On-demand jobs" in JS
    assert "data-job-path" in JS
    assert "/routines/run-brief" in JS
    assert "/routines/run-challenge" in JS
    assert "/routines/run-risk-deny" in JS
    assert "/routines/run-0730-meeting" in JS
    assert "/routines/run-nightly-filter" in JS
    assert "/routines/run-flatten-us-close" in JS
    assert "/routines/run-flatten-london-close" in JS
    assert "/routines/run-backup" in JS
    assert "/routines/run-paper-trade-path" in JS
    assert "US_REGULAR_CASH_CLOSE" in JS or "US cash close" in JS
    assert "LONDON_CLOSING_AUCTION" in JS or "London closing auction" in JS
    assert "split_flatten_clocks" in JS
    assert "02F bound" in JS
    assert "GET /observability does not flatten" in JS
    assert "Run Trader paper-ticket proposal" in JS
    assert "first paper-trade PATH exists" in JS
    assert "PAPER_EXECUTION_CLOSED" in JS
    assert "Board Addendum J" in JS
    assert "Run company backup now" in JS
    assert "last successful backup" in JS.lower()
    assert "Owen Blake · Technology" in JS
    assert "Board Addendum C" in JS
    assert "US_REGULAR_CASH_CLOSE" in JS or "US cash close" in JS
    assert "LONDON_CLOSING_AUCTION" in JS or "London closing auction" in JS
    assert "GET /observability does not flatten" in JS
    assert "runBoardJob" in JS
    assert 'method: "POST"' in JS or "method: \"POST\"" in JS or 'method: "POST"' in JS.replace(" ", "")
    assert "showBoardObservability" in JS
    assert "GET /observability does not run jobs" in JS
    assert "Ask Asha Patel · Research" in JS
    assert 'display_name: "Asha Patel · Research"' in JS
    assert 'display_name: "Jordan Hale · CEO"' in JS
    assert 'display_name: "Sam Okeke · Challenge"' in JS
    assert 'display_name: "Elena Voss · Risk"' in JS
    assert 'display_name: "Chris Adeyemi · Trader"' in JS
    assert 'display_name: "Nina Kapoor · Quant"' in JS
    assert 'display_name: "Owen Blake · Technology"' in JS
    assert 'display_name: "Research"' not in JS
    assert "Select Asha Patel · Research" in HTML
    assert "Select Research, the CEO" not in HTML
    assert "talk-disabled" in HTML
    assert "Approve LIVE" not in HTML
    assert 'id="approve-live"' not in HTML.lower()
    assert "approve-live-btn" not in JS
    assert "job-runs" in CSS
    assert "Board Addendum I" in JS
    assert "two-opening rule" in JS
    assert "Board Addendum K" in JS
    assert "LSE after London cash close" in JS
    assert "no Board Member diary invite" in JS
    assert "Talk is disabled" in JS or "talk-disabled" in HTML


def test_pixel_office_is_not_four_desk_placeholder():
    assert 'id="staff-bar"' in HTML
    assert "office-floor.js" in HTML
    assert "placeholder pixels" not in HTML.lower()
    assert "conference table" in HTML.lower() or "conferenceTable" in FLOOR
    assert "poolTable" in FLOOR
    assert "plant(" in FLOOR
    assert "pixel-art-2d" in APP
    assert "placeholder-pixel-2d" not in APP
    assert "VarmaOfficeFloor" in JS
    assert "SEATS" in FLOOR
    assert "PATHS" in FLOOR
    assert "cubicle(" in FLOOR
    assert "redCabinet" in FLOOR
    assert "isWood" in FLOOR
    assert "walkPos" in FLOOR
    assert "drawPortrait" in FLOOR
    assert "drawBubble" in FLOOR
    assert "game-frame" in HTML
    assert "game-frame" in CSS
    assert "#f4b486" in CSS.lower() or "#F4B486" in CSS
    assert "Click on a character to see chat history." in HTML
    assert 'id="board-observability-btn"' in HTML
    assert 'data-employee-slug="board"' not in HTML
    assert "staff-portrait" in HTML
    assert "paintPortraits" in JS
    assert "Press Start 2P" in CSS or "Press Start 2P" in HTML
    for slug in (
        "ceo",
        "market-intelligence-research",
        "challenge",
        "risk",
        "trader",
        "quant-strategy",
        "technology",
    ):
        assert f'data-employee-slug="{slug}"' in HTML
        assert f"{slug}:" in FLOOR or f'"{slug}"' in FLOOR
    rows = [
        line.strip().strip('",')
        for line in FLOOR.splitlines()
        if line.strip().startswith('"') and line.strip().endswith('",')
    ]
    map_rows = [row for row in rows if set(row) <= set("#.")]
    assert len(map_rows) == 20
    assert all(len(row) == 32 for row in map_rows)
    assert "#" in "".join(map_rows)
    assert "." in "".join(map_rows)


def test_office_uses_varma_staff_not_sitcom_names():
    blob = HTML + CSS + JS + FLOOR
    for name in SITCOM:
        assert name not in blob
    for label in (
        "Jordan Hale · CEO",
        "Asha Patel · Research",
        "Sam Okeke · Challenge",
        "Elena Voss · Risk",
        "Chris Adeyemi · Trader",
        "Nina Kapoor · Quant",
        "Owen Blake · Technology",
    ):
        assert label in HTML
        assert label in JS

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "desktop" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "desktop" / "src" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "desktop" / "src" / "office.js").read_text(encoding="utf-8")
FLOOR = (ROOT / "desktop" / "src" / "office-floor.js").read_text(encoding="utf-8")
JOBS_JS = (ROOT / "desktop" / "src" / "staff-jobs.js").read_text(encoding="utf-8")
JOBS_JSON = json.loads((ROOT / "desktop" / "staff-jobs.json").read_text(encoding="utf-8"))
APP = (ROOT / "varma" / "kernel" / "app.py").read_text(encoding="utf-8")

SITCOM = ("Michael", "Jim", "Pam", "Dwight", "Angela", "Kevin", "Oscar", "Stanley")
STAFF_SLUGS = (
    "ceo",
    "market-intelligence-research",
    "challenge",
    "risk",
    "trader",
    "quant-strategy",
    "technology",
)


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
    floor_js = JS + JOBS_JS
    assert "right-panel" in JS
    assert "status" in JS.lower() or "bubble" in JS.lower()
    assert "ceo" in floor_js
    assert "challenge" in floor_js
    assert "risk" in floor_js
    assert "market-intelligence-research" in floor_js
    assert "Ask the CEO" in JS or "ceo" in floor_js
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
    assert 'display_name: "Asha Patel · Research"' in JOBS_JS
    assert 'display_name: "Jordan Hale · CEO"' in JOBS_JS
    assert 'display_name: "Sam Okeke · Challenge"' in JOBS_JS
    assert 'display_name: "Elena Voss · Risk"' in JOBS_JS
    assert 'display_name: "Chris Adeyemi · Trader"' in JOBS_JS
    assert 'display_name: "Nina Kapoor · Quant"' in JOBS_JS
    assert 'display_name: "Owen Blake · Technology"' in JOBS_JS
    assert 'display_name: "Research"' not in JS
    assert 'display_name: "Research"' not in JOBS_JS
    assert 'status_bubble: "OFFLINE"' not in JS
    assert 'status_bubble: "OFFLINE"' not in JOBS_JS
    assert "staff-jobs.json" in JS
    assert "staff-jobs.js" in HTML
    assert "Display off — staff still at work" in HTML
    assert 'id="building-banner"' in HTML
    assert "Resting" in JOBS_JS
    assert "Resting" in FLOOR
    assert "building-banner" in CSS
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
    vendor = ROOT / "desktop" / "vendor" / "claude-office"
    room = vendor / "rooms" / "office-day.png"
    license_file = vendor / "LICENSE"
    notice = ROOT / "desktop" / "vendor" / "NOTICE.md"
    desk = vendor / "sprites" / "furniture" / "standing-desk-left-rear.png"
    chars = [
        vendor / "sprites" / "characters" / name
        for name in (
            "Me-1-rear-left.png",
            "Claude-1-rear-right.png",
            "employee-1-front-left.png",
            "security-audit-1-rear-left.png",
            "employee-2-rear-right.png",
            "Frontend-dev-1-rear-left.png",
            "dev-1-rear-right.png",
        )
    ]
    assert room.is_file()
    assert room.stat().st_size > 1_000_000
    assert room.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert desk.is_file()
    assert desk.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert license_file.is_file()
    assert "W17ANT" in license_file.read_text(encoding="utf-8")
    assert notice.is_file()
    assert "W17ant/Claude-Office" in notice.read_text(encoding="utf-8")
    assert "did not draw" in notice.read_text(encoding="utf-8")
    for path in chars:
        assert path.is_file(), path
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert not (ROOT / "desktop" / "vendor" / "ai-office").exists()
    assert not (ROOT / "desktop" / "vendor" / "pixel-agents").exists()
    assert 'id="staff-bar"' in HTML
    assert "office-floor.js" in HTML
    assert "claude-office-layout.js" in HTML
    assert "placeholder pixels" not in HTML.lower()
    assert "office-day.png" in FLOOR
    assert "vendor/claude-office" in FLOOR
    assert "vendor/claude-office/rooms/office-day.png" in FLOOR
    assert "vendor/ai-office" not in FLOOR
    assert "fillRect a lookalike" in FLOOR or "Do not fillRect" in FLOOR
    assert "conferenceTable" not in FLOOR
    assert "poolTable" not in FLOOR
    assert "redCabinet" not in FLOOR
    assert "claude-office-isometric" in APP
    assert "placeholder-pixel-2d" not in APP
    assert "VarmaOfficeFloor" in JS
    assert "SEATS" in FLOOR
    assert "drawPortrait" in FLOOR
    assert "portraitUrl" in FLOOR
    assert "character-wrapper" in FLOOR
    assert "furniture-item" in FLOOR
    assert "game-frame" in HTML
    assert "game-frame" in CSS
    assert "room-container" in HTML
    assert "Click on a character to see chat history." in HTML
    assert 'id="board-observability-btn"' in HTML
    assert 'data-employee-slug="board"' not in HTML
    assert "staff-portrait" in HTML
    assert "paintPortraits" in JS
    assert "Press Start 2P" in CSS or "Press Start 2P" in HTML
    assert "Approve LIVE" not in HTML
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
    assert "ROOM_URL" in FLOOR
    assert "CHAR_DIR" in FLOOR
    assert FLOOR.count("Me-1") >= 1
    assert not (vendor / "sprites" / "office").exists()
    assert not (vendor / "rooms" / "office-day-dm.png").exists()


def test_office_uses_varma_staff_not_sitcom_names():
    layout = (ROOT / "desktop" / "src" / "claude-office-layout.js").read_text(encoding="utf-8")
    blob = HTML + CSS + JS + FLOOR + JOBS_JS + layout
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
        assert label in JOBS_JS


def test_floor_jobs_are_desk_text_not_kernel_presence():
    jobs = JOBS_JSON["jobs"]
    assert set(jobs) == set(STAFF_SLUGS)
    assert jobs["ceo"] == "Running desk"
    assert jobs["market-intelligence-research"] == "US pack"
    assert jobs["challenge"] == "Challenge"
    assert jobs["risk"] == "US ticket ready"
    assert jobs["trader"] == "Watching SHEL"
    assert jobs["quant-strategy"] == "US-open rule"
    assert jobs["technology"] == "Backups"
    for job in jobs.values():
        assert job
        assert job != "OFFLINE"
        assert job != "AVAILABLE"
        assert len(job.split()) <= 4
    assert 'RESTING = "Resting"' in JOBS_JS
    assert "OFFLINE: true" in JOBS_JS
    assert "AVAILABLE: true" in JOBS_JS
    assert "PAPER_DAY_JOBS" in JOBS_JS
    assert "applyJobs" in JOBS_JS
    assert "setDisplayOff" in JS
    assert "paintJobs" in JS
    assert "kernel unreachable — display off" in JS
    assert "Click never grants authority" in JOBS_JS
    assert 'data-employee-slug="board"' not in HTML
    assert "Approve LIVE" not in HTML


def test_staff_job_resolver_resting_not_offline():
    import subprocess

    jobs_js = str(ROOT / "desktop" / "src" / "staff-jobs.js")
    jobs_json = str(ROOT / "desktop" / "staff-jobs.json")
    script = f"""
global.window = global;
require({json.dumps(jobs_js)});
const J = window.VarmaStaffJobs;
const jobs = require({json.dumps(jobs_json)}).jobs;
const painted = J.applyJobs(J.STAFF_ROSTER, jobs);
if (painted.some((e) => e.status_bubble === "OFFLINE")) process.exit(2);
if (painted.find((e) => e.slug === "trader").status_bubble !== "Watching SHEL") process.exit(3);
const resting = J.applyJobs(J.STAFF_ROSTER, Object.assign({{}}, jobs, {{ challenge: "" }}));
if (resting.find((e) => e.slug === "challenge").status_bubble !== "Resting") process.exit(4);
const presence = J.applyJobs(
  [{{ slug: "trader", status_bubble: "OFFLINE" }}, {{ slug: "ceo", status_bubble: "AVAILABLE" }}],
  jobs
);
if (presence.find((e) => e.slug === "trader").status_bubble !== "Watching SHEL") process.exit(5);
if (J.DISPLAY_OFF_BANNER.indexOf("staff still at work") === -1) process.exit(6);
console.log("ok");
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout

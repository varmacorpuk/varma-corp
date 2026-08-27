from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "desktop" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "desktop" / "src" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "desktop" / "src" / "office.js").read_text(encoding="utf-8")


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

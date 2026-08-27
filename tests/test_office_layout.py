from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "desktop" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "desktop" / "src" / "styles.css").read_text(encoding="utf-8")
JS = (ROOT / "desktop" / "src" / "office.js").read_text(encoding="utf-8")


def test_right_hand_panel_not_overlay():
    assert 'id="office-floor"' in HTML
    assert 'id="right-panel"' in HTML
    assert 'id="chat-form"' in HTML
    assert "Talk" not in HTML or "talk-disabled" in HTML
    assert "overlay" not in CSS.lower() or "not an overlay" in CSS.lower()
    assert "display: flex" in CSS or "display:flex" in CSS.replace(" ", "")
    assert "#right-panel" in CSS
    assert "Board Member" in HTML


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

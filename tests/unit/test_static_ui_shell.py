from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "services" / "api" / "static"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_index_contains_phase_ui_shell_and_disclaimer() -> None:
    html = _read(STATIC_DIR / "index.html")
    assert 'id="auth-gate"' in html
    assert 'id="onboarding-wizard"' in html
    assert 'data-view="dashboard"' in html
    assert 'data-view="onboarding"' not in html
    assert 'data-view="mercado"' in html
    assert 'data-view="operacoes"' in html
    assert 'data-view="backtest"' in html
    assert 'data-view="risco"' in html
    assert 'data-view="game"' in html
    assert 'data-view="alertas"' in html
    assert 'id="b3-universe-sync-form"' in html
    assert 'id="news-sync-form"' in html
    assert 'id="intraday-fetch-form"' in html
    assert 'id="refresh-feed-health"' in html
    assert 'id="game-setup-form"' in html
    assert 'id="game-decision-form"' in html
    assert 'id="dashboard-coverage-table"' in html
    assert 'id="dashboard-quality-summary"' in html
    assert 'id="dashboard-quality-table"' in html
    assert 'id="logout-btn"' in html
    assert 'id="sidebar-toggle"' in html
    assert 'name="user_id"' not in html
    assert "terminal-output" not in html
    assert 'id="seed-market"' not in html
    assert 'id="seed-news"' not in html
    assert "Conteúdo analítico e educacional." in html
    assert "Operações são simuladas. CVM Res. 19/2021." in html


def test_styles_define_design_tokens_and_mono_font() -> None:
    css = _read(STATIC_DIR / "styles.css")
    assert ":root {" in css
    assert "--c-bg:" in css
    assert "--c-accent:" in css
    assert "--font-mono:" in css
    assert ".mono {" in css
    assert "font-family: var(--font-mono);" in css


def test_app_script_has_navigation_and_feed_status_logic() -> None:
    script = _read(STATIC_DIR / "app.js")
    assert 'const TOKEN_KEY = "ia_session_token";' in script
    assert "function showAuthGate()" in script
    assert "function getAuthUserId()" in script
    assert "function switchView(viewId)" in script
    assert "function refreshFeedStatus()" in script
    assert '"/api/market/external/b3/sync-universe-range"' in script
    assert '"/api/news/external/sync-period"' in script
    assert '"/api/market/feed/health"' in script
    assert '"/api/data-quality/gate"' in script
    assert '"/api/market/intraday/fetch-live"' in script
    assert '"/api/theses/game-playbook"' in script
    assert "function bindGameHandlers()" in script
    assert "function renderCoverage(coverage)" in script
    assert "function renderDataQualityGate(gate)" in script
    assert "function buildTimeSeries(" not in script
    assert "window.setInterval(refreshFeedStatus, 15000);" in script

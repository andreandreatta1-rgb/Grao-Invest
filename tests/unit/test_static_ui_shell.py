from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPO_ROOT / "services" / "api" / "frontend_dist"


def _read(path: Path) -> str:
    assert path.exists(), f"Expected tracked frontend artifact at {path}"
    return path.read_text(encoding="utf-8")


def test_frontend_bundle_contains_modern_shell_and_assets() -> None:
    html = _read(FRONTEND_DIST_DIR / "index.html")

    assert '<div id="root"></div>' in html
    assert 'href="/manifest.webmanifest"' in html
    assert 'href="/apple-touch-icon.png"' in html
    assert re.search(r'src="/assets/index-[^"]+\.js"', html)
    assert re.search(r'href="/assets/index-[^"]+\.css"', html)
    assert "Grão Invest" in html
    assert "Laboratório de Teses de Investimento" in html
    assert (FRONTEND_DIST_DIR / "assets").is_dir()
    assert (FRONTEND_DIST_DIR / "icon-192.png").exists()
    assert (FRONTEND_DIST_DIR / "icon-512.png").exists()
    assert (FRONTEND_DIST_DIR / "apple-touch-icon.png").exists()


def test_frontend_bundle_has_no_mojibake_in_visible_shell_text() -> None:
    bundle_paths = sorted((FRONTEND_DIST_DIR / "assets").glob("index-*.js"))
    assert bundle_paths, "Expected a built frontend JS bundle"
    bundle = bundle_paths[-1].read_text(encoding="utf-8")

    forbidden_tokens = ["GrÃ", "DecisÃ", "LaboratÃ", "ConfiguraÃ", "ConteÃ", "Â·"]
    assert not any(token in bundle for token in forbidden_tokens)


def test_cockpit_defers_full_thesis_fetch_until_summary_loaded() -> None:
    source = _read(REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "pages" / "Cockpit.tsx")

    assert 'enabled: Boolean(data)' in source


def test_manifest_keeps_pwa_installability_metadata() -> None:
    manifest = json.loads(_read(FRONTEND_DIST_DIR / "manifest.webmanifest"))

    assert manifest["name"].startswith("Grão Invest")
    assert manifest["short_name"] == "Grão Invest"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] == "#08101C"
    assert manifest["background_color"] == "#08101C"
    icon_sources = {icon["src"] for icon in manifest["icons"]}
    assert "/icon-192.png" in icon_sources
    assert "/icon-512.png" in icon_sources
    assert "/icon-512-maskable.png" in icon_sources

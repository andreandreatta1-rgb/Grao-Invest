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
    assert (
        re.search(r'href="/assets/index-[^"]+\.css"', html)
        or 'id="grao-mobile-responsive-patch"' in html
    )
    assert "Grão Invest" in html or "Gr&atilde;o Invest" in html
    assert (
        "Laboratório de Teses de Investimento" in html
        or "Laborat&oacute;rio de Teses de Investimento" in html
    )
    assert (FRONTEND_DIST_DIR / "assets").is_dir()
    assert (FRONTEND_DIST_DIR / "icon-192.png").exists()
    assert (FRONTEND_DIST_DIR / "icon-512.png").exists()
    assert (FRONTEND_DIST_DIR / "apple-touch-icon.png").exists()


def test_mobile_responsive_patch_is_present_and_sync_enforced() -> None:
    html = _read(FRONTEND_DIST_DIR / "index.html")
    patch = _read(
        REPO_ROOT
        / "services"
        / "api"
        / "frontend_shell_patches"
        / "mobile-responsive-patch.html"
    )
    sync_script = _read(REPO_ROOT / "scripts" / "sync_thesis_lab_frontend.ps1")
    patch_script = _read(REPO_ROOT / "scripts" / "apply_frontend_shell_patches.py")

    assert 'id="grao-mobile-responsive-patch"' in html
    assert "#root > div > aside" in html
    assert "grid-template-columns: minmax(0, 1fr)" in html
    assert 'id="grao-mobile-responsive-patch"' in patch
    assert "apply_frontend_shell_patches.py" in sync_script
    assert "grao-mobile-responsive-patch" in patch_script


def test_frontend_bundle_has_no_mojibake_in_visible_shell_text() -> None:
    bundle_paths = sorted((FRONTEND_DIST_DIR / "assets").glob("index-*.js"))
    assert bundle_paths, "Expected a built frontend JS bundle"
    bundle = bundle_paths[-1].read_text(encoding="utf-8")

    forbidden_tokens = ["GrÃ", "DecisÃ", "LaboratÃ", "ConfiguraÃ", "ConteÃ", "Â·"]
    assert not any(token in bundle for token in forbidden_tokens)


def test_cockpit_defers_full_thesis_fetch_until_summary_loaded() -> None:
    source = _read(REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "pages" / "Cockpit.tsx")

    assert 'enabled: Boolean(data)' in source


def test_metodo_grao_onboarding_is_routed_and_asset_backed() -> None:
    app_source = _read(REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "App.tsx")
    shell_source = _read(
        REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "components" / "MobileShell.tsx"
    )
    metodo_source = _read(
        REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "lib" / "metodo-grao-scenes.ts"
    )
    metodo_page = _read(REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "pages" / "MetodoGrao.tsx")
    public_metodo = REPO_ROOT / "apps" / "thesis-lab-view" / "public" / "metodo" / "06_sequencia_09"

    assert 'path="/metodo"' in app_source
    assert 'label: "Método"' in shell_source
    assert "hasSeenMetodoOnboarding" in shell_source
    assert 'METODO_ONBOARDING_KEY = "graoinvest.metodo_onboarding_seen"' in metodo_source
    assert "markMetodoOnboardingSeen" in metodo_page
    assert "order-2 lg:order-1" in metodo_page
    assert "order-1 lg:order-2" in metodo_page

    for step in [f"{index:02d}" for index in range(1, 10)]:
        assert (public_metodo / "audio" / f"{step}.mp3").exists()

    for step in ["01", "02", "04", "05", "06", "07", "08", "09"]:
        assert (public_metodo / "video" / f"{step}.mp4").exists()
        assert (public_metodo / "poster" / f"{step}.png").exists()

    assert (public_metodo / "image" / "03.png").exists()


def test_metodo_grao_screen_images_are_used_by_shell() -> None:
    scene_source = _read(
        REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "lib" / "metodo-grao-scenes.ts"
    )
    shell_source = _read(
        REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "components" / "MobileShell.tsx"
    )
    public_images = REPO_ROOT / "apps" / "thesis-lab-view" / "public" / "metodo" / "imagens"

    assert "metodoGraoScreenImages" in scene_source
    assert "getMetodoGraoScreenImage" in scene_source
    assert "getMetodoGraoScreenImage(pathname)" in shell_source
    assert 'alt={screenImage.alt}' in shell_source
    assert 'src={screenImage.src}' in shell_source

    for step in [f"{index:02d}" for index in range(1, 10)]:
        assert (public_images / f"{step}.webp").exists()


def test_metodo_grao_audio_playback_is_user_gesture_driven() -> None:
    metodo_page = _read(REPO_ROOT / "apps" / "thesis-lab-view" / "src" / "pages" / "MetodoGrao.tsx")

    assert "playMedia(withAudio)" in metodo_page
    assert "playMedia(nextAudioOn)" in metodo_page
    assert "audioOnRef.current" in metodo_page
    assert "elapsedMs, index, isPlaying" not in metodo_page
    assert "flex items-center justify-center p-4" in metodo_page
    assert "w-full max-w-sm" in metodo_page
    assert "h-[32rem] w-full max-h-[72vh]" in metodo_page
    assert "aspect-video min-h-[32rem]" not in metodo_page


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

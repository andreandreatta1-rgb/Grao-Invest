from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPO_ROOT / "services" / "api" / "frontend_dist"
HTML_PATH = FRONTEND_DIST_DIR / "index.html"


def _html() -> str:
    assert HTML_PATH.exists(), f"Expected tracked frontend artifact at {HTML_PATH}"
    return HTML_PATH.read_text(encoding="utf-8")


def _bundle_text() -> str:
    html = _html()
    asset_match = re.search(r'src="(?P<asset>/assets/index-[^"]+\.js)"', html)
    assert asset_match is not None, "Expected JS bundle reference in frontend_dist/index.html"
    asset_path = FRONTEND_DIST_DIR / asset_match.group("asset").lstrip("/")
    assert asset_path.exists(), f"Expected bundle at {asset_path}"
    return asset_path.read_text(encoding="utf-8")


FORBIDDEN_COPY_PATTERNS = [
    r"\bcompre agora\b",
    r"\bvenda agora\b",
    r"\binvista agora\b",
    r"\blucro garantido\b",
    r"\bretorno garantido\b",
    r"\bsem risco\b",
    r"\brecomendamos compra\b",
    r"\brecomendamos venda\b",
]


def test_no_forbidden_recommendation_copy() -> None:
    bundle = f"{_html()}\n{_bundle_text()}".lower()
    violations = [pattern for pattern in FORBIDDEN_COPY_PATTERNS if re.search(pattern, bundle)]
    assert not violations, (
        "HTML contém linguagem proibida de recomendação: "
        f"{', '.join(violations)}"
    )


def test_disclaimer_is_present() -> None:
    bundle = _bundle_text()
    assert "CVM" in bundle
    assert "simulad" in bundle.lower()
    assert "educacional" in bundle.lower()


def test_no_hardcoded_credentials() -> None:
    bundle = f"{_html()}\n{_bundle_text()}"
    assert "SenhaForte123!" not in bundle
    assert "enzo@example.com" not in bundle
    assert "andre@example.com" not in bundle.lower()
    assert not re.search(
        r'<input[^>]*type=["\']password["\'][^>]*\bvalue=["\']',
        bundle,
        flags=re.IGNORECASE,
    )


def test_no_visible_user_id_fields() -> None:
    bundle = _bundle_text()
    visible_user_id_fields = re.findall(
        r'<input(?![^>]*type=["\']hidden["\'])[^>]*name=["\']user_id["\'][^>]*>',
        bundle,
        flags=re.IGNORECASE,
    )
    assert not visible_user_id_fields


def test_no_terminal_output_elements() -> None:
    bundle = _bundle_text()
    terminal_outputs = re.findall(
        r'class=["\'][^"\']*terminal-output[^"\']*["\']',
        bundle,
        flags=re.IGNORECASE,
    )
    assert not terminal_outputs

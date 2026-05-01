from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = REPO_ROOT / "services" / "api" / "static" / "index.html"


def _html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


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
    html = _html().lower()
    violations = [pattern for pattern in FORBIDDEN_COPY_PATTERNS if re.search(pattern, html)]
    assert not violations, (
        "HTML contém linguagem proibida de recomendação: "
        f"{', '.join(violations)}"
    )


def test_disclaimer_is_present() -> None:
    html = _html()
    assert "global-disclaimer" in html
    assert "CVM" in html
    assert "simulad" in html.lower()


def test_no_hardcoded_credentials() -> None:
    html = _html()
    assert "SenhaForte123!" not in html
    assert "enzo@example.com" not in html
    assert "andre@example.com" not in html.lower()
    assert not re.search(
        r'<input[^>]*type=["\']password["\'][^>]*\bvalue=["\']',
        html,
        flags=re.IGNORECASE,
    )


def test_no_visible_user_id_fields() -> None:
    html = _html()
    visible_user_id_fields = re.findall(
        r'<input(?![^>]*type=["\']hidden["\'])[^>]*name=["\']user_id["\'][^>]*>',
        html,
        flags=re.IGNORECASE,
    )
    assert not visible_user_id_fields


def test_no_terminal_output_elements() -> None:
    html = _html()
    terminal_outputs = re.findall(
        r'class=["\'][^"\']*terminal-output[^"\']*["\']',
        html,
        flags=re.IGNORECASE,
    )
    assert not terminal_outputs

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_DIR = REPO_ROOT / "services" / "api" / "frontend_shell_patches"
MOBILE_PATCH = PATCH_DIR / "mobile-responsive-patch.html"
PATCH_ID = "grao-mobile-responsive-patch"
INSERT_BEFORE = '    <meta property="og:type" content="website" />'
FALLBACK_INSERT_BEFORE = '    <script type="module"'


def apply_mobile_patch(frontend_dist: Path) -> Path:
    index_path = frontend_dist / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"index.html not found at {index_path}")

    patch = MOBILE_PATCH.read_text(encoding="utf-8").strip("\n")
    if f'id="{PATCH_ID}"' not in patch:
        raise ValueError(f"Patch file must contain id={PATCH_ID!r}")

    html = index_path.read_text(encoding="utf-8")
    html = re.sub(
        rf"\n?[ \t]*<style\s+id=[\"']{re.escape(PATCH_ID)}[\"']>.*?</style>[ \t]*\r?\n?",
        "\n",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"\n{2,}([ \t]*<(?:meta property=\"og:type\"|script type=\"module\"))",
        r"\n\1",
        html,
    )

    if INSERT_BEFORE in html:
        patched = html.replace(INSERT_BEFORE, f"{patch}\n\n{INSERT_BEFORE}", 1)
    elif FALLBACK_INSERT_BEFORE in html:
        patched = html.replace(FALLBACK_INSERT_BEFORE, f"{patch}\n\n{FALLBACK_INSERT_BEFORE}", 1)
    else:
        raise ValueError(
            "Could not find insertion marker in "
            f"{index_path}: {INSERT_BEFORE} or {FALLBACK_INSERT_BEFORE}"
        )

    index_path.write_text(patched, encoding="utf-8")
    return index_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply stable HTML shell patches to the built frontend_dist artifact.",
    )
    parser.add_argument(
        "--frontend-dist",
        type=Path,
        default=REPO_ROOT / "services" / "api" / "frontend_dist",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    index_path = apply_mobile_patch(args.frontend_dist)
    print(f"Applied mobile responsive shell patch to {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

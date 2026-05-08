from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
WEB_ROOT = WORKSPACE_ROOT / "apps" / "grao-invest-cockpit"

BACKEND_CONTRACT_TESTS = [
    "tests/unit/test_thesis_current_monitor.py",
    "tests/unit/test_thesis_current_by_front_job.py",
    "tests/unit/test_data_quality.py",
    "tests/e2e/test_current_thesis_monitor_api.py",
]

FRONTEND_TRUST_TESTS = [
    "src/__tests__/dataTrust.test.jsx",
    "src/__tests__/formatters.test.js",
    "src/__tests__/cockpitHalleyAdapter.test.js",
    "src/__tests__/components.test.jsx",
    "src/__tests__/CockpitHalley.test.jsx",
]

CURRENT_MONITOR_ARTIFACTS = [
    "data/current_thesis_monitor_latest.json",
    "data/current_thesis_by_front_latest.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa o portao de confianca do Grao Invest: contratos de dados atuais, "
            "testes criticos backend/frontend e build web."
        )
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Roda apenas testes frontend criticos em vez da suite Vitest completa.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Nao roda o build Vite.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Nao roda testes/build frontend.",
    )
    parser.add_argument(
        "--skip-backend-tests",
        action="store_true",
        help="Nao roda os testes backend focados.",
    )
    parser.add_argument(
        "--enforce-fresh-b3",
        action="store_true",
        help="Falha se tese B3 atual estiver mais velha que 96h no artefato.",
    )
    return parser.parse_args()


def run(command: list[str], *, cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def python_executable() -> str:
    return sys.executable


def node_executable() -> str:
    candidates = [
        str(
            Path.home()
            / ".cache"
            / "codex-runtimes"
            / "codex-primary-runtime"
            / "dependencies"
            / "node"
            / "bin"
            / "node.exe"
        ),
        str(
            Path.home()
            / ".cache"
            / "codex-runtimes"
            / "codex-primary-runtime"
            / "dependencies"
            / "node"
            / "bin"
            / "node"
        ),
        shutil.which("node"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("Node.js nao encontrado para executar os testes frontend.")


def parse_reference_time(payload: dict[str, object]) -> datetime | None:
    raw = payload.get("generated_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def validate_current_monitor_artifacts(*, enforce_fresh_b3: bool) -> None:
    sys.path.insert(0, str(REPO_ROOT / "services" / "api"))
    from app.services.thesis_current_monitor import current_monitor_contract_issues

    failed = False
    for relative_path in CURRENT_MONITOR_ARTIFACTS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            print(f"[skip] artefato ausente: {relative_path}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(f"[fail] {relative_path}: JSON raiz nao e objeto.")
            failed = True
            continue
        issues = current_monitor_contract_issues(
            payload,
            reference_time=parse_reference_time(payload),
            enforce_fresh_b3=enforce_fresh_b3,
        )
        errors = [issue for issue in issues if issue["severity"] == "error"]
        if errors:
            failed = True
            print(f"[fail] {relative_path}: {len(errors)} erro(s) de contrato")
            for issue in errors[:12]:
                print(f"  - {issue['code']}: {issue['message']}")
        else:
            print(f"[ok] {relative_path}: contrato valido")
    if failed:
        raise SystemExit(1)


def run_backend_checks(args: argparse.Namespace) -> None:
    py = python_executable()
    run(
        [
            py,
            "-m",
            "ruff",
            "check",
            "services/api/app/services/thesis_current_monitor.py",
            "services/api/app/services/thesis_case_study.py",
            "services/api/app/services/thesis_current_by_front_job.py",
            "scripts/run_current_thesis_by_front_job.py",
            "scripts/trust_sanity_gate.py",
            "tests/unit/test_thesis_current_monitor.py",
            "tests/unit/test_thesis_current_by_front_job.py",
        ],
        cwd=REPO_ROOT,
    )
    validate_current_monitor_artifacts(enforce_fresh_b3=args.enforce_fresh_b3)
    if not args.skip_backend_tests:
        run([py, "-m", "pytest", *BACKEND_CONTRACT_TESTS, "-q"], cwd=REPO_ROOT)


def run_frontend_checks(args: argparse.Namespace) -> None:
    if args.skip_frontend:
        return
    if not WEB_ROOT.exists():
        raise SystemExit(f"Frontend nao encontrado em {WEB_ROOT}")
    node = node_executable()
    vitest = WEB_ROOT / "node_modules" / "vitest" / "dist" / "cli.js"
    vite = WEB_ROOT / "node_modules" / "vite" / "bin" / "vite.js"
    if not vitest.exists():
        raise SystemExit(f"Vitest nao encontrado em {vitest}")
    if not vite.exists():
        raise SystemExit(f"Vite nao encontrado em {vite}")

    frontend_test_args = FRONTEND_TRUST_TESTS if args.quick else []
    run([node, str(vitest), "run", *frontend_test_args], cwd=WEB_ROOT)
    if not args.skip_build:
        run([node, str(vite), "build"], cwd=WEB_ROOT)


def main() -> None:
    args = parse_args()
    run_backend_checks(args)
    run_frontend_checks(args)
    print("Trust sanity gate aprovado.")


if __name__ == "__main__":
    main()

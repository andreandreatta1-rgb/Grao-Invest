from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_branch(repo_root: Path, requested_branch: str | None) -> str:
    if requested_branch:
        return requested_branch
    result = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        raise SystemExit(f"Falha ao descobrir branch atual: {result.stderr.strip()}")
    branch = result.stdout.strip()
    if not branch:
        raise SystemExit("Branch atual vazio.")
    return branch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publica atualizacao do dashboard seed para disparar novo deploy no Vercel via git push."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default="",
        help="Raiz do repositório. Vazio = auto-detecta pela pasta do script.",
    )
    parser.add_argument(
        "--remote",
        type=str,
        default="origin",
        help="Remote do git para push.",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="",
        help="Branch de destino. Vazio = branch atual.",
    )
    parser.add_argument(
        "--message",
        type=str,
        default="",
        help="Mensagem de commit. Vazio = gera automaticamente com data/hora.",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Commit local sem push.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = (
        Path(args.repo_root).resolve()
        if args.repo_root.strip()
        else Path(__file__).resolve().parents[1]
    )
    seed_path = repo_root / "data" / "dashboard_seed.json"
    if not seed_path.exists():
        raise SystemExit(f"Arquivo nao encontrado: {seed_path}")

    status = _run_git(repo_root, ["status", "--porcelain", "--", str(seed_path)])
    if status.returncode != 0:
        raise SystemExit(f"Falha ao verificar status git: {status.stderr.strip()}")
    if not status.stdout.strip():
        print("Sem mudancas em data/dashboard_seed.json. Nada para publicar.")
        return

    add_result = _run_git(repo_root, ["add", str(seed_path)])
    if add_result.returncode != 0:
        raise SystemExit(f"Falha no git add: {add_result.stderr.strip()}")

    commit_message = args.message.strip() or (
        "chore: atualiza dashboard seed "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    commit_result = _run_git(repo_root, ["commit", "-m", commit_message])
    if commit_result.returncode != 0:
        raise SystemExit(f"Falha no git commit: {commit_result.stderr.strip()}")

    print(commit_result.stdout.strip() or "Commit criado.")

    if args.skip_push:
        print("Push pulado por --skip-push.")
        return

    branch = _resolve_branch(repo_root, args.branch.strip() or None)
    push_result = _run_git(repo_root, ["push", args.remote, branch])
    if push_result.returncode != 0:
        raise SystemExit(f"Falha no git push: {push_result.stderr.strip()}")
    print(push_result.stdout.strip() or f"Push concluido em {args.remote}/{branch}.")


if __name__ == "__main__":
    main()

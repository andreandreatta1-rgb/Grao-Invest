from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from app.db import SessionLocal
from app.services.thesis_current_by_front_job import (
    DEFAULT_B3_INSTRUMENTS,
    DEFAULT_CRYPTO_INSTRUMENTS,
    FrontConfig,
    run_current_thesis_by_front_job,
    write_current_by_front_outputs,
)


def _csv_items(raw: str) -> list[str]:
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _fronts_from_args(args: argparse.Namespace) -> list[FrontConfig]:
    fronts: list[FrontConfig] = []
    b3_instruments = _csv_items(args.b3_instruments)
    crypto_instruments = _csv_items(args.crypto_instruments)

    if not args.skip_b3:
        fronts.append(
            FrontConfig(
                front_id="acoes_b3",
                label="Acoes B3",
                instruments=b3_instruments,
            )
        )
    if not args.skip_crypto:
        fronts.append(
            FrontConfig(
                front_id="cripto",
                label="Cripto",
                instruments=crypto_instruments,
            )
        )
    if not fronts:
        raise SystemExit("Nenhuma frente selecionada. Remova --skip-b3 ou --skip-crypto.")
    return fronts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Job de teses atuais por frente: roda Acoes B3 e Cripto, combina o snapshot "
            "e atualiza os arquivos consumidos pelo dashboard."
        )
    )
    parser.add_argument("--user-id", type=int, default=1, help="ID do usuario.")
    parser.add_argument(
        "--b3-instruments",
        type=str,
        default=",".join(DEFAULT_B3_INSTRUMENTS),
        help="Lista CSV de ativos B3 para o monitor atual.",
    )
    parser.add_argument(
        "--crypto-instruments",
        type=str,
        default=",".join(DEFAULT_CRYPTO_INSTRUMENTS),
        help="Lista CSV de criptos para o monitor atual.",
    )
    parser.add_argument("--skip-b3", action="store_true", help="Nao roda a frente Acoes B3.")
    parser.add_argument("--skip-crypto", action="store_true", help="Nao roda a frente Cripto.")
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=8,
        help="Quantidade de barras para construcao da tese.",
    )
    parser.add_argument(
        "--thesis-count-per-front",
        type=int,
        default=8,
        help="Quantidade maxima de teses por frente.",
    )
    parser.add_argument(
        "--recent-bars-window",
        type=int,
        default=30,
        help=(
            "Janela de barras para considerar tese como atual. Valor alto permite "
            "usar a base historica como treino continuo."
        ),
    )
    parser.add_argument(
        "--oversample-factor",
        type=int,
        default=5,
        help=(
            "Busca mais candidatos internamente para evitar publicar varias teses "
            "iguais do mesmo ativo."
        ),
    )
    parser.add_argument(
        "--max-latest-age-days",
        type=int,
        default=0,
        help=(
            "Ignora ativos cujo ultimo preco local esteja mais velho que este limite. "
            "Use 0 para inferir a janela pelo intervalo dos ticks e evitar publicar "
            "dado velho como atual."
        ),
    )
    parser.add_argument(
        "--skip-dashboard-seed",
        action="store_true",
        help="Nao atualiza data/dashboard_seed.json apos combinar as frentes.",
    )
    parser.add_argument(
        "--publish-dashboard-seed",
        action="store_true",
        help="Depois do seed, cria commit e push via scripts/publish_dashboard_seed.py.",
    )
    parser.add_argument(
        "--publish-skip-push",
        action="store_true",
        help="Quando publicar, cria commit local mas nao faz push.",
    )
    return parser.parse_args()


def _refresh_dashboard_seed(repo_root: Path, user_id: int) -> dict[str, Any]:
    from run_b3_daily_job import _refresh_dashboard_seed as refresh_dashboard_seed

    return refresh_dashboard_seed(repo_root, user_id)


def _publish_dashboard_seed(repo_root: Path, *, skip_push: bool) -> int:
    command = [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(repo_root / "scripts" / "publish_dashboard_seed.py"),
        "--repo-root",
        str(repo_root),
    ]
    if skip_push:
        command.append("--skip-push")
    completed = subprocess.run(command, cwd=repo_root, check=False)
    return int(completed.returncode)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    fronts = _fronts_from_args(args)

    with SessionLocal() as db:
        payload = run_current_thesis_by_front_job(
            db,
            user_id=args.user_id,
            fronts=fronts,
            horizon_bars=args.horizon_bars,
            thesis_count_per_front=args.thesis_count_per_front,
            recent_bars_window=args.recent_bars_window,
            max_latest_age_days=args.max_latest_age_days,
            oversample_factor=args.oversample_factor,
        )
        db.commit()

    output_files = write_current_by_front_outputs(payload)
    dashboard_seed: dict[str, Any] = {"executed": False}
    if not args.skip_dashboard_seed:
        dashboard_seed = _refresh_dashboard_seed(repo_root, args.user_id)

    publish_exit_code: int | None = None
    if args.publish_dashboard_seed:
        publish_exit_code = _publish_dashboard_seed(repo_root, skip_push=args.publish_skip_push)
        if publish_exit_code != 0:
            raise SystemExit(f"Publicacao do dashboard seed falhou (exit={publish_exit_code}).")

    summary = payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    print(f"Arquivo gerado: {output_files['json_file']}")
    print(f"Arquivo gerado: {output_files['markdown_file']}")
    print(f"Arquivo gerado: {output_files['latest_markdown_file']}")
    if dashboard_seed.get("executed"):
        print(f"Dashboard seed atualizado: {dashboard_seed.get('summary_file')}")
    else:
        print("Dashboard seed nao atualizado.")
    print(
        "Resumo current-by-front: "
        f"thesis_count={payload.get('thesis_count', 0)} | "
        f"target_hits={summary_dict.get('target_hits', 0)} | "
        f"stop_alerts={summary_dict.get('stop_alerts', 0)} | "
        f"monitoring_count={summary_dict.get('monitoring_count', 0)} | "
        f"avg_unrealized_financial_pct={summary_dict.get('avg_unrealized_financial_pct', 0)}"
    )
    if publish_exit_code is not None:
        print(f"Publicacao dashboard seed concluida (exit={publish_exit_code}).")


if __name__ == "__main__":
    main()

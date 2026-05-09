from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.db import DATA_DIR, SessionLocal
from app.services.b3_daily_job import (
    build_b3_daily_job_markdown,
    find_latest_snapshot_dir,
    utc_iso_now,
)
from app.services.b3_data_lake import run_b3_bronze_silver_pipeline
from app.services.b3_external import DEFAULT_SMALL_PORTFOLIO
from app.services.b3_silver_loader import load_b3_silver_market_daily
from app.services.thesis_case_study import run_thesis_case_study


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Job diario unificado: build da lake B3 (bronze/silver), carga no banco "
            "market_ticks e execucao do case study de tese."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--source-root",
        type=str,
        default="",
        help="Pasta historico B3. Vazio = auto-detecta o snapshot mais recente.",
    )
    parser.add_argument(
        "--pesquisa-root",
        type=str,
        default="",
        help="Pasta pesquisa por pregao. Vazio = auto-detecta snapshot mais recente.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="data/lake/b3",
        help="Destino da data lake.",
    )
    parser.add_argument(
        "--full-universe",
        action="store_true",
        help="Processa universo completo no build COTAHIST.",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default=",".join(DEFAULT_SMALL_PORTFOLIO),
        help="Lista CSV de instrumentos quando nao usar --full-universe.",
    )
    parser.add_argument(
        "--max-rows-per-cotahist-file",
        type=int,
        default=0,
        help="Limite de linhas por arquivo COTAHIST (0 = sem limite).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="b3-cotahist-lake",
        help="Provider para carga em market_ticks.",
    )
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch de carga no SQLite.")
    parser.add_argument(
        "--flush-max-retries",
        type=int,
        default=80,
        help="Retries por batch em caso de lock no SQLite.",
    )
    parser.add_argument(
        "--truncate-provider-before-load",
        action="store_true",
        help="Limpa o provider antes de recarregar market_ticks.",
    )
    parser.add_argument(
        "--case-study-instruments",
        type=str,
        default="PETR4,VALE3",
        help="Lista CSV para o case study.",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=8,
        help="Horizonte de barras do case study.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Pula etapa de build lake.",
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Pula etapa de carga market_ticks.",
    )
    parser.add_argument(
        "--skip-case-study",
        action="store_true",
        help="Pula etapa de case study.",
    )
    parser.add_argument(
        "--skip-dashboard-seed",
        action="store_true",
        help="Pula atualizacao do dashboard_seed.json a partir do resumo mais recente.",
    )
    return parser.parse_args()


def _resolve_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _resolve_source_roots(repo_root: Path, args: argparse.Namespace) -> tuple[Path, Path | None]:
    data_b3_root = repo_root / "data" / "b3"
    if args.source_root.strip():
        source_root = _resolve_path(repo_root, args.source_root.strip())
    else:
        auto = find_latest_snapshot_dir(data_b3_root=data_b3_root, prefix="historico_")
        if auto is None:
            raise SystemExit(
                "Nao foi possivel auto-detectar pasta historico_YYYY-MM-DD em data/b3."
            )
        source_root = auto

    if args.pesquisa_root.strip():
        pesquisa_root = _resolve_path(repo_root, args.pesquisa_root.strip())
    else:
        pesquisa_root = find_latest_snapshot_dir(
            data_b3_root=data_b3_root,
            prefix="pesquisa_pregao_",
        )

    return source_root, pesquisa_root


def _refresh_dashboard_seed(repo_root: Path, user_id: int) -> dict[str, Any]:
    from app.main import app  # import tardio para reduzir efeito colateral no startup do script

    with TestClient(app) as client:
        response = client.get(f"/api/dashboard/summary/{user_id}")
        if response.status_code >= 400:
            raise SystemExit(
                "Falha ao gerar dashboard_seed.json "
                f"(status={response.status_code}): {response.text}"
            )
        payload = response.json()

    historical = payload.get("historical_analysis_summary")
    current = payload.get("current_simulation_summary")
    current_daily = payload.get("current_simulation_daily")
    overview = payload.get("thesis_history_overview")
    executive = payload.get("thesis_executive_summary")
    open_operations = payload.get("thesis_open_operations")
    front_overview = payload.get("front_overview")
    data_quality_gate = payload.get("data_quality_gate")
    ops_health = payload.get("ops_health")

    dashboard_seed = {
        "generated_at": utc_iso_now(),
        "user_id": int(payload.get("user_id") or user_id),
        "phase_kickoff_date": payload.get("phase_kickoff_date"),
        "historical_analysis_summary": historical if isinstance(historical, dict) else {},
        "current_simulation_summary": current if isinstance(current, dict) else {},
        "current_simulation_daily": current_daily if isinstance(current_daily, list) else [],
        "thesis_history_overview": overview if isinstance(overview, dict) else {},
        "thesis_executive_summary": executive if isinstance(executive, dict) else {},
        "thesis_open_operations": open_operations if isinstance(open_operations, list) else [],
        "front_overview": front_overview if isinstance(front_overview, dict) else {},
        "data_quality_gate": data_quality_gate if isinstance(data_quality_gate, dict) else {},
        "ops_health": ops_health if isinstance(ops_health, dict) else {},
    }

    output_path = repo_root / "data" / "dashboard_seed.json"
    output_path.write_text(
        json.dumps(dashboard_seed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    overview_dict = dashboard_seed["thesis_history_overview"]
    total_tested = int(overview_dict.get("total_tested") or 0) if isinstance(overview_dict, dict) else 0

    return {
        "executed": True,
        "user_id": int(dashboard_seed["user_id"]),
        "total_tested": total_tested,
        "summary_file": str(output_path),
    }


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    source_root, pesquisa_root = _resolve_source_roots(repo_root, args)
    output_root = _resolve_path(repo_root, args.output_root)
    database_path = DATA_DIR / "app.db"

    max_rows = args.max_rows_per_cotahist_file or None
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    case_study_instruments = [
        item.strip().upper() for item in args.case_study_instruments.split(",") if item.strip()
    ]

    summary: dict[str, Any] = {
        "pipeline": {
            "run_at": utc_iso_now(),
            "source_root": str(source_root),
            "pesquisa_root": str(pesquisa_root) if pesquisa_root is not None else "",
            "output_root": str(output_root),
            "database_path": str(database_path),
            "full_universe": bool(args.full_universe),
            "selected_instruments": instruments,
            "max_rows_per_cotahist_file": max_rows,
            "provider": args.provider,
        },
        "build": {"executed": False},
        "load": {"executed": False},
        "case_study": {"executed": False},
        "dashboard_seed": {"executed": False},
    }

    pesquisa_for_build = (
        pesquisa_root if pesquisa_root is not None and pesquisa_root.exists() else None
    )

    if not args.skip_build:
        build_payload = run_b3_bronze_silver_pipeline(
            source_root=source_root,
            output_root=output_root,
            instruments=instruments,
            include_all_instruments=args.full_universe,
            max_rows_per_cotahist_file=max_rows,
            pesquisa_root=pesquisa_for_build,
        )
        summary["build"] = {
            "executed": True,
            "cotahist_silver_rows": build_payload["datasets"]["cotahist"]["silver_rows"],
            "cambio_input_files": build_payload["datasets"]["cambio"]["input_files"],
            "renda_fixa_silver_rows": build_payload["datasets"]["renda_fixa"]["silver_rows"],
            "summary_file": str(repo_root / "data" / "b3_bronze_silver_latest.json"),
        }

    if not args.skip_load:
        market_daily_csv = output_root / "silver" / "market_daily.csv"
        load_payload = load_b3_silver_market_daily(
            csv_path=market_daily_csv,
            database_path=database_path,
            provider=args.provider,
            batch_size=args.batch_size,
            truncate_provider_before_load=args.truncate_provider_before_load,
            max_rows=None,
            flush_max_retries=args.flush_max_retries,
        )
        summary["load"] = {
            "executed": True,
            "provider": load_payload.provider,
            "rows_seen": load_payload.rows_seen,
            "rows_parsed": load_payload.rows_parsed,
            "inserted": load_payload.inserted,
            "duplicates_ignored": load_payload.duplicates_ignored,
            "parse_errors": load_payload.parse_errors,
            "truncated_existing_rows": load_payload.truncated_existing_rows,
            "summary_file": str(repo_root / "data" / "b3_silver_load_latest.json"),
        }

    if not args.skip_case_study:
        with SessionLocal() as db:
            case_payload = run_thesis_case_study(
                db,
                user_id=args.user_id,
                instruments=case_study_instruments or None,
                horizon_bars=args.horizon_bars,
            )
        selected_case = case_payload["selected_case"]
        kpis = selected_case["kpis"]
        thesis = selected_case["thesis"]
        summary["case_study"] = {
            "executed": True,
            "thesis_id": thesis["thesis_id"],
            "instrument": thesis["instrument"],
            "confidence_pct": kpis["confidence_tese_pct"],
            "expected_pct": kpis["expected_financial_pct"],
            "realized_pct": kpis["realized_financial_pct"],
            "json_file": str(repo_root / "data" / "case_study_latest.json"),
            "markdown_file": str(repo_root / "data" / "case_study_latest.md"),
        }

    if not args.skip_dashboard_seed:
        summary["dashboard_seed"] = _refresh_dashboard_seed(repo_root, args.user_id)

    output_json = repo_root / "data" / "b3_daily_job_latest.json"
    output_md = repo_root / "data" / "b3_daily_job_latest.md"
    output_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    output_md.write_text(build_b3_daily_job_markdown(summary), encoding="utf-8")

    print(f"Arquivo gerado: {output_json}")
    print(f"Arquivo gerado: {output_md}")
    print(
        "Resumo job diario: "
        f"build_executed={summary['build']['executed']} | "
        f"load_executed={summary['load']['executed']} | "
        f"case_study_executed={summary['case_study']['executed']} | "
        f"dashboard_seed_executed={summary['dashboard_seed']['executed']}"
    )


if __name__ == "__main__":
    main()

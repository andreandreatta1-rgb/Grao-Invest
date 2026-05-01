from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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
        f"case_study_executed={summary['case_study']['executed']}"
    )


if __name__ == "__main__":
    main()

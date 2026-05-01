from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.audit import record_audit_event
from app.services.data_quality import build_data_quality_gate_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa o data quality gate (cobertura, freshness e saude de providers) "
            "e grava artefato para operacao diaria."
        )
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="User ID opcional para trilha de auditoria.",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Lista CSV de instrumentos alvo (ex.: PETR4,VALE3).",
    )
    parser.add_argument(
        "--market-max-lag-seconds",
        type=int,
        default=1800,
        help="Lag maximo permitido para tick fresco.",
    )
    parser.add_argument(
        "--market-min-fresh-coverage-pct",
        type=float,
        default=95.0,
        help="Cobertura minima de ticks frescos no universo alvo.",
    )
    parser.add_argument(
        "--fundamentals-min-coverage-pct",
        type=float,
        default=90.0,
        help="Cobertura minima de fundamentos no universo alvo.",
    )
    parser.add_argument(
        "--fundamentals-max-staleness-days",
        type=int,
        default=1,
        help="Staleness maxima (dias) para considerar fundamento fresco.",
    )
    parser.add_argument(
        "--fundamentals-min-fresh-coverage-pct",
        type=float,
        default=90.0,
        help="Cobertura minima de fundamentos frescos no universo alvo.",
    )
    parser.add_argument(
        "--news-lookback-days",
        type=int,
        default=7,
        help="Janela de dias para cobertura de noticias recentes.",
    )
    parser.add_argument(
        "--news-min-coverage-pct",
        type=float,
        default=60.0,
        help="Cobertura minima de noticias recentes por ativo.",
    )
    parser.add_argument(
        "--max-critical-providers",
        type=int,
        default=0,
        help="Quantidade maxima tolerada de providers criticos.",
    )
    parser.add_argument(
        "--max-no-data-providers",
        type=int,
        default=0,
        help="Quantidade maxima tolerada de providers sem dados.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    with SessionLocal() as db:
        payload = build_data_quality_gate_snapshot(
            db,
            instruments=instruments if instruments else None,
            market_max_lag_seconds=args.market_max_lag_seconds,
            market_min_fresh_coverage_pct=args.market_min_fresh_coverage_pct,
            fundamentals_min_coverage_pct=args.fundamentals_min_coverage_pct,
            fundamentals_max_staleness_days=args.fundamentals_max_staleness_days,
            fundamentals_min_fresh_coverage_pct=args.fundamentals_min_fresh_coverage_pct,
            news_lookback_days=args.news_lookback_days,
            news_min_coverage_pct=args.news_min_coverage_pct,
            max_critical_providers=args.max_critical_providers,
            max_no_data_providers=args.max_no_data_providers,
        )
        if args.user_id is not None:
            event_type = (
                "data.quality.gate.pass"
                if payload["summary"]["gate_status"] == "pass"
                else "data.quality.gate.fail"
            )
            record_audit_event(
                db,
                event_type,
                {
                    "summary": payload["summary"],
                    "failed_checks": [
                        item["check_id"]
                        for item in payload["checks"]
                        if item["status"] == "fail"
                    ],
                    "scope": payload["scope"],
                },
                args.user_id,
            )

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "data_quality_gate_latest.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    summary = payload["summary"]
    print(f"Arquivo gerado: {output_path}")
    print(
        "Resumo gate: "
        f"status={summary['gate_status']} | "
        f"score={summary['quality_score_pct']:.2f}% | "
        f"checks={summary['passed_checks']}/{summary['total_checks']}"
    )


if __name__ == "__main__":
    main()

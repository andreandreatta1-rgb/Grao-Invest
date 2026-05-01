from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.db import SessionLocal
from app.services.b3_external import (
    DEFAULT_SMALL_PORTFOLIO,
    sync_b3_cotahist_portfolio,
    sync_b3_cotahist_portfolio_range,
)
from app.services.news_external import sync_external_news_period
from app.services.thesis_case_study import run_thesis_case_study
from app.services.thesis_current_monitor import run_current_thesis_monitor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline diario: sincroniza B3 (carteira pequena) e executa estudo de caso."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument("--year", type=int, default=2025, help="Ano do COTAHIST anual.")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Ano inicial opcional para sincronizacao multi-anual.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Ano final opcional para sincronizacao multi-anual.",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=10,
        help="Janela de barras para o estudo de caso.",
    )
    parser.add_argument(
        "--max-days-per-instrument",
        type=int,
        default=120,
        help="Limite de dias por ativo na sincronizacao.",
    )
    parser.add_argument(
        "--sync-news",
        action="store_true",
        help="Ativa sincronizacao de noticias reais no periodo informado.",
    )
    parser.add_argument(
        "--news-start-date",
        type=str,
        default=None,
        help="Data inicial de noticias (YYYY-MM-DD). Default: 30 dias atras.",
    )
    parser.add_argument(
        "--news-end-date",
        type=str,
        default=None,
        help="Data final de noticias (YYYY-MM-DD). Default: hoje.",
    )
    parser.add_argument(
        "--news-max-articles-per-instrument",
        type=int,
        default=80,
        help="Limite de noticias por ativo quando --sync-news estiver ativo.",
    )
    return parser.parse_args()


def _parse_date(raw: str | None, fallback: date) -> date:
    if raw is None:
        return fallback
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"Data invalida: {raw}. Use YYYY-MM-DD.") from exc


def main() -> None:
    args = parse_args()
    today = datetime.now(UTC).date()
    news_start_default = today - timedelta(days=30)
    news_start = _parse_date(args.news_start_date, news_start_default)
    news_end = _parse_date(args.news_end_date, today)
    news_payload: dict[str, object] | None = None

    with SessionLocal() as db:
        if args.start_year is not None or args.end_year is not None:
            if args.start_year is None or args.end_year is None:
                raise SystemExit("Informe start-year e end-year juntos para modo multi-anual.")
            sync_payload = sync_b3_cotahist_portfolio_range(
                db,
                user_id=args.user_id,
                start_year=args.start_year,
                end_year=args.end_year,
                instruments=DEFAULT_SMALL_PORTFOLIO,
                max_days_per_instrument_per_year=args.max_days_per_instrument,
            )
        else:
            sync_payload = sync_b3_cotahist_portfolio(
                db,
                user_id=args.user_id,
                year=args.year,
                instruments=DEFAULT_SMALL_PORTFOLIO,
                max_days_per_instrument=args.max_days_per_instrument,
            )
        if args.sync_news:
            news_payload = sync_external_news_period(
                db,
                user_id=args.user_id,
                start_date=news_start,
                end_date=news_end,
                instruments=DEFAULT_SMALL_PORTFOLIO,
                max_articles_per_instrument=args.news_max_articles_per_instrument,
            )
        case_study_payload = run_thesis_case_study(
            db,
            user_id=args.user_id,
            instruments=DEFAULT_SMALL_PORTFOLIO,
            horizon_bars=args.horizon_bars,
        )
        current_monitor_payload = run_current_thesis_monitor(
            db,
            user_id=args.user_id,
            instruments=DEFAULT_SMALL_PORTFOLIO,
            horizon_bars=args.horizon_bars,
            thesis_count=8,
            recent_bars_window=max(7, min(args.horizon_bars + 2, 20)),
        )

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "sync": sync_payload,
        "news_sync": news_payload,
        "case_study": case_study_payload,
        "current_monitor": current_monitor_payload,
    }
    output_path = data_dir / "daily_pipeline_latest.json"
    output_path.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
    monitor_path = data_dir / "current_thesis_monitor_latest.json"
    monitor_path.write_text(
        json.dumps(current_monitor_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    print(f"Arquivo gerado: {output_path}")
    print(f"Monitor diario gerado: {monitor_path}")
    print(
        "Resumo: "
        f"sync_inserted={sync_payload['sync_result']['inserted']} | "
        f"case_thesis={case_study_payload['pipeline']['selected_thesis_id']} | "
        f"current_theses={current_monitor_payload['thesis_count']}"
    )


if __name__ == "__main__":
    main()

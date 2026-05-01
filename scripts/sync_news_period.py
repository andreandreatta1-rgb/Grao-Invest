from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.db import SessionLocal
from app.services.news_external import sync_external_news_period


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza noticias reais por periodo para os instrumentos informados "
            "e injeta no pipeline de sentimento/XAI."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Data inicial no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="Data final no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        required=True,
        help="Lista de instrumentos separada por virgula (ex.: PETR4,VALE3,ITUB4).",
    )
    parser.add_argument(
        "--max-articles-per-instrument",
        type=int,
        default=80,
        help="Limite de noticias por instrumento.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="pt-BR",
        help="Idioma preferencial da busca (pt-BR/en-US).",
    )
    return parser.parse_args()


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"Data invalida: {raw}. Use formato YYYY-MM-DD.") from exc


def main() -> None:
    args = parse_args()
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    if not instruments:
        raise SystemExit("Informe ao menos um instrumento em --instruments.")

    with SessionLocal() as db:
        payload = sync_external_news_period(
            db,
            user_id=args.user_id,
            start_date=start_date,
            end_date=end_date,
            instruments=instruments,
            max_articles_per_instrument=args.max_articles_per_instrument,
            language=args.language,
        )

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "news_sync_latest.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {output_path}")
    print(
        "Resumo: "
        f"fetched={payload['fetched']} | "
        f"inserted={payload['inserted']} | "
        f"duplicates={payload['duplicates_ignored']} | "
        f"failed={payload['failed']}"
    )


if __name__ == "__main__":
    main()

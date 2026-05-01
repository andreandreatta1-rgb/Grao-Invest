from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.b3_external import (
    DEFAULT_SMALL_PORTFOLIO,
    sync_b3_cotahist_portfolio,
    sync_b3_cotahist_portfolio_range,
    sync_b3_cotahist_universe_range,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza historico COTAHIST da B3 para carteira pequena."
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario para auditoria.")
    parser.add_argument("--year", type=int, default=2025, help="Ano do arquivo anual COTAHIST.")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Ano inicial para sincronizacao multi-anual (opcional).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Ano final para sincronizacao multi-anual (opcional).",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default=",".join(DEFAULT_SMALL_PORTFOLIO),
        help="Carteira pequena (lista separada por virgula).",
    )
    parser.add_argument(
        "--full-universe",
        action="store_true",
        help="Ativa sincronizacao do universo completo elegivel da B3 (mercado a vista).",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=1500,
        help="Limite maximo de instrumentos no modo full-universe.",
    )
    parser.add_argument(
        "--allowed-bdi-codes",
        type=str,
        default="02",
        help="Codigos BDI permitidos no modo full-universe (separados por virgula).",
    )
    parser.add_argument(
        "--allowed-market-types",
        type=str,
        default="010",
        help="Tipos de mercado permitidos no modo full-universe (separados por virgula).",
    )
    parser.add_argument(
        "--max-days-per-instrument",
        type=int,
        default=120,
        help="Limite de dias por ativo para validacao de formato.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    bdi_codes = [item.strip() for item in args.allowed_bdi_codes.split(",") if item.strip()]
    market_types = [item.strip() for item in args.allowed_market_types.split(",") if item.strip()]

    with SessionLocal() as db:
        if args.full_universe:
            start_year = args.start_year or args.year
            end_year = args.end_year or args.year
            payload = sync_b3_cotahist_universe_range(
                db,
                user_id=args.user_id,
                start_year=start_year,
                end_year=end_year,
                max_days_per_instrument_per_year=args.max_days_per_instrument,
                max_instruments=args.max_instruments,
                allowed_bdi_codes=bdi_codes,
                allowed_market_types=market_types,
            )
        elif args.start_year is not None or args.end_year is not None:
            if args.start_year is None or args.end_year is None:
                raise SystemExit("Informe start-year e end-year juntos para sync multi-anual.")
            payload = sync_b3_cotahist_portfolio_range(
                db,
                user_id=args.user_id,
                start_year=args.start_year,
                end_year=args.end_year,
                instruments=instruments,
                max_days_per_instrument_per_year=args.max_days_per_instrument,
            )
        else:
            payload = sync_b3_cotahist_portfolio(
                db,
                user_id=args.user_id,
                year=args.year,
                instruments=instruments,
                max_days_per_instrument=args.max_days_per_instrument,
            )

    output_path = Path(__file__).resolve().parents[1] / "data" / "b3_sync_latest.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {output_path}")
    matched_rows = payload["format_validation"]["matched_rows"]
    print(
        "Resumo sync: "
        f"inserted={payload['sync_result']['inserted']} | "
        f"duplicates={payload['sync_result']['duplicates_ignored']} | "
        f"matched_rows={matched_rows}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.fundamentals_external import (
    fundamentals_coverage_snapshot,
    sync_external_fundamentals,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza snapshots fundamentalistas reais de fonte externa "
            "e gera relatorio de cobertura por ticker."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--provider-name",
        type=str,
        default="auto",
        help="Provider de fundamentos (auto, yahoo ou brapi).",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default=None,
        help=(
            "Lista de instrumentos separada por virgula. "
            "Se omitido, usa o universo de mercado da base."
        ),
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=600,
        help="Limite maximo de ativos por execucao.",
    )
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Inclui ativos que ja possuem fundamentos (desativa modo only_missing).",
    )
    parser.add_argument(
        "--coverage-max-rows",
        type=int,
        default=300,
        help="Limite de linhas no relatorio de cobertura.",
    )
    parser.add_argument(
        "--coverage-only-missing",
        action="store_true",
        help="No relatorio, mostra apenas ativos sem fundamento.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/fundamentals_external_sync_latest.json"),
        help="Arquivo JSON de saida.",
    )
    return parser.parse_args()


def _parse_instruments(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    instruments = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not instruments:
        raise SystemExit("Parametro --instruments informado sem ativos validos.")
    return instruments


def main() -> None:
    args = parse_args()
    instruments = _parse_instruments(args.instruments)
    only_missing = not args.include_existing

    with SessionLocal() as db:
        sync_payload = sync_external_fundamentals(
            db,
            user_id=args.user_id,
            provider_name=args.provider_name,
            instruments=instruments,
            only_missing=only_missing,
            max_instruments=args.max_instruments,
        )
        coverage_payload = fundamentals_coverage_snapshot(
            db,
            max_rows=args.coverage_max_rows,
            only_missing=args.coverage_only_missing,
        )

    output = {
        "sync": sync_payload,
        "coverage": coverage_payload,
    }
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {args.output_file}")
    print(
        "Resumo: "
        f"inserted={sync_payload['inserted']} | "
        f"duplicates={sync_payload['duplicates_ignored']} | "
        f"failed={sync_payload['failed']} | "
        f"coverage={coverage_payload['coverage_pct']}%"
    )


if __name__ == "__main__":
    main()

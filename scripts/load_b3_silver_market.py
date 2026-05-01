from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.b3_silver_loader import load_b3_silver_market_daily


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Carrega data/lake/b3/silver/market_daily.csv na tabela market_ticks "
            "para uso em treino/backtest."
        )
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="data/lake/b3/silver/market_daily.csv",
        help="Caminho do CSV silver market_daily.",
    )
    parser.add_argument(
        "--database-path",
        type=str,
        default="data/app.db",
        help="Caminho do banco SQLite da aplicacao.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="b3-cotahist-lake",
        help="Nome do provider gravado em market_ticks.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamanho do batch de insert.",
    )
    parser.add_argument(
        "--truncate-provider-before-load",
        action="store_true",
        help="Apaga os ticks existentes do provider antes da carga.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Limite de linhas para carga rapida (0 = sem limite).",
    )
    parser.add_argument(
        "--flush-max-retries",
        type=int,
        default=30,
        help="Tentativas maximas por batch quando houver lock no banco.",
    )
    return parser.parse_args()


def _resolve(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (repo_root / path)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = _resolve(repo_root, args.csv_path)
    db_path = _resolve(repo_root, args.database_path)
    max_rows = args.max_rows or None

    summary = load_b3_silver_market_daily(
        csv_path=csv_path,
        database_path=db_path,
        provider=args.provider,
        batch_size=args.batch_size,
        truncate_provider_before_load=args.truncate_provider_before_load,
        max_rows=max_rows,
        flush_max_retries=args.flush_max_retries,
    )

    output_path = repo_root / "data" / "b3_silver_load_latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary.as_dict(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    print(f"Arquivo gerado: {output_path}")
    print(
        "Resumo carga silver->market_ticks: "
        f"inserted={summary.inserted} | "
        f"duplicates={summary.duplicates_ignored} | "
        f"parse_errors={summary.parse_errors} | "
        f"rows_seen={summary.rows_seen}"
    )


if __name__ == "__main__":
    main()

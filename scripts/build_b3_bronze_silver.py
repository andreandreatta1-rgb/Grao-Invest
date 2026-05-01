from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.b3_data_lake import run_b3_bronze_silver_pipeline
from app.services.b3_external import DEFAULT_SMALL_PORTFOLIO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Constroi pipeline B3 em duas camadas: bronze (dados normalizados por origem) "
            "e silver (tabelas prontas para treino/backtest)."
        )
    )
    parser.add_argument(
        "--source-root",
        type=str,
        default="data/b3/historico_2026-04-22",
        help="Pasta de origem dos arquivos historicos B3.",
    )
    parser.add_argument(
        "--pesquisa-root",
        type=str,
        default="data/b3/pesquisa_pregao_2026-04-22",
        help="Pasta opcional do pacote pesquisa por pregao (manifesto XML).",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="data/lake/b3",
        help="Destino da data lake (bronze/silver).",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        default=",".join(DEFAULT_SMALL_PORTFOLIO),
        help="Lista de instrumentos (CSV) quando nao estiver em modo full-universe.",
    )
    parser.add_argument(
        "--full-universe",
        action="store_true",
        help="Processa todos os instrumentos encontrados no COTAHIST.",
    )
    parser.add_argument(
        "--max-rows-per-cotahist-file",
        type=int,
        default=0,
        help="Limite por arquivo COTAHIST para execucao rapida (0 = sem limite).",
    )
    return parser.parse_args()


def _resolve_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root / path


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    source_root = _resolve_path(repo_root, args.source_root)
    pesquisa_root = _resolve_path(repo_root, args.pesquisa_root)
    output_root = _resolve_path(repo_root, args.output_root)

    instruments = [
        item.strip().upper() for item in args.instruments.split(",") if item.strip()
    ]
    max_rows = args.max_rows_per_cotahist_file or None

    payload = run_b3_bronze_silver_pipeline(
        source_root=source_root,
        output_root=output_root,
        instruments=instruments,
        include_all_instruments=args.full_universe,
        max_rows_per_cotahist_file=max_rows,
        pesquisa_root=pesquisa_root if pesquisa_root.exists() else None,
    )

    summary_path = repo_root / "data" / "b3_bronze_silver_latest.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    cotahist = payload["datasets"]["cotahist"]
    cambio = payload["datasets"]["cambio"]
    renda = payload["datasets"]["renda_fixa"]
    print(f"Arquivo gerado: {summary_path}")
    print(
        "Resumo pipeline B3: "
        f"cotahist_silver_rows={cotahist['silver_rows']} | "
        f"cambio_input_files={cambio['input_files']} | "
        f"renda_fixa_silver_rows={renda['silver_rows']}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.real_estate_candidate_generation import write_strategy_territory_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera matriz de candidatos imobiliarios por estrategia e territorio, "
            "separando hipoteses de busca de sinais confirmados de condominio."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="Diretorio para gravar JSON e Markdown.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    files = write_strategy_territory_report(args.output_dir)
    print(f"JSON gerado: {files['json_file']}")
    print(f"Markdown gerado: {files['markdown_file']}")


if __name__ == "__main__":
    main()

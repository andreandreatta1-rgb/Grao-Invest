from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.schemas import FundamentalIngestRequest
from app.services.fundamentals import ingest_fundamentals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingestao em lote de snapshots fundamentalistas para analise point-in-time. "
            "Use arquivo JSON com uma lista de objetos no formato do endpoint "
            "/api/fundamentals/ingest."
        )
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        required=True,
        help="Arquivo JSON com lista de snapshots fundamentalistas.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/fundamentals_ingest_latest.json"),
        help="Arquivo de saida com resumo da ingestao.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_file.exists():
        raise SystemExit(f"Arquivo de entrada nao encontrado: {args.input_file}")

    raw_payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list):
        raise SystemExit("O arquivo deve conter uma lista JSON de snapshots.")

    ingested: list[dict[str, object]] = []
    with SessionLocal() as db:
        for row in raw_payload:
            if not isinstance(row, dict):
                raise SystemExit("Cada item da lista deve ser um objeto JSON.")
            request = FundamentalIngestRequest(**row)
            snapshot = ingest_fundamentals(db, request)
            ingested.append(
                {
                    "fundamental_id": snapshot.id,
                    "instrument": snapshot.instrument,
                    "reference_time": snapshot.reference_time,
                    "availability_time": snapshot.availability_time,
                    "version_tag": snapshot.version_tag,
                }
            )

    summary = {
        "input_file": str(args.input_file),
        "ingested_count": len(ingested),
        "snapshots": ingested,
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Resumo salvo em: {args.output_file}")
    print(f"Ingested snapshots: {len(ingested)}")


if __name__ == "__main__":
    main()

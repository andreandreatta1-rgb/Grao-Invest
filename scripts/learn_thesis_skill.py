from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.db import SessionLocal
from app.services.thesis_learning import run_thesis_skill_learning_cycle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa ciclo de aprendizado de tese: "
            "varredura -> simulacao -> avaliacao -> retroalimentacao de confianca."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--instruments",
        type=str,
        default=None,
        help=(
            "Lista de instrumentos separada por virgula. "
            "Se omitido, usa universo da base."
        ),
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=12,
        help="Janela de barras para validar cada tese.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=1500,
        help="Limite de teses historicas por ciclo.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Numero de ciclos sequenciais.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=0,
        help="Intervalo entre ciclos quando iterations > 1.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/thesis_skill_learning_latest.json"),
        help="Arquivo de saida com relatorio consolidado.",
    )
    return parser.parse_args()


def _parse_instruments(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not values:
        raise SystemExit("Parametro --instruments informado sem ativos validos.")
    return values


def main() -> None:
    args = parse_args()
    if args.iterations <= 0:
        raise SystemExit("--iterations deve ser maior que zero.")
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds nao pode ser negativo.")

    instruments = _parse_instruments(args.instruments)
    cycles: list[dict[str, object]] = []
    for index in range(args.iterations):
        with SessionLocal() as db:
            payload = run_thesis_skill_learning_cycle(
                db,
                user_id=args.user_id,
                instruments=instruments,
                horizon_bars=args.horizon_bars,
                max_candidates=args.max_candidates,
            )
        cycles.append(
            {
                "cycle": index + 1,
                "generated_at": payload["generated_at"],
                "summary": payload["summary"],
                "profile_path": payload["profile_path"],
            }
        )
        if index < args.iterations - 1 and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    output = {
        "requested": {
            "user_id": args.user_id,
            "instruments": instruments,
            "horizon_bars": args.horizon_bars,
            "max_candidates": args.max_candidates,
            "iterations": args.iterations,
            "sleep_seconds": args.sleep_seconds,
        },
        "cycles": cycles,
    }
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {args.output_file}")
    print(
        "Resumo ultimo ciclo: "
        f"success_rate={cycles[-1]['summary']['success_rate_pct']}% | "
        f"avg_conf={cycles[-1]['summary']['avg_confidence_tese_pct']}% | "
        f"blindspots={cycles[-1]['summary']['blindspot_count']}"
    )


if __name__ == "__main__":
    main()

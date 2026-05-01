from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.db import SessionLocal
from app.services.b3_external import sync_b3_cotahist_universe_range
from app.services.market import recompute_indicators


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Loop operacional para atualizacao quase real-time via COTAHIST anual atual, "
            "com recomputacao automatica de indicadores para instrumentos atualizados."
        )
    )
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="ID do usuario para trilha de auditoria.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now(UTC).year,
        help="Ano COTAHIST para polling incremental.",
    )
    parser.add_argument(
        "--max-days-per-instrument",
        type=int,
        default=5,
        help="Quantidade de dias por instrumento a considerar por ciclo.",
    )
    parser.add_argument(
        "--max-instruments",
        type=int,
        default=1500,
        help="Limite maximo de instrumentos elegiveis por ciclo.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=900,
        help="Intervalo entre ciclos em segundos (default: 15 min).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Quantidade de ciclos (use 0 para loop continuo).",
    )
    return parser.parse_args()


def _run_cycle(args: argparse.Namespace) -> dict[str, object]:
    with SessionLocal() as db:
        sync_payload = sync_b3_cotahist_universe_range(
            db,
            user_id=args.user_id,
            start_year=args.year,
            end_year=args.year,
            max_days_per_instrument_per_year=args.max_days_per_instrument,
            max_instruments=args.max_instruments,
            allowed_bdi_codes=["02"],
            allowed_market_types=["010"],
        )
        touched_instruments = [
            instrument
            for instrument, qty in sync_payload["sync_result"]["ingested_by_instrument"].items()
            if qty > 0
        ]
        indicator_recomputed = 0
        indicator_warmup = 0
        for instrument in touched_instruments:
            try:
                recompute_indicators(db, instrument)
                indicator_recomputed += 1
            except ValueError:
                indicator_warmup += 1

    return {
        "cycle_time": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "sync": sync_payload,
        "algorithm_update": {
            "touched_instruments": len(touched_instruments),
            "indicator_recomputed": indicator_recomputed,
            "indicator_warmup": indicator_warmup,
        },
    }


def main() -> None:
    args = parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("poll-seconds deve ser maior que zero.")
    if args.iterations < 0:
        raise SystemExit("iterations deve ser >= 0.")

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "realtime_b3_latest.json"

    cycle = 0
    while True:
        cycle += 1
        payload = _run_cycle(args)
        payload["cycle_index"] = cycle
        output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        print(f"[cycle={cycle}] atualizado: {output_path}")
        print(
            "Resumo: "
            f"inserted={payload['sync']['sync_result']['inserted']} | "
            f"recomputed={payload['algorithm_update']['indicator_recomputed']} | "
            f"warmup={payload['algorithm_update']['indicator_warmup']}"
        )
        if args.iterations != 0 and cycle >= args.iterations:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()

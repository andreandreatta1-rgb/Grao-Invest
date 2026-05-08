from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.db import DATA_DIR, SessionLocal
from app.models import MarketTick
from app.services.b3_external import sync_b3_cotahist_portfolio
from app.services.crypto_history_provider import (
    CryptoHistoryProviderError,
    fetch_historical_crypto_candles,
)
from app.services.market import recompute_indicators
from app.services.thesis_current_by_front_job import (
    DEFAULT_B3_INSTRUMENTS,
    DEFAULT_CRYPTO_INSTRUMENTS,
)
from app.services.utils import isoformat, utc_now
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Atualiza feeds de mercado antes do gerador de teses: B3 via COTAHIST "
            "e Cripto via candles historicas."
        )
    )
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--skip-b3", action="store_true")
    parser.add_argument("--skip-crypto", action="store_true")
    parser.add_argument("--b3-year", type=int, default=datetime.now(UTC).year)
    parser.add_argument("--b3-instruments", type=str, default=",".join(DEFAULT_B3_INSTRUMENTS))
    parser.add_argument("--b3-max-days-per-instrument", type=int, default=10)
    parser.add_argument("--crypto-provider", type=str, default="binance")
    parser.add_argument(
        "--crypto-instruments",
        type=str,
        default=",".join(DEFAULT_CRYPTO_INSTRUMENTS),
    )
    parser.add_argument("--crypto-interval", type=str, default="5m")
    parser.add_argument("--crypto-lookback-hours", type=int, default=72)
    parser.add_argument("--crypto-max-candles-per-instrument", type=int, default=1200)
    parser.add_argument("--skip-indicators", action="store_true")
    return parser.parse_args()


def csv_items(raw: str) -> list[str]:
    return list(dict.fromkeys(item.strip().upper() for item in raw.split(",") if item.strip()))


def _latest_event_time(db: Session, *, provider: str, instruments: list[str]) -> str | None:
    if not instruments:
        return None
    return db.scalar(
        select(MarketTick.event_time)
        .where(MarketTick.provider == provider.lower())
        .where(MarketTick.instrument.in_(instruments))
        .order_by(MarketTick.event_time.desc())
        .limit(1)
    )


def refresh_b3_cotahist(
    db: Session,
    *,
    user_id: int,
    year: int,
    instruments: list[str],
    max_days_per_instrument: int,
    auto_recompute_indicators: bool,
) -> dict[str, object]:
    payload = sync_b3_cotahist_portfolio(
        db,
        user_id=user_id,
        year=year,
        instruments=instruments,
        max_days_per_instrument=max_days_per_instrument,
    )
    sync_result = payload["sync_result"]
    touched = [
        instrument
        for instrument, count in sync_result["ingested_by_instrument"].items()
        if int(count or 0) > 0
    ]
    recomputed: list[str] = []
    skipped: list[str] = []
    if auto_recompute_indicators:
        for instrument in touched:
            try:
                recompute_indicators(db, instrument)
                recomputed.append(instrument)
            except ValueError:
                skipped.append(instrument)
    return {
        "status": "ok",
        "provider": payload["provider"],
        "year": year,
        "requested_instruments": instruments,
        "inserted": int(sync_result["inserted"]),
        "duplicates_ignored": int(sync_result["duplicates_ignored"]),
        "latest_event_time": _latest_event_time(
            db,
            provider=str(payload["provider"]),
            instruments=instruments,
        ),
        "indicator_recomputed": recomputed,
        "indicator_skipped": skipped,
    }


def refresh_crypto_history(
    db: Session,
    *,
    provider_name: str,
    instruments: list[str],
    interval: str,
    lookback_hours: int,
    max_candles_per_instrument: int,
    auto_recompute_indicators: bool,
) -> dict[str, object]:
    end_time = utc_now()
    start_time = end_time - timedelta(hours=lookback_hours)
    candles = fetch_historical_crypto_candles(
        provider_name,
        instruments,
        interval,
        start_time=start_time,
        end_time=end_time,
        max_candles_per_instrument=max_candles_per_instrument,
    )
    provider_label = f"crypto-{provider_name.lower()}-{interval}".lower()
    payload_ids = [
        str(candle["source_payload_id"])
        for candle in candles
        if candle.get("source_payload_id") is not None
    ]
    existing_ids = set(
        db.scalars(
            select(MarketTick.source_payload_id).where(
                MarketTick.provider == provider_label,
                MarketTick.instrument.in_(instruments),
                MarketTick.source_payload_id.in_(payload_ids),
            )
        )
    )
    ingest_time = isoformat(utc_now())
    rows: list[MarketTick] = []
    duplicates = 0
    touched: set[str] = set()
    for candle in candles:
        instrument = str(candle["instrument"]).upper()
        source_payload_id = str(candle["source_payload_id"])
        touched.add(instrument)
        if source_payload_id in existing_ids:
            duplicates += 1
            continue
        rows.append(
            MarketTick(
                instrument=instrument,
                provider=provider_label,
                event_time=isoformat(candle["event_time"]),
                ingest_time=ingest_time,
                price=float(candle["price"]),
                volume=int(candle["volume"]),
                currency=str(candle["currency"]),
                source_payload_id=source_payload_id,
            )
        )
    if rows:
        db.add_all(rows)
        db.commit()

    recomputed: list[str] = []
    skipped: list[str] = []
    if auto_recompute_indicators:
        for instrument in sorted(touched):
            try:
                recompute_indicators(db, instrument)
                recomputed.append(instrument)
            except ValueError:
                skipped.append(instrument)

    return {
        "status": "ok",
        "provider": provider_label,
        "interval": interval,
        "lookback_hours": lookback_hours,
        "requested_instruments": instruments,
        "requested_candles": len(candles),
        "inserted": len(rows),
        "duplicates_ignored": duplicates,
        "latest_event_time": _latest_event_time(
            db,
            provider=provider_label,
            instruments=instruments,
        ),
        "indicator_recomputed": recomputed,
        "indicator_skipped": skipped,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Market Feed Refresh",
        "",
        f"- `generated_at`: {payload.get('generated_at')}",
        f"- `status`: {payload.get('status')}",
        "",
        "## Fronts",
    ]
    fronts = payload.get("fronts") if isinstance(payload.get("fronts"), dict) else {}
    for name, front in fronts.items():
        if not isinstance(front, dict):
            continue
        lines.extend(
            [
                "",
                f"### {name}",
                f"- `status`: {front.get('status')}",
                f"- `provider`: {front.get('provider')}",
                f"- `inserted`: {front.get('inserted', 0)}",
                f"- `duplicates_ignored`: {front.get('duplicates_ignored', 0)}",
                f"- `latest_event_time`: {front.get('latest_event_time')}",
            ]
        )
        if front.get("error"):
            lines.append(f"- `error`: {front.get('error')}")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    fronts: dict[str, object] = {}
    with SessionLocal() as db:
        if args.skip_b3:
            fronts["b3"] = {"status": "skipped", "message": "Refresh B3 ignorado."}
        else:
            try:
                fronts["b3"] = refresh_b3_cotahist(
                    db,
                    user_id=args.user_id,
                    year=args.b3_year,
                    instruments=csv_items(args.b3_instruments),
                    max_days_per_instrument=args.b3_max_days_per_instrument,
                    auto_recompute_indicators=not args.skip_indicators,
                )
            except Exception as exc:
                fronts["b3"] = {"status": "failed", "error": str(exc)}

        if args.skip_crypto:
            fronts["crypto"] = {"status": "skipped", "message": "Refresh Cripto ignorado."}
        else:
            try:
                fronts["crypto"] = refresh_crypto_history(
                    db,
                    provider_name=args.crypto_provider,
                    instruments=csv_items(args.crypto_instruments),
                    interval=args.crypto_interval,
                    lookback_hours=args.crypto_lookback_hours,
                    max_candles_per_instrument=args.crypto_max_candles_per_instrument,
                    auto_recompute_indicators=not args.skip_indicators,
                )
            except CryptoHistoryProviderError as exc:
                fronts["crypto"] = {
                    "status": "failed",
                    "error": str(exc),
                    "detail": exc.to_detail(),
                }
            except Exception as exc:
                fronts["crypto"] = {"status": "failed", "error": str(exc)}

    statuses = [str(front.get("status")) for front in fronts.values() if isinstance(front, dict)]
    status = "ok" if statuses and all(item in {"ok", "skipped"} for item in statuses) else "warning"
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": status,
        "fronts": fronts,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "market_feed_refresh_latest.json"
    md_path = DATA_DIR / "market_feed_refresh_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    print(f"Arquivo gerado: {json_path}")
    print(f"Arquivo gerado: {md_path}")
    print(f"Market feed refresh: status={status}")


if __name__ == "__main__":
    main()

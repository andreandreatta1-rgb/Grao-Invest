from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.db import SessionLocal
from app.schemas import MarketTickIngestRequest
from app.services.intraday_provider import fetch_intraday_quotes
from app.services.market import ingest_tick_live


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Worker intraday real para ingestao de cotacoes via API (REST) ou WebSocket, "
            "com atualizacao automatica do algoritmo."
        )
    )
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="ID do usuario de referencia operacional.",
    )
    parser.add_argument(
        "--provider-name",
        type=str,
        default="finnhub",
        help="Provider intraday real (finnhub).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="rest",
        choices=["rest", "ws"],
        help="Modo do worker.",
    )
    parser.add_argument(
        "--instruments",
        type=str,
        required=True,
        help="Lista de instrumentos separada por virgula (ex.: PETR4,VALE3).",
    )
    parser.add_argument(
        "--symbol-overrides",
        type=str,
        default="",
        help="Overrides instrument:symbol separados por virgula (ex.: PETR4:BVMF:PETR4).",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=120,
        help="Duracao do stream em modo ws.",
    )
    parser.add_argument(
        "--auto-recompute-indicators",
        action="store_true",
        help="Ativa recomputacao imediata dos indicadores durante a ingestao live.",
    )
    return parser.parse_args()


def _parse_symbol_overrides(raw: str) -> dict[str, str] | None:
    cleaned = [item.strip() for item in raw.split(",") if item.strip()]
    if not cleaned:
        return None
    mapping: dict[str, str] = {}
    for item in cleaned:
        if ":" not in item:
            raise SystemExit(f"Override invalido: {item}. Formato esperado instrument:symbol.")
        instrument, symbol = item.split(":", 1)
        if not instrument.strip() or not symbol.strip():
            raise SystemExit(f"Override invalido: {item}.")
        mapping[instrument.strip().upper()] = symbol.strip()
    return mapping


def _persist_worker_output(payload: dict[str, object]) -> Path:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "intraday_worker_latest.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return output_path


def _run_rest_mode(
    *,
    provider_name: str,
    instruments: list[str],
    symbol_overrides: dict[str, str] | None,
    auto_recompute_indicators: bool,
) -> dict[str, object]:
    quotes = fetch_intraday_quotes(provider_name, instruments, symbol_overrides)
    processed: list[dict[str, object]] = []
    with SessionLocal() as db:
        for quote in quotes:
            result = ingest_tick_live(
                db,
                MarketTickIngestRequest(
                    instrument=quote["instrument"],
                    provider=f"intraday-{provider_name}",
                    event_time=quote["event_time"],
                    price=quote["price"],
                    volume=quote["volume"],
                    currency=quote["currency"],
                    source_payload_id=quote["source_payload_id"],
                ),
                auto_recompute_indicators=auto_recompute_indicators,
            )
            processed.append(
                {
                    "instrument": quote["instrument"],
                    "provider_symbol": quote["provider_symbol"],
                    "market_tick": result["market_tick"],
                    "algorithm_update": result["algorithm_update"],
                }
            )
    return {
        "mode": "rest",
        "provider_name": provider_name,
        "processed_count": len(processed),
        "processed": processed,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


async def _run_finnhub_ws_mode(
    *,
    instruments: list[str],
    symbol_overrides: dict[str, str] | None,
    duration_seconds: int,
    auto_recompute_indicators: bool,
) -> dict[str, object]:
    token = os.getenv("FINNHUB_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("FINNHUB_API_TOKEN nao configurado para modo websocket.")
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "Pacote 'websockets' nao encontrado. Instale com: python -m pip install websockets"
        ) from exc

    instrument_symbols = {
        instrument.upper(): (
            symbol_overrides.get(instrument.upper())  # type: ignore[union-attr]
            if symbol_overrides is not None and instrument.upper() in symbol_overrides
            else f"BVMF:{instrument.upper()}"
        )
        for instrument in instruments
    }
    symbol_to_instrument = {symbol: instrument for instrument, symbol in instrument_symbols.items()}
    received = 0
    processed = 0
    started_at = datetime.now(UTC)

    uri = f"wss://ws.finnhub.io?token={token}"
    with SessionLocal() as db:
        async with websockets.connect(uri, open_timeout=20, close_timeout=10) as websocket:
            for symbol in instrument_symbols.values():
                await websocket.send(json.dumps({"type": "subscribe", "symbol": symbol}))

            while (datetime.now(UTC) - started_at).total_seconds() < float(duration_seconds):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                except TimeoutError:
                    continue
                if not isinstance(message, str):
                    continue
                payload = json.loads(message)
                if payload.get("type") != "trade":
                    continue
                trades = payload.get("data")
                if not isinstance(trades, list):
                    continue
                received += len(trades)
                for trade in trades:
                    if not isinstance(trade, dict):
                        continue
                    provider_symbol = str(trade.get("s", "")).strip()
                    instrument = symbol_to_instrument.get(provider_symbol)
                    if instrument is None:
                        continue
                    try:
                        trade_price = float(trade["p"])
                        trade_timestamp_ms = int(trade["t"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if trade_price <= 0:
                        continue
                    trade_volume_raw = trade.get("v")
                    trade_volume = (
                        int(trade_volume_raw)
                        if isinstance(trade_volume_raw, (int, float)) and trade_volume_raw > 0
                        else 0
                    )
                    event_time = datetime.fromtimestamp(trade_timestamp_ms / 1000, tz=UTC)
                    source_payload_id = f"finnhub-ws:{provider_symbol}:{trade_timestamp_ms}"
                    ingest_tick_live(
                        db,
                        MarketTickIngestRequest(
                            instrument=instrument,
                            provider="intraday-finnhub-ws",
                            event_time=event_time,
                            price=trade_price,
                            volume=trade_volume,
                            currency="BRL",
                            source_payload_id=source_payload_id,
                        ),
                        auto_recompute_indicators=auto_recompute_indicators,
                    )
                    processed += 1

    return {
        "mode": "ws",
        "provider_name": "finnhub",
        "received_trades": received,
        "processed_trades": processed,
        "duration_seconds": duration_seconds,
        "started_at": started_at.replace(microsecond=0).isoformat(),
        "finished_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    if not instruments:
        raise SystemExit("Informe ao menos um instrumento.")
    symbol_overrides = _parse_symbol_overrides(args.symbol_overrides)

    if args.mode == "rest":
        payload = _run_rest_mode(
            provider_name=args.provider_name,
            instruments=instruments,
            symbol_overrides=symbol_overrides,
            auto_recompute_indicators=args.auto_recompute_indicators,
        )
    else:
        if args.provider_name.lower() != "finnhub":
            raise SystemExit("Modo websocket atualmente suportado apenas para provider finnhub.")
        payload = asyncio.run(
            _run_finnhub_ws_mode(
                instruments=instruments,
                symbol_overrides=symbol_overrides,
                duration_seconds=args.duration_seconds,
                auto_recompute_indicators=args.auto_recompute_indicators,
            )
        )

    payload["user_id"] = args.user_id
    output_path = _persist_worker_output(payload)
    print(f"Worker output: {output_path}")
    if args.mode == "rest":
        print(f"processed_count={payload['processed_count']}")
    else:
        print(
            f"received={payload['received_trades']} | "
            f"processed={payload['processed_trades']}"
        )


if __name__ == "__main__":
    main()

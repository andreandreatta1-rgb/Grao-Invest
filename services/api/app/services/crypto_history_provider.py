from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class CryptoHistoryCandle(TypedDict):
    instrument: str
    provider_symbol: str
    provider_name: str
    interval: str
    event_time: datetime
    price: float
    volume: int
    currency: str
    source_payload_id: str


class CryptoHistoryProviderError(ValueError):
    pass


_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
_ALLOWED_INTERVALS_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}


def _normalize_symbol(raw: str) -> str:
    return "".join(char for char in raw.strip().upper() if char.isalnum())


def _normalize_provider_symbol(raw: str) -> str:
    candidate = raw.strip().upper()
    if ":" in candidate:
        candidate = candidate.split(":")[-1]
    normalized = _normalize_symbol(candidate)
    if not normalized:
        raise CryptoHistoryProviderError("Symbol override vazio ou invalido.")
    return normalized


def _currency_for_symbol(symbol: str) -> str:
    upper_symbol = symbol.upper()
    for suffix in ("USDT", "USDC", "FDUSD", "BUSD", "BTC", "ETH", "BNB", "EUR", "BRL"):
        if upper_symbol.endswith(suffix):
            return suffix
    return "USD"


def _symbol_for_provider(instrument: str, symbol_overrides: dict[str, str] | None) -> str:
    normalized_instrument = _normalize_symbol(instrument)
    if not normalized_instrument:
        raise CryptoHistoryProviderError("Instrumento cripto invalido.")

    if symbol_overrides:
        normalized_overrides = {
            _normalize_symbol(key): _normalize_provider_symbol(value)
            for key, value in symbol_overrides.items()
        }
        if normalized_instrument in normalized_overrides:
            return normalized_overrides[normalized_instrument]

    # Common user shorthand: BTCUSD -> BTCUSDT.
    if normalized_instrument.endswith("USD") and not normalized_instrument.endswith("USDT"):
        return f"{normalized_instrument}T"
    return normalized_instrument


def _to_float(value: object, field_name: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise CryptoHistoryProviderError(
                f"Campo '{field_name}' invalido no provider de historico."
            ) from exc
    raise CryptoHistoryProviderError(f"Campo '{field_name}' ausente no provider de historico.")


def _to_int(value: object, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError as exc:
            raise CryptoHistoryProviderError(
                f"Campo '{field_name}' invalido no provider de historico."
            ) from exc
    raise CryptoHistoryProviderError(f"Campo '{field_name}' ausente no provider de historico.")


def _binance_klines_request(
    *,
    symbol: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: int,
    limit: int,
) -> list[list[object]]:
    params = urlencode(
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms,
            "limit": limit,
        }
    )
    url = f"{_BINANCE_KLINES_URL}?{params}"
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Binance para {symbol}: {exc}"
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CryptoHistoryProviderError("Binance retornou payload nao-JSON.") from exc

    if isinstance(parsed, dict):
        message = parsed.get("msg") or parsed.get("message") or str(parsed)
        raise CryptoHistoryProviderError(f"Binance retornou erro para {symbol}: {message}")
    if not isinstance(parsed, list):
        raise CryptoHistoryProviderError("Binance retornou payload invalido para klines.")
    rows = [row for row in parsed if isinstance(row, list)]
    return rows


def _parse_binance_candle(
    row: list[object],
    *,
    instrument: str,
    provider_symbol: str,
    interval: str,
) -> CryptoHistoryCandle:
    if len(row) < 7:
        raise CryptoHistoryProviderError("Linha de kline Binance com estrutura invalida.")
    open_time_ms = _to_int(row[0], "openTime")
    close_price = _to_float(row[4], "close")
    close_time_ms = _to_int(row[6], "closeTime")
    base_volume = _to_float(row[5], "volume")
    if close_price <= 0:
        raise CryptoHistoryProviderError("Preco de fechamento invalido no historico Binance.")
    volume = int(max(0.0, base_volume))
    event_time = datetime.fromtimestamp(close_time_ms / 1000, tz=UTC)
    source_payload_id = f"bnc:{provider_symbol}:{interval}:{open_time_ms}"
    return {
        "instrument": _normalize_symbol(instrument),
        "provider_symbol": provider_symbol,
        "provider_name": "binance",
        "interval": interval,
        "event_time": event_time,
        "price": round(close_price, 8),
        "volume": volume,
        "currency": _currency_for_symbol(provider_symbol),
        "source_payload_id": source_payload_id[:64],
    }


def _fetch_binance_candles_for_instrument(
    *,
    instrument: str,
    provider_symbol: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
    max_candles: int,
) -> list[CryptoHistoryCandle]:
    start_ms = int(start_time.astimezone(UTC).timestamp() * 1000)
    end_ms = int(end_time.astimezone(UTC).timestamp() * 1000)
    interval_ms = _ALLOWED_INTERVALS_SECONDS[interval] * 1000
    cursor = start_ms
    collected: list[CryptoHistoryCandle] = []

    while cursor < end_ms and len(collected) < max_candles:
        remaining = max_candles - len(collected)
        limit = min(1000, remaining)
        rows = _binance_klines_request(
            symbol=provider_symbol,
            interval=interval,
            start_time_ms=cursor,
            end_time_ms=end_ms,
            limit=limit,
        )
        if not rows:
            break

        for row in rows:
            candle = _parse_binance_candle(
                row,
                instrument=instrument,
                provider_symbol=provider_symbol,
                interval=interval,
            )
            if candle["event_time"] < start_time:
                continue
            if candle["event_time"] > end_time:
                continue
            collected.append(candle)
            if len(collected) >= max_candles:
                break

        try:
            last_open_time = _to_int(rows[-1][0], "openTime")
        except CryptoHistoryProviderError:
            break
        next_cursor = last_open_time + interval_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(rows) < limit:
            break

    return collected


def fetch_historical_crypto_candles(
    provider_name: str,
    instruments: list[str],
    interval: str,
    start_time: datetime,
    end_time: datetime,
    *,
    symbol_overrides: dict[str, str] | None = None,
    max_candles_per_instrument: int = 1500,
) -> list[CryptoHistoryCandle]:
    provider = provider_name.strip().lower()
    if provider != "binance":
        raise CryptoHistoryProviderError(
            "Provider de historico cripto nao suportado. Use 'binance'."
        )
    normalized_interval = interval.strip()
    if normalized_interval not in _ALLOWED_INTERVALS_SECONDS:
        raise CryptoHistoryProviderError(
            "Intervalo invalido. Use 1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h ou 1d."
        )
    if end_time <= start_time:
        raise CryptoHistoryProviderError("Janela de tempo invalida para backfill historico.")
    if max_candles_per_instrument <= 0:
        raise CryptoHistoryProviderError("max_candles_per_instrument deve ser positivo.")

    unique_instruments = list(dict.fromkeys(item.upper().strip() for item in instruments if item.strip()))
    if not unique_instruments:
        raise CryptoHistoryProviderError("Informe ao menos um instrumento para historico cripto.")

    output: list[CryptoHistoryCandle] = []
    for instrument in unique_instruments:
        provider_symbol = _symbol_for_provider(instrument, symbol_overrides)
        candles = _fetch_binance_candles_for_instrument(
            instrument=instrument,
            provider_symbol=provider_symbol,
            interval=normalized_interval,
            start_time=start_time,
            end_time=end_time,
            max_candles=max_candles_per_instrument,
        )
        output.extend(candles)
    output.sort(key=lambda item: (item["instrument"], item["event_time"]))
    return output

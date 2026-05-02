from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from urllib.error import HTTPError
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
    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        provider_name: str | None = None,
        user_message: str | None = None,
        retryable: bool = False,
        safe_to_continue: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_name = provider_name
        self.user_message = user_message or message
        self.retryable = retryable
        self.safe_to_continue = safe_to_continue

    def to_detail(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": str(self),
            "user_message": self.user_message,
            "provider_name": self.provider_name,
            "retryable": self.retryable,
            "safe_to_continue": self.safe_to_continue,
        }


_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
_COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/{product_id}/candles"
_REGION_BLOCKED_USER_MESSAGE = (
    "Fonte historica cripto indisponivel por restricao regional. "
    "Nenhuma nova operacao deve ser avaliada ate haver dados suficientes."
)
_PROVIDER_UNAVAILABLE_USER_MESSAGE = (
    "Fonte historica cripto temporariamente indisponivel. "
    "Nenhuma nova operacao deve ser avaliada ate haver dados suficientes."
)
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
_COINBASE_SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "6h", "1d"}
_KNOWN_QUOTES = ("USDT", "USDC", "FDUSD", "BUSD", "BTC", "ETH", "BNB", "EUR", "BRL", "USD")


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
    for suffix in _KNOWN_QUOTES:
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


def _split_base_quote(symbol: str) -> tuple[str, str]:
    normalized_symbol = _normalize_symbol(symbol)
    for quote in _KNOWN_QUOTES:
        if normalized_symbol.endswith(quote) and len(normalized_symbol) > len(quote):
            return normalized_symbol[: -len(quote)], quote
    raise CryptoHistoryProviderError(f"Par cripto invalido ou sem quote reconhecida: {symbol}")


def _coinbase_product_id_for_symbol(symbol: str) -> str:
    base, quote = _split_base_quote(symbol)
    normalized_quote = "USD" if quote in {"USDT", "USDC", "FDUSD", "BUSD"} else quote
    if normalized_quote == "BRL":
        normalized_quote = "USD"
    return f"{base}-{normalized_quote}"


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
    except HTTPError as exc:
        if exc.code == 451:
            raise CryptoHistoryProviderError(
                f"Falha ao consultar historico Binance para {symbol}: HTTP 451",
                code="provider_region_blocked",
                provider_name="binance",
                user_message=_REGION_BLOCKED_USER_MESSAGE,
                retryable=True,
                safe_to_continue=False,
            ) from exc
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Binance para {symbol}: HTTP {exc.code}",
            code="provider_unavailable",
            provider_name="binance",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        ) from exc
    except TimeoutError as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Binance para {symbol}: timeout",
            code="provider_unavailable",
            provider_name="binance",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        ) from exc
    except Exception as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Binance para {symbol}: {exc}",
            code="provider_unavailable",
            provider_name="binance",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
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


def _coinbase_candles_request(
    *,
    product_id: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
) -> list[list[object]]:
    granularity = _ALLOWED_INTERVALS_SECONDS[interval]
    params = urlencode(
        {
            "granularity": granularity,
            "start": start_time.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "end": end_time.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
    )
    url = _COINBASE_CANDLES_URL.format(product_id=product_id) + f"?{params}"
    request = Request(
        url,
        headers={
            "User-Agent": "AI-Investment-Advisor-MVP/0.1",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Coinbase para {product_id}: HTTP {exc.code}",
            code="provider_unavailable",
            provider_name="coinbase",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        ) from exc
    except TimeoutError as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Coinbase para {product_id}: timeout",
            code="provider_unavailable",
            provider_name="coinbase",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        ) from exc
    except Exception as exc:
        raise CryptoHistoryProviderError(
            f"Falha ao consultar historico Coinbase para {product_id}: {exc}",
            code="provider_unavailable",
            provider_name="coinbase",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CryptoHistoryProviderError("Coinbase retornou payload nao-JSON.") from exc

    if isinstance(parsed, dict):
        message = parsed.get("message") or str(parsed)
        raise CryptoHistoryProviderError(
            f"Coinbase retornou erro para {product_id}: {message}",
            code="provider_unavailable",
            provider_name="coinbase",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=True,
            safe_to_continue=False,
        )
    if not isinstance(parsed, list):
        raise CryptoHistoryProviderError("Coinbase retornou payload invalido para candles.")
    return [row for row in parsed if isinstance(row, list)]


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


def _parse_coinbase_candle(
    row: list[object],
    *,
    instrument: str,
    provider_symbol: str,
    interval: str,
) -> CryptoHistoryCandle:
    if len(row) < 6:
        raise CryptoHistoryProviderError("Linha de candle Coinbase com estrutura invalida.")
    bucket_start = _to_int(row[0], "time")
    close_price = _to_float(row[4], "close")
    base_volume = _to_float(row[5], "volume")
    if close_price <= 0:
        raise CryptoHistoryProviderError("Preco de fechamento invalido no historico Coinbase.")
    event_time = datetime.fromtimestamp(bucket_start + _ALLOWED_INTERVALS_SECONDS[interval], tz=UTC)
    volume = int(max(0.0, base_volume))
    source_payload_id = f"cb:{provider_symbol}:{interval}:{bucket_start}"
    return {
        "instrument": _normalize_symbol(instrument),
        "provider_symbol": provider_symbol,
        "provider_name": "coinbase",
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


def _fetch_coinbase_candles_for_instrument(
    *,
    instrument: str,
    provider_symbol: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
    max_candles: int,
) -> list[CryptoHistoryCandle]:
    if interval not in _COINBASE_SUPPORTED_INTERVALS:
        raise CryptoHistoryProviderError(
            f"Intervalo {interval} nao suportado pelo fallback Coinbase.",
            code="provider_unsupported_interval",
            provider_name="coinbase",
            user_message=_PROVIDER_UNAVAILABLE_USER_MESSAGE,
            retryable=False,
            safe_to_continue=False,
        )

    product_id = _coinbase_product_id_for_symbol(provider_symbol)
    interval_seconds = _ALLOWED_INTERVALS_SECONDS[interval]
    max_window_seconds = interval_seconds * 300
    cursor = start_time.astimezone(UTC)
    normalized_end = end_time.astimezone(UTC)
    collected: dict[str, CryptoHistoryCandle] = {}

    while cursor < normalized_end and len(collected) < max_candles:
        window_end = min(normalized_end, cursor + timedelta(seconds=max_window_seconds))
        rows = _coinbase_candles_request(
            product_id=product_id,
            interval=interval,
            start_time=cursor,
            end_time=window_end,
        )
        for row in rows:
            candle = _parse_coinbase_candle(
                row,
                instrument=instrument,
                provider_symbol=product_id,
                interval=interval,
            )
            if candle["event_time"] < start_time:
                continue
            if candle["event_time"] > end_time:
                continue
            collected[candle["source_payload_id"]] = candle
            if len(collected) >= max_candles:
                break
        cursor = datetime.fromtimestamp(window_end.timestamp() + interval_seconds, tz=UTC)

    output = sorted(collected.values(), key=lambda item: item["event_time"])
    return output[:max_candles]


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
    if provider not in {"binance", "coinbase"}:
        raise CryptoHistoryProviderError(
            "Provider de historico cripto nao suportado. Use 'binance' ou 'coinbase'."
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

    unique_instruments = list(
        dict.fromkeys(item.upper().strip() for item in instruments if item.strip())
    )
    if not unique_instruments:
        raise CryptoHistoryProviderError("Informe ao menos um instrumento para historico cripto.")

    output: list[CryptoHistoryCandle] = []
    for instrument in unique_instruments:
        provider_symbol = _symbol_for_provider(instrument, symbol_overrides)
        try:
            if provider == "coinbase":
                candles = _fetch_coinbase_candles_for_instrument(
                    instrument=instrument,
                    provider_symbol=provider_symbol,
                    interval=normalized_interval,
                    start_time=start_time,
                    end_time=end_time,
                    max_candles=max_candles_per_instrument,
                )
            else:
                candles = _fetch_binance_candles_for_instrument(
                    instrument=instrument,
                    provider_symbol=provider_symbol,
                    interval=normalized_interval,
                    start_time=start_time,
                    end_time=end_time,
                    max_candles=max_candles_per_instrument,
                )
        except CryptoHistoryProviderError as exc:
            if provider != "binance" or exc.code not in {"provider_region_blocked", "provider_unavailable"}:
                raise
            candles = _fetch_coinbase_candles_for_instrument(
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

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class IntradayQuote(TypedDict):
    instrument: str
    provider_symbol: str
    provider_name: str
    event_time: datetime
    price: float
    volume: int
    currency: str
    source_payload_id: str


class IntradayProviderError(ValueError):
    pass


def _to_float(value: object, field_name: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise IntradayProviderError(
                f"Campo '{field_name}' invalido no provider intraday."
            ) from exc
    raise IntradayProviderError(f"Campo '{field_name}' ausente no provider intraday.")


def _to_int(value: object, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError as exc:
            raise IntradayProviderError(
                f"Campo '{field_name}' invalido no provider intraday."
            ) from exc
    raise IntradayProviderError(f"Campo '{field_name}' ausente no provider intraday.")


def _symbol_for_provider(instrument: str, symbol_overrides: dict[str, str] | None) -> str:
    key = instrument.upper()
    if symbol_overrides and key in symbol_overrides:
        return symbol_overrides[key]
    return f"BVMF:{key}"


def _parse_finnhub_quote(
    payload: dict[str, object],
    instrument: str,
    provider_symbol: str,
) -> IntradayQuote:
    try:
        price = _to_float(payload.get("c"), "c")
        event_epoch = _to_int(payload.get("t"), "t")
    except (KeyError, TypeError, ValueError) as exc:
        raise IntradayProviderError(
            f"Resposta invalida para {provider_symbol} no provider finnhub."
        ) from exc
    if price <= 0:
        raise IntradayProviderError(
            f"Preco invalido retornado para {provider_symbol} no provider finnhub."
        )
    event_time = datetime.fromtimestamp(event_epoch, tz=UTC)
    volume_raw = payload.get("v")
    volume = int(volume_raw) if isinstance(volume_raw, (int, float)) and volume_raw > 0 else 0
    source_payload_id = f"finnhub:{provider_symbol}:{event_epoch}"
    return {
        "instrument": instrument.upper(),
        "provider_symbol": provider_symbol,
        "provider_name": "finnhub",
        "event_time": event_time,
        "price": round(price, 6),
        "volume": volume,
        "currency": "BRL",
        "source_payload_id": source_payload_id,
    }


def _finnhub_quote_request(provider_symbol: str, api_token: str) -> dict[str, object]:
    params = urlencode({"symbol": provider_symbol, "token": api_token})
    url = f"https://finnhub.io/api/v1/quote?{params}"
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise IntradayProviderError(f"Falha ao consultar provider finnhub: {exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise IntradayProviderError("Provider finnhub retornou payload nao-JSON.") from exc
    if not isinstance(parsed, dict):
        raise IntradayProviderError("Provider finnhub retornou payload invalido.")
    return parsed


def fetch_intraday_quotes(
    provider_name: str,
    instruments: list[str],
    symbol_overrides: dict[str, str] | None = None,
) -> list[IntradayQuote]:
    provider = provider_name.lower().strip()
    quotes: list[IntradayQuote] = []
    unique_instruments = list(dict.fromkeys(item.upper() for item in instruments))

    if provider != "finnhub":
        raise IntradayProviderError(
            "Provider intraday nao suportado. Use 'finnhub' para integracao real-time."
        )

    token = os.getenv("FINNHUB_API_TOKEN", "").strip()
    if not token:
        raise IntradayProviderError(
            "FINNHUB_API_TOKEN nao configurado para ingestao intraday real."
        )
    for instrument in unique_instruments:
        provider_symbol = _symbol_for_provider(instrument, symbol_overrides)
        payload = _finnhub_quote_request(provider_symbol, token)
        quote = _parse_finnhub_quote(payload, instrument, provider_symbol)
        quotes.append(quote)
    return quotes

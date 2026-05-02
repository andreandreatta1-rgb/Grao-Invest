from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from urllib.error import HTTPError

import pytest
from app.services import crypto_history_provider
from app.services.crypto_history_provider import (
    CryptoHistoryProviderError,
    fetch_historical_crypto_candles,
)


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_binance_region_block_falls_back_to_coinbase(monkeypatch) -> None:
    def fallback_urlopen(request: object, *args: object, **kwargs: object) -> object:
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "binance.com" in url:
            raise HTTPError(
                url="https://api.binance.com/api/v3/klines",
                code=451,
                msg="Unavailable For Legal Reasons",
                hdrs=None,
                fp=BytesIO(b'{"msg":"Service unavailable from a restricted location"}'),
            )
        if "api.exchange.coinbase.com" in url:
            return _FakeResponse(b"[[1714644000,62000,63000,62100,62850,12.5]]")
        raise AssertionError(url)

    monkeypatch.setattr(crypto_history_provider, "urlopen", fallback_urlopen)

    candles = fetch_historical_crypto_candles(
        "binance",
        ["BTCUSDT"],
        "5m",
        datetime(2024, 5, 2, 10, 0, tzinfo=UTC),
        datetime(2024, 5, 2, 11, 0, tzinfo=UTC),
        max_candles_per_instrument=50,
    )

    assert len(candles) == 1
    assert candles[0]["provider_name"] == "coinbase"
    assert candles[0]["provider_symbol"] == "BTC-USD"
    assert candles[0]["instrument"] == "BTCUSDT"


def test_binance_request_timeout_is_classified_as_provider_unavailable(monkeypatch) -> None:
    def timeout_urlopen(request: object, *args: object, **kwargs: object) -> object:
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "binance.com" in url:
            raise TimeoutError("timed out")
        if "api.exchange.coinbase.com" in url:
            raise HTTPError(
                url=url,
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=BytesIO(b'{"message":"unavailable"}'),
            )
        raise AssertionError(url)

    monkeypatch.setattr(crypto_history_provider, "urlopen", timeout_urlopen)

    with pytest.raises(CryptoHistoryProviderError) as exc_info:
        fetch_historical_crypto_candles(
            "binance",
            ["ETHUSDT"],
            "5m",
            datetime.now(UTC) - timedelta(hours=1),
            datetime.now(UTC),
            max_candles_per_instrument=50,
        )

    error = exc_info.value
    assert error.code == "provider_unavailable"
    assert error.provider_name == "coinbase"
    assert error.retryable is True
    assert error.to_detail()["safe_to_continue"] is False

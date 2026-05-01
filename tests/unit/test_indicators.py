from __future__ import annotations

from app.services.indicators import ema, macd, momentum, rsi, sma, volatility


def test_indicator_calculations() -> None:
    series = [
        35.1,
        35.4,
        35.6,
        35.5,
        35.8,
        36.0,
        36.2,
        36.4,
        36.5,
        36.7,
        36.9,
        37.1,
        37.2,
        37.4,
        37.6,
    ]
    assert round(sma(series, 5), 2) == 37.24
    assert round(ema(series, 5), 2) == 37.24
    assert round(rsi(series, 14), 2) > 80
    assert round(volatility(series, 10), 4) > 0
    assert round(momentum(series, 5), 2) == 0.90
    extended_series = series + [37.8, 38.0, 38.2, 38.4, 38.6, 38.8, 39.0, 39.2, 39.4, 39.6, 39.8]
    assert round(macd(extended_series), 4) > 0

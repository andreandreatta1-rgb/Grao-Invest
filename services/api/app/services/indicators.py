from __future__ import annotations

from math import sqrt
from statistics import mean


def sma(values: list[float], window: int) -> float:
    if len(values) < window:
        raise ValueError("Serie insuficiente para SMA")
    return mean(values[-window:])


def ema(values: list[float], window: int) -> float:
    if len(values) < window:
        raise ValueError("Serie insuficiente para EMA")
    multiplier = 2 / (window + 1)
    ema_value = mean(values[:window])
    for value in values[window:]:
        ema_value = ((value - ema_value) * multiplier) + ema_value
    return ema_value


def rsi(values: list[float], window: int = 14) -> float:
    if len(values) <= window:
        raise ValueError("Serie insuficiente para RSI")
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[-(window + 1):], values[-window:], strict=False):
        delta = current - previous
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))
    average_gain = mean(gains)
    average_loss = mean(losses)
    if average_loss == 0:
        return 100.0
    rs = average_gain / average_loss
    return 100 - (100 / (1 + rs))


def volatility(values: list[float], window: int) -> float:
    if len(values) < window:
        raise ValueError("Serie insuficiente para volatilidade")
    sample = values[-window:]
    avg = mean(sample)
    variance = sum((value - avg) ** 2 for value in sample) / len(sample)
    return sqrt(variance)


def momentum(values: list[float], window: int) -> float:
    if len(values) <= window:
        raise ValueError("Serie insuficiente para momentum")
    return values[-1] - values[-(window + 1)]


def macd(values: list[float]) -> float:
    if len(values) < 26:
        raise ValueError("Serie insuficiente para MACD")
    return ema(values, 12) - ema(values, 26)

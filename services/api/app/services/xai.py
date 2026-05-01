from __future__ import annotations

from app.models import FundamentalSnapshot, IndicatorSnapshot
from app.services.fundamentals import summarize_fundamental_quality
from app.services.news import SentimentAggregate
from app.services.utils import to_json


def build_signal_xai_payload(
    snapshot: IndicatorSnapshot,
    signal_type: str,
    confidence: float,
    anti_hype_score: float,
    fundamentals: FundamentalSnapshot | None = None,
    sentiment_context: SentimentAggregate | None = None,
) -> str:
    top_features = [
        {"name": "sma_gap_5_10", "value": round(snapshot.sma_5 - snapshot.sma_10, 4)},
        {"name": "sma_gap_10_20", "value": round(snapshot.sma_10 - snapshot.sma_20, 4)},
        {"name": "ema_gap_12_26", "value": round(snapshot.ema_12 - snapshot.ema_26, 4)},
        {"name": "rsi_14", "value": round(snapshot.rsi_14, 4)},
        {"name": "macd", "value": round(snapshot.macd, 4)},
        {"name": "momentum_5", "value": round(snapshot.momentum_5, 4)},
        {"name": "volatility_10", "value": round(snapshot.volatility_10, 4)},
    ]
    fundamentals_summary: dict[str, float] | None = None
    if fundamentals is not None:
        fundamentals_summary = summarize_fundamental_quality(fundamentals)
        top_features.extend(
            [
                {"name": "pe_ratio", "value": round(fundamentals.pe_ratio, 4)},
                {"name": "roe", "value": round(fundamentals.roe, 4)},
                {"name": "revenue_growth", "value": round(fundamentals.revenue_growth, 4)},
                {"name": "dividend_yield", "value": round(fundamentals.dividend_yield, 4)},
            ]
        )
    if sentiment_context is not None:
        top_features.extend(
            [
                {
                    "name": "weighted_sentiment",
                    "value": round(float(sentiment_context["weighted_sentiment"]), 4),
                },
                {
                    "name": "average_magnitude",
                    "value": round(float(sentiment_context["average_magnitude"]), 4),
                },
            ]
        )
    payload = {
        "signal_type": signal_type,
        "confidence": confidence,
        "anti_hype_score": anti_hype_score,
        "top_features": top_features,
        "fundamentals": (
            {
                "available": True,
                "value_score": fundamentals_summary["value_score"],
                "quality_score": fundamentals_summary["quality_score"],
                "reference_time": fundamentals.reference_time,
                "availability_time": fundamentals.availability_time,
            }
            if fundamentals is not None and fundamentals_summary is not None
            else {"available": False}
        ),
        "sentiment": sentiment_context or {"available": False},
        "explanation": (
            "O motor combina tendencia, momentum, volatilidade, fundamentos point-in-time, "
            "sentimento agregado por noticia e score anti-hype para produzir "
            "cenarios descritivos compativeis com simulacao."
        ),
    }
    return to_json(payload)

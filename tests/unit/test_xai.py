from __future__ import annotations

import json

from app.models import FundamentalSnapshot, IndicatorSnapshot
from app.services.xai import build_signal_xai_payload


def test_build_signal_xai_payload() -> None:
    snapshot = IndicatorSnapshot(
        instrument="PETR4",
        reference_time="2026-04-20T12:00:00+00:00",
        availability_time="2026-04-20T12:00:00+00:00",
        sma_5=37.4,
        sma_10=36.8,
        sma_20=35.9,
        ema_5=37.3,
        ema_12=37.2,
        ema_26=36.6,
        rsi_14=61.2,
        volatility_10=0.45,
        momentum_5=0.7,
        macd=0.6,
    )
    payload = json.loads(build_signal_xai_payload(snapshot, "bullish_setup", 0.66, 72.0))
    assert payload["signal_type"] == "bullish_setup"
    assert payload["top_features"][0]["name"] == "sma_gap_5_10"
    assert payload["anti_hype_score"] == 72.0


def test_build_signal_xai_payload_with_fundamentals() -> None:
    snapshot = IndicatorSnapshot(
        instrument="PETR4",
        reference_time="2026-04-20T12:00:00+00:00",
        availability_time="2026-04-20T12:00:00+00:00",
        sma_5=37.4,
        sma_10=36.8,
        sma_20=35.9,
        ema_5=37.3,
        ema_12=37.2,
        ema_26=36.6,
        rsi_14=61.2,
        volatility_10=0.45,
        momentum_5=0.7,
        macd=0.6,
    )
    fundamentals = FundamentalSnapshot(
        instrument="PETR4",
        source_name="CVM",
        source_type="regulatory",
        reference_time="2026-03-31T00:00:00+00:00",
        availability_time="2026-05-15T00:00:00+00:00",
        pe_ratio=10.2,
        pb_ratio=1.7,
        ev_ebitda=7.0,
        dividend_yield=5.4,
        roe=16.5,
        net_margin=12.8,
        revenue_growth=9.3,
        payout_ratio=41.0,
        version_tag="itr-2026q1-v1",
    )
    payload = json.loads(
        build_signal_xai_payload(
            snapshot,
            "bullish_setup",
            0.7,
            74.0,
            fundamentals,
            {
                "available": True,
                "instrument": "PETR4",
                "sector": "energia",
                "article_count": 3,
                "weighted_sentiment": 0.44,
                "average_magnitude": 0.58,
                "average_confidence": 0.82,
                "sentiment_bias": "positive",
            },
        )
    )
    assert payload["fundamentals"]["available"] is True
    assert payload["fundamentals"]["quality_score"] > 0
    assert any(feature["name"] == "pe_ratio" for feature in payload["top_features"])
    assert payload["sentiment"]["sentiment_bias"] == "positive"
    assert any(feature["name"] == "weighted_sentiment" for feature in payload["top_features"])

from __future__ import annotations

from statistics import mean

from app.models import FundamentalSnapshot, IndicatorSnapshot, Signal
from app.services.alerts import maybe_emit_signal_alerts
from app.services.audit import record_audit_event
from app.services.fundamentals import summarize_fundamental_quality
from app.services.news import SentimentAggregate, aggregate_sentiment_as_of, latest_news_as_of
from app.services.point_in_time import latest_fundamentals_as_of, latest_indicator_as_of
from app.services.utils import (
    DISCLAIMER,
    anti_recommendation_text,
    assert_compliant_copy,
    isoformat,
    utc_now,
)
from app.services.xai import build_signal_xai_payload
from sqlalchemy import select
from sqlalchemy.orm import Session


def evaluate_signal_context(
    snapshot: IndicatorSnapshot,
    instrument: str,
    anti_hype_score: float,
    fundamentals: FundamentalSnapshot | None = None,
    sentiment_context: SentimentAggregate | None = None,
) -> tuple[str, float, str]:
    instrument_name = instrument.upper()
    trend_score = 0.0
    mean_reversion_score = 0.0

    if snapshot.sma_5 > snapshot.sma_10:
        trend_score += 0.18
    if snapshot.sma_10 > snapshot.sma_20:
        trend_score += 0.16
    if snapshot.ema_12 > snapshot.ema_26:
        trend_score += 0.16
    if snapshot.macd > 0:
        trend_score += 0.12
    if snapshot.momentum_5 > 0:
        trend_score += 0.10
    if snapshot.rsi_14 < 68:
        trend_score += 0.08

    if snapshot.rsi_14 > 70:
        mean_reversion_score += 0.18
    if snapshot.momentum_5 < 0:
        mean_reversion_score += 0.14
    if snapshot.macd < 0:
        mean_reversion_score += 0.14
    if snapshot.sma_5 < snapshot.sma_10:
        mean_reversion_score += 0.16
    if snapshot.ema_12 < snapshot.ema_26:
        mean_reversion_score += 0.16

    if fundamentals is not None:
        fundamental_scores = summarize_fundamental_quality(fundamentals)
        trend_score += min(0.14, fundamental_scores["quality_score"] * 0.5)
        trend_score += min(0.12, fundamental_scores["value_score"] * 0.45)
        if fundamentals.roe < 0 or fundamentals.net_margin < 0:
            mean_reversion_score += 0.1
        if fundamentals.revenue_growth < 0:
            mean_reversion_score += 0.08

    if sentiment_context is not None and int(sentiment_context["article_count"]) > 0:
        weighted_sentiment = float(sentiment_context["weighted_sentiment"])
        avg_magnitude = float(sentiment_context["average_magnitude"])
        avg_confidence = float(sentiment_context["average_confidence"])
        if weighted_sentiment > 0.2:
            trend_score += min(0.12, weighted_sentiment * 0.18 + avg_confidence * 0.05)
        elif weighted_sentiment < -0.2:
            mean_reversion_score += min(0.14, abs(weighted_sentiment) * 0.18 + avg_magnitude * 0.06)

    if trend_score >= mean_reversion_score and trend_score >= 0.54:
        signal_type = "bullish_setup"
        confidence = min(0.95, 0.5 + trend_score)
        rationale = (
            f"Cenario multi-fator favoravel em {instrument_name}, "
            f"com tendencia positiva e RSI em {snapshot.rsi_14:.2f}. "
        )
    elif mean_reversion_score > trend_score and mean_reversion_score >= 0.5:
        signal_type = "mean_reversion_watch"
        confidence = min(0.9, 0.46 + mean_reversion_score)
        rationale = (
            f"Cenario de vigilancia para reversao ou defesa em {instrument_name}, "
            f"com enfraquecimento de momentum e RSI em {snapshot.rsi_14:.2f}. "
        )
    else:
        signal_type = "defensive_setup"
        confidence = 0.55
        rationale = (
            f"Cenario de cautela para {instrument_name}, "
            "com momentum menos favoravel no recorte atual. "
        )
    if fundamentals is not None:
        fundamental_scores = summarize_fundamental_quality(fundamentals)
        rationale += (
            "Os fundamentos point-in-time acrescentam "
            f"qualidade {fundamental_scores['quality_score']:.2f} e "
            f"valor relativo {fundamental_scores['value_score']:.2f}. "
        )
    if sentiment_context is not None and int(sentiment_context["article_count"]) > 0:
        rationale += (
            "O sentimento agregado das noticias aponta vies "
            f"{sentiment_context['sentiment_bias']} com intensidade "
            f"{float(sentiment_context['weighted_sentiment']):.2f}. "
        )
    if anti_hype_score < 40:
        signal_type = "defensive_setup"
        confidence = min(confidence, 0.56)
        rationale = (
            rationale
            + " O fluxo de noticias recente apresenta baixa credibilidade "
            + "e foi despriorizado pelo motor."
        )
    rationale += DISCLAIMER
    rationale = anti_recommendation_text(rationale)
    assert_compliant_copy(rationale)
    return signal_type, round(confidence, 4), rationale


def generate_signal(db: Session, user_id: int, instrument: str) -> Signal:
    as_of = utc_now()
    snapshot = latest_indicator_as_of(db, instrument.upper(), as_of)
    if snapshot is None:
        raise ValueError("Nao ha indicadores disponiveis para este ativo")
    recent_news = latest_news_as_of(db, instrument.upper(), as_of)
    fundamentals = latest_fundamentals_as_of(db, instrument.upper(), as_of)
    sentiment_context = aggregate_sentiment_as_of(db, instrument.upper(), as_of)
    anti_hype_score = (
        round(mean(article.anti_hype_score for article in recent_news), 2)
        if recent_news
        else 75.0
    )
    signal_type, confidence, rationale = evaluate_signal_context(
        snapshot,
        instrument,
        anti_hype_score,
        fundamentals,
        sentiment_context,
    )
    superseded_at = isoformat(as_of)
    previous_signals = list(
        db.scalars(
            select(Signal)
            .where(Signal.user_id == user_id)
            .where(Signal.instrument == instrument.upper())
            .where(Signal.signal_status == "active")
        )
    )
    for previous in previous_signals:
        previous.signal_status = "expired"
        previous.expires_at = superseded_at
        previous.expiry_reason = "superseded_by_new_signal"

    signal = Signal(
        user_id=user_id,
        instrument=instrument.upper(),
        reference_time=snapshot.reference_time,
        availability_time=isoformat(as_of),
        signal_type=signal_type,
        confidence=confidence,
        rationale=rationale,
        anti_hype_score=anti_hype_score,
        xai_payload=build_signal_xai_payload(
            snapshot,
            signal_type,
            confidence,
            anti_hype_score,
            fundamentals,
            sentiment_context,
        ),
        signal_status="active",
        expires_at=None,
        expiry_reason=None,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    maybe_emit_signal_alerts(db, signal)
    record_audit_event(
        db,
        "signal.generated",
        {"instrument": signal.instrument, "signal_type": signal.signal_type},
        user_id,
    )
    return signal

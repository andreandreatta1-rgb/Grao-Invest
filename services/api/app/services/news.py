from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from app.models import NewsAnalysisSnapshot, NewsArticle
from app.schemas import NewsIngestRequest
from app.services.alerts import maybe_emit_news_alerts
from app.services.audit import record_audit_event
from app.services.point_in_time import news_analysis_as_of
from app.services.utils import isoformat, utc_now
from sqlalchemy import select
from sqlalchemy.orm import Session

SENSATIONAL_TERMS = [
    "dispara",
    "explosao",
    "imperdivel",
    "garantido",
    "segredo",
    "multiplique",
    "enriqueca",
    "ultima chance",
]

SOURCE_CREDIBILITY = {
    "official": 0.95,
    "regulated_media": 0.8,
    "financial_media": 0.75,
    "community": 0.45,
    "social": 0.3,
}

SECTOR_BY_INSTRUMENT = {
    "PETR4": "energia",
    "VALE3": "mineracao",
    "ITUB4": "financeiro",
    "BBDC4": "financeiro",
}

POSITIVE_TERMS = [
    "aprova",
    "cresce",
    "lucro",
    "recorde",
    "expande",
    "dividend",
    "supera",
    "guidance positivo",
]

NEGATIVE_TERMS = [
    "queda",
    "prejuizo",
    "investigacao",
    "risco",
    "dela",
    "rebaixa",
    "cai",
    "multa",
]

HIGH_MAGNITUDE_TERMS = [
    "fato relevante",
    "guidance",
    "fusao",
    "aquisicao",
    "resultado",
    "dividend",
    "provento",
    "investigacao",
]


class NewsClassification(TypedDict):
    sector: str
    theme: str
    sentiment_label: str
    sentiment_score: float
    magnitude_score: float
    model_confidence: float


class SentimentAggregate(TypedDict):
    instrument: str
    sector: str
    article_count: int
    weighted_sentiment: float
    average_magnitude: float
    average_confidence: float
    sentiment_bias: str


class SourceCredibilityAggregate(TypedDict):
    source_name: str
    source_type: str
    article_count: int
    average_credibility: float
    average_anti_hype: float
    average_magnitude: float
    weighted_sentiment: float
    latest_published_at: str
    latest_captured_at: str


class SourceCredibilityAccumulator(TypedDict):
    source_name: str
    source_type: str
    article_count: int
    sum_credibility: float
    sum_anti_hype: float
    sum_magnitude: float
    weighted_sentiment_sum: float
    weight_sum: float
    latest_published_at: str
    latest_captured_at: str


def compute_anti_hype_score(headline: str, source_type: str) -> tuple[float, float]:
    lower_headline = headline.lower()
    penalty = sum(12 for term in SENSATIONAL_TERMS if term in lower_headline)
    credibility = SOURCE_CREDIBILITY.get(source_type, 0.5)
    base_score = max(5.0, 100.0 - penalty)
    anti_hype = round(base_score * credibility, 2)
    return round(credibility * 100, 2), anti_hype


def classify_news(
    instrument: str,
    headline: str,
    source_type: str,
) -> NewsClassification:
    lower_headline = headline.lower()
    positive_hits = sum(1 for term in POSITIVE_TERMS if term in lower_headline)
    negative_hits = sum(1 for term in NEGATIVE_TERMS if term in lower_headline)
    high_magnitude_hits = sum(1 for term in HIGH_MAGNITUDE_TERMS if term in lower_headline)

    if positive_hits > negative_hits:
        sentiment_label = "positive"
        sentiment_score = min(1.0, 0.55 + positive_hits * 0.12)
    elif negative_hits > positive_hits:
        sentiment_label = "negative"
        sentiment_score = max(-1.0, -0.55 - negative_hits * 0.12)
    else:
        sentiment_label = "neutral"
        sentiment_score = 0.0

    if "dividend" in lower_headline or "provento" in lower_headline:
        theme = "proventos"
    elif "guidance" in lower_headline or "resultado" in lower_headline:
        theme = "resultados"
    elif "investig" in lower_headline or "multa" in lower_headline:
        theme = "compliance"
    else:
        theme = "corporativo"

    base_confidence = SOURCE_CREDIBILITY.get(source_type, 0.5)
    model_confidence = round(
        min(0.98, 0.45 + base_confidence * 0.4 + high_magnitude_hits * 0.05),
        4,
    )
    magnitude_score = round(
        min(1.0, 0.25 + high_magnitude_hits * 0.18 + abs(sentiment_score) * 0.25),
        4,
    )
    return {
        "sector": SECTOR_BY_INSTRUMENT.get(instrument.upper(), "diversificado"),
        "theme": theme,
        "sentiment_label": sentiment_label,
        "sentiment_score": round(sentiment_score, 4),
        "magnitude_score": magnitude_score,
        "model_confidence": model_confidence,
    }


def ingest_news(db: Session, payload: NewsIngestRequest) -> NewsArticle:
    credibility_score, anti_hype_score = compute_anti_hype_score(
        payload.headline,
        payload.source_type,
    )
    classified = classify_news(payload.instrument, payload.headline, payload.source_type)
    article = NewsArticle(
        instrument=payload.instrument.upper(),
        headline=payload.headline,
        source_name=payload.source_name,
        source_type=payload.source_type,
        credibility_score=credibility_score,
        anti_hype_score=anti_hype_score,
        published_at=isoformat(payload.published_at),
        captured_at=isoformat(utc_now()),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    analysis = NewsAnalysisSnapshot(
        news_article_id=article.id,
        instrument=article.instrument,
        sector=str(classified["sector"]),
        theme=str(classified["theme"]),
        sentiment_label=str(classified["sentiment_label"]),
        sentiment_score=float(classified["sentiment_score"]),
        magnitude_score=float(classified["magnitude_score"]),
        model_confidence=float(classified["model_confidence"]),
        source_url=payload.source_url,
        language=payload.language,
        # For historical backfills, availability must follow economic publication time.
        # This keeps point-in-time simulations realistic and avoids "late ingest" blind spots.
        availability_time=isoformat(payload.published_at),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    maybe_emit_news_alerts(db, article, analysis)
    record_audit_event(
        db,
        "news.article.ingested",
        {
            "instrument": article.instrument,
            "source_type": article.source_type,
            "anti_hype_score": article.anti_hype_score,
            "sentiment_label": analysis.sentiment_label,
            "magnitude_score": analysis.magnitude_score,
        },
    )
    return article


def latest_news_as_of(db: Session, instrument: str, as_of: datetime) -> list[NewsArticle]:
    statement = (
        select(NewsArticle)
        .where(NewsArticle.instrument == instrument.upper())
        .where(NewsArticle.published_at <= as_of.isoformat())
        .order_by(NewsArticle.published_at.desc())
        .limit(5)
    )
    return list(db.scalars(statement))


def source_credibility_history_as_of(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> list[SourceCredibilityAggregate]:
    statement = (
        select(NewsArticle, NewsAnalysisSnapshot)
        .join(
            NewsAnalysisSnapshot,
            NewsAnalysisSnapshot.news_article_id == NewsArticle.id,
        )
        .where(NewsArticle.instrument == instrument.upper())
        .where(NewsArticle.published_at <= as_of.isoformat())
        .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
    )
    rows = list(db.execute(statement).all())
    if not rows:
        return []

    grouped: dict[str, SourceCredibilityAccumulator] = {}
    for article, analysis in rows:
        key = f"{article.source_name}::{article.source_type}"
        if key not in grouped:
            grouped[key] = {
                "source_name": article.source_name,
                "source_type": article.source_type,
                "article_count": 0,
                "sum_credibility": 0.0,
                "sum_anti_hype": 0.0,
                "sum_magnitude": 0.0,
                "weighted_sentiment_sum": 0.0,
                "weight_sum": 0.0,
                "latest_published_at": article.published_at,
                "latest_captured_at": article.captured_at,
            }

        entry = grouped[key]
        entry["article_count"] += 1
        entry["sum_credibility"] += article.credibility_score
        entry["sum_anti_hype"] += article.anti_hype_score
        entry["sum_magnitude"] += analysis.magnitude_score
        weight = max(0.1, analysis.model_confidence * max(analysis.magnitude_score, 0.1))
        entry["weighted_sentiment_sum"] += analysis.sentiment_score * weight
        entry["weight_sum"] += weight
        if article.published_at > entry["latest_published_at"]:
            entry["latest_published_at"] = article.published_at
        if article.captured_at > entry["latest_captured_at"]:
            entry["latest_captured_at"] = article.captured_at

    aggregates: list[SourceCredibilityAggregate] = []
    for entry in grouped.values():
        article_count = entry["article_count"]
        weighted_sentiment = 0.0
        if entry["weight_sum"] > 0:
            weighted_sentiment = entry["weighted_sentiment_sum"] / entry["weight_sum"]
        aggregates.append(
            {
                "source_name": entry["source_name"],
                "source_type": entry["source_type"],
                "article_count": article_count,
                "average_credibility": round(entry["sum_credibility"] / article_count, 4),
                "average_anti_hype": round(entry["sum_anti_hype"] / article_count, 4),
                "average_magnitude": round(entry["sum_magnitude"] / article_count, 4),
                "weighted_sentiment": round(weighted_sentiment, 4),
                "latest_published_at": entry["latest_published_at"],
                "latest_captured_at": entry["latest_captured_at"],
            }
        )
    aggregates.sort(
        key=lambda item: (
            -item["average_credibility"],
            -item["article_count"],
            item["source_name"],
        )
    )
    return aggregates


def aggregate_sentiment_as_of(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> SentimentAggregate:
    analyses = news_analysis_as_of(db, instrument, as_of)
    if not analyses:
        return {
            "instrument": instrument.upper(),
            "sector": SECTOR_BY_INSTRUMENT.get(instrument.upper(), "diversificado"),
            "article_count": 0,
            "weighted_sentiment": 0.0,
            "average_magnitude": 0.0,
            "average_confidence": 0.0,
            "sentiment_bias": "neutral",
        }

    weights = [item.model_confidence * max(item.magnitude_score, 0.1) for item in analyses]
    total_weight = sum(weights)
    weighted_sentiment = (
        sum(item.sentiment_score * weight for item, weight in zip(analyses, weights, strict=False))
        / total_weight
    )
    average_magnitude = sum(item.magnitude_score for item in analyses) / len(analyses)
    average_confidence = sum(item.model_confidence for item in analyses) / len(analyses)
    if weighted_sentiment > 0.2:
        sentiment_bias = "positive"
    elif weighted_sentiment < -0.2:
        sentiment_bias = "negative"
    else:
        sentiment_bias = "neutral"
    return {
        "instrument": instrument.upper(),
        "sector": analyses[0].sector,
        "article_count": len(analyses),
        "weighted_sentiment": round(weighted_sentiment, 4),
        "average_magnitude": round(average_magnitude, 4),
        "average_confidence": round(average_confidence, 4),
        "sentiment_bias": sentiment_bias,
    }

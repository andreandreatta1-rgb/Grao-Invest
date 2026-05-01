from __future__ import annotations

from datetime import datetime

from app.models import (
    FundamentalSnapshot,
    IndicatorSnapshot,
    MarketTick,
    NewsAnalysisSnapshot,
    NewsArticle,
)
from sqlalchemy import Select, select
from sqlalchemy.orm import Session


def ticks_as_of(db: Session, instrument: str, as_of: datetime) -> list[MarketTick]:
    statement = (
        select(MarketTick)
        .where(MarketTick.instrument == instrument)
        .where(MarketTick.event_time <= as_of.isoformat())
        .order_by(MarketTick.event_time.asc())
    )
    return list(db.scalars(statement))


def latest_indicator_as_of(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> IndicatorSnapshot | None:
    statement = (
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.instrument == instrument)
        .where(IndicatorSnapshot.availability_time <= as_of.isoformat())
        .order_by(IndicatorSnapshot.availability_time.desc())
        .limit(1)
    )
    return db.scalar(statement)


def latest_fundamentals_as_of(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> FundamentalSnapshot | None:
    statement = (
        select(FundamentalSnapshot)
        .where(FundamentalSnapshot.instrument == instrument)
        .where(FundamentalSnapshot.availability_time <= as_of.isoformat())
        .order_by(FundamentalSnapshot.availability_time.desc(), FundamentalSnapshot.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def news_analysis_as_of(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> list[NewsAnalysisSnapshot]:
    as_of_iso = as_of.isoformat()
    statement: Select[tuple[NewsAnalysisSnapshot]] = (
        select(NewsAnalysisSnapshot)
        .join(NewsArticle, NewsArticle.id == NewsAnalysisSnapshot.news_article_id)
        .where(NewsAnalysisSnapshot.instrument == instrument.upper())
        .where(NewsArticle.published_at <= as_of_iso)
        .order_by(NewsArticle.published_at.desc(), NewsAnalysisSnapshot.id.desc())
        .limit(10)
    )
    return list(db.scalars(statement))

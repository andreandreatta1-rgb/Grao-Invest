from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db import Base
from app.models import (
    FundamentalSnapshot,
    IndicatorSnapshot,
    MarketTick,
    NewsAnalysisSnapshot,
    NewsArticle,
)
from app.services.point_in_time import (
    latest_fundamentals_as_of,
    latest_indicator_as_of,
    news_analysis_as_of,
    ticks_as_of,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def test_point_in_time_helpers_use_cutoff() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        db.add(
            MarketTick(
                instrument="PETR4",
                provider="demo",
                event_time=(base_time - timedelta(minutes=2)).isoformat(),
                ingest_time=(base_time - timedelta(minutes=2)).isoformat(),
                price=10.0,
                volume=100,
                currency="BRL",
                source_payload_id="a",
            )
        )
        db.add(
            MarketTick(
                instrument="PETR4",
                provider="demo",
                event_time=(base_time + timedelta(minutes=2)).isoformat(),
                ingest_time=(base_time + timedelta(minutes=2)).isoformat(),
                price=20.0,
                volume=200,
                currency="BRL",
                source_payload_id="b",
            )
        )
        db.add(
            IndicatorSnapshot(
                instrument="PETR4",
                reference_time=base_time.isoformat(),
                availability_time=(base_time - timedelta(minutes=1)).isoformat(),
                sma_5=10,
                sma_10=9,
                ema_5=10,
                rsi_14=60,
            )
        )
        db.add(
            IndicatorSnapshot(
                instrument="PETR4",
                reference_time=base_time.isoformat(),
                availability_time=(base_time + timedelta(minutes=1)).isoformat(),
                sma_5=20,
                sma_10=19,
                ema_5=20,
                rsi_14=65,
            )
        )
        db.add(
            FundamentalSnapshot(
                instrument="PETR4",
                source_name="CVM",
                source_type="regulatory",
                reference_time=(base_time - timedelta(days=30)).isoformat(),
                availability_time=(base_time - timedelta(hours=2)).isoformat(),
                pe_ratio=9.0,
                pb_ratio=1.4,
                ev_ebitda=6.5,
                dividend_yield=6.2,
                roe=18.0,
                net_margin=14.0,
                revenue_growth=9.0,
                payout_ratio=42.0,
                version_tag="itr-2026q1-v1",
            )
        )
        db.add(
            FundamentalSnapshot(
                instrument="PETR4",
                source_name="CVM",
                source_type="regulatory",
                reference_time=(base_time - timedelta(days=5)).isoformat(),
                availability_time=(base_time + timedelta(hours=2)).isoformat(),
                pe_ratio=20.0,
                pb_ratio=4.2,
                ev_ebitda=14.0,
                dividend_yield=1.0,
                roe=6.0,
                net_margin=3.0,
                revenue_growth=-2.0,
                payout_ratio=10.0,
                version_tag="itr-2026q2-v1",
            )
        )
        old_article = NewsArticle(
            instrument="PETR4",
            headline="Petrobras aprova dividendo ordinario",
            source_name="CVM",
            source_type="official",
            credibility_score=95.0,
            anti_hype_score=95.0,
            published_at=(base_time - timedelta(minutes=30)).isoformat(),
            captured_at=(base_time - timedelta(minutes=29)).isoformat(),
        )
        future_article = NewsArticle(
            instrument="PETR4",
            headline="Petrobras sofre investigacao adicional",
            source_name="Portal X",
            source_type="social",
            credibility_score=30.0,
            anti_hype_score=28.0,
            published_at=(base_time + timedelta(minutes=30)).isoformat(),
            captured_at=(base_time + timedelta(minutes=31)).isoformat(),
        )
        db.add(old_article)
        db.add(future_article)
        db.flush()
        db.add(
            NewsAnalysisSnapshot(
                news_article_id=old_article.id,
                instrument="PETR4",
                sector="energia",
                theme="proventos",
                sentiment_label="positive",
                sentiment_score=0.7,
                magnitude_score=0.6,
                model_confidence=0.85,
                source_url="https://example.com/old",
                language="pt-BR",
                availability_time=(base_time - timedelta(minutes=29)).isoformat(),
            )
        )
        db.add(
            NewsAnalysisSnapshot(
                news_article_id=future_article.id,
                instrument="PETR4",
                sector="energia",
                theme="compliance",
                sentiment_label="negative",
                sentiment_score=-0.8,
                magnitude_score=0.7,
                model_confidence=0.7,
                source_url="https://example.com/future",
                language="pt-BR",
                availability_time=(base_time + timedelta(minutes=31)).isoformat(),
            )
        )
        db.commit()

        ticks = ticks_as_of(db, "PETR4", base_time)
        assert len(ticks) == 1
        assert ticks[0].price == 10.0

        snapshot = latest_indicator_as_of(db, "PETR4", base_time)
        assert snapshot is not None
        assert snapshot.sma_5 == 10

        fundamentals = latest_fundamentals_as_of(db, "PETR4", base_time)
        assert fundamentals is not None
        assert fundamentals.version_tag == "itr-2026q1-v1"

        analyses = news_analysis_as_of(db, "PETR4", base_time)
        assert len(analyses) == 1
        assert analyses[0].sentiment_label == "positive"
    finally:
        db.close()


def test_news_analysis_as_of_uses_published_time_for_backfilled_news() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        base_time = datetime(2026, 3, 6, 12, 0, tzinfo=UTC)
        article = NewsArticle(
            instrument="PETR4",
            headline="Tensao no Golfo pressiona logistica de petroleo",
            source_name="InvesTalk",
            source_type="financial_media",
            credibility_score=75.0,
            anti_hype_score=75.0,
            published_at=(base_time - timedelta(hours=3)).isoformat(),
            captured_at=(base_time + timedelta(days=40)).isoformat(),
        )
        db.add(article)
        db.flush()
        db.add(
            NewsAnalysisSnapshot(
                news_article_id=article.id,
                instrument="PETR4",
                sector="energia",
                theme="corporativo",
                sentiment_label="negative",
                sentiment_score=-0.45,
                magnitude_score=0.7,
                model_confidence=0.8,
                source_url="https://example.com/backfill",
                language="pt-BR",
                availability_time=(base_time + timedelta(days=40)).isoformat(),
            )
        )
        db.commit()

        analyses = news_analysis_as_of(db, "PETR4", base_time)
        assert len(analyses) == 1
        assert analyses[0].sentiment_label == "negative"
    finally:
        db.close()

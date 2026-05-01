from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db import Base
from app.models import NewsAnalysisSnapshot, NewsArticle
from app.services.thesis_case_study import _geopolitical_oil_support_pct
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def test_geopolitical_oil_support_for_bullish_petrol_asset() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        entry_time = datetime(2026, 3, 6, 12, 0, tzinfo=UTC)
        article = NewsArticle(
            instrument="PETR4",
            headline="Guerra no Oriente Medio eleva Brent e favorece exportadoras de petroleo",
            source_name="Canal Financeiro",
            source_type="financial_media",
            credibility_score=75.0,
            anti_hype_score=70.0,
            published_at=(entry_time - timedelta(days=2)).isoformat(),
            captured_at=(entry_time - timedelta(days=2)).isoformat(),
        )
        db.add(article)
        db.flush()
        db.add(
            NewsAnalysisSnapshot(
                news_article_id=article.id,
                instrument="PETR4",
                sector="energia",
                theme="corporativo",
                sentiment_label="positive",
                sentiment_score=0.7,
                magnitude_score=0.9,
                model_confidence=0.9,
                source_url="https://example.com/geo",
                language="pt-BR",
                availability_time=(entry_time - timedelta(days=2)).isoformat(),
            )
        )
        db.commit()

        support_pct, available, rationale = _geopolitical_oil_support_pct(
            db,
            "PETR4",
            entry_time,
            "bullish",
        )
        assert available is True
        assert support_pct > 50
        assert "geo_oil_context_sent_" in rationale
    finally:
        db.close()


def test_geopolitical_oil_support_non_sensitive_asset_is_neutral() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        entry_time = datetime(2026, 3, 6, 12, 0, tzinfo=UTC)
        support_pct, available, rationale = _geopolitical_oil_support_pct(
            db,
            "ITUB4",
            entry_time,
            "bullish",
        )
        assert support_pct == 50.0
        assert available is False
        assert rationale == "geo_oil_nao_aplicavel_para_ativo"
    finally:
        db.close()

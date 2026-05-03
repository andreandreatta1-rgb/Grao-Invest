from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from app.db import Base
from app.models import FundamentalSnapshot, IndicatorSnapshot, MarketTick, NewsArticle, Signal
from app.services.thesis_ai_analysis import build_thesis_ai_analysis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return session_local()


def _seed_context(db: Session, *, user_id: int = 7, instrument: str = "PETR4") -> None:
    now = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)
    for index, price in enumerate([35.1, 35.7, 36.4]):
        event_time = now - timedelta(days=2 - index)
        db.add(
            MarketTick(
                instrument=instrument,
                provider="unit-test",
                event_time=event_time.isoformat(),
                ingest_time=event_time.isoformat(),
                price=price,
                volume=1000 + index,
                currency="BRL",
            )
        )
    db.add(
        IndicatorSnapshot(
            instrument=instrument,
            reference_time=now.isoformat(),
            availability_time=now.isoformat(),
            sma_5=36.1,
            sma_10=35.6,
            sma_20=34.9,
            ema_5=36.2,
            ema_12=35.9,
            ema_26=35.1,
            rsi_14=61.0,
            volatility_10=0.024,
            momentum_5=0.043,
            macd=0.38,
        )
    )
    db.add(
        FundamentalSnapshot(
            instrument=instrument,
            source_name="unit-test",
            source_type="fixture",
            reference_time=now.isoformat(),
            availability_time=now.isoformat(),
            pe_ratio=7.8,
            pb_ratio=1.3,
            ev_ebitda=4.1,
            dividend_yield=9.2,
            roe=18.0,
            net_margin=14.0,
            revenue_growth=6.0,
            payout_ratio=42.0,
            version_tag="fixture",
        )
    )
    db.add(
        Signal(
            user_id=user_id,
            instrument=instrument,
            reference_time=now.isoformat(),
            availability_time=now.isoformat(),
            signal_type="bullish_setup",
            confidence=0.78,
            rationale="Cenario multi-fator favoravel. Conteudo educacional; nao e recomendacao.",
            anti_hype_score=82.0,
            xai_payload=json.dumps({"drivers": ["momentum", "fundamentos"]}),
        )
    )
    db.add(
        NewsArticle(
            instrument=instrument,
            headline="Petrobras avanca com melhora de margem e petroleo firme",
            source_name="Unit News",
            source_type="financial_media",
            credibility_score=80.0,
            anti_hype_score=78.0,
            published_at=now.isoformat(),
            captured_at=now.isoformat(),
        )
    )
    db.commit()


def test_local_fallback_returns_structured_educational_analysis(monkeypatch) -> None:
    db = _db_session()
    try:
        _seed_context(db)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        macro_context = {"status": "available", "items": [{"name": "Selic", "value": 10.5}]}

        result = build_thesis_ai_analysis(
            db,
            user_id=7,
            instrument="PETR4",
            question="Como ler a tese?",
            macro_fetcher=lambda: macro_context,
        )

        assert result["instrument"] == "PETR4"
        assert result["asset_class"] == "stock"
        assert result["provider"] == "local_fallback"
        assert result["summary"]
        assert result["thesis"]
        assert result["evidence"]
        assert result["risks"]
        assert result["triggers"]
        assert result["exit_conditions"]
        assert result["macro_context"]["status"] == "available"
        assert "nao e recomendacao de investimento" in result["education_disclaimer"]
    finally:
        db.close()


def test_macro_fetch_failure_does_not_block_analysis(monkeypatch) -> None:
    db = _db_session()
    try:
        _seed_context(db)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        def broken_macro_fetcher() -> dict[str, Any]:
            raise httpx.TimeoutException("BCB indisponivel")

        result = build_thesis_ai_analysis(
            db,
            user_id=7,
            instrument="PETR4",
            macro_fetcher=broken_macro_fetcher,
        )

        assert result["provider"] == "local_fallback"
        assert result["macro_context"]["status"] == "unavailable"
        assert "BCB indisponivel" in result["macro_context"]["reason"]
    finally:
        db.close()


def test_openai_structured_response_is_used_when_key_exists(monkeypatch) -> None:
    db = _db_session()
    captured: dict[str, Any] = {}
    try:
        _seed_context(db)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
        openai_payload = {
            "instrument": "PETR4",
            "asset_class": "stock",
            "summary": "Resumo gerado pela IA.",
            "thesis": "Tese estruturada.",
            "evidence": ["Momentum positivo"],
            "risks": ["Risco de petroleo"],
            "triggers": ["Rompimento tecnico"],
            "exit_conditions": ["Perda do stop"],
            "macro_context": {"status": "available"},
            "confidence_score": 0.74,
            "education_disclaimer": "Conteudo educacional; nao e recomendacao de investimento.",
            "sources": ["sinal interno"],
        }

        def fake_post(url: str, **kwargs: Any) -> httpx.Response:
            captured["url"] = url
            captured["kwargs"] = kwargs
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(openai_payload),
                                }
                            ]
                        }
                    ]
                },
            )

        monkeypatch.setattr("app.services.thesis_ai_analysis.httpx.post", fake_post)

        result = build_thesis_ai_analysis(
            db,
            user_id=7,
            instrument="PETR4",
            macro_fetcher=lambda: {"status": "available", "items": []},
        )

        assert result["provider"] == "openai"
        assert result["summary"] == "Resumo gerado pela IA."
        assert captured["url"] == "https://api.openai.com/v1/responses"
        assert captured["kwargs"]["headers"]["Authorization"] == "Bearer sk-test"
        request_payload = captured["kwargs"]["json"]
        assert request_payload["model"] == "gpt-test"
        assert request_payload["text"]["format"]["type"] == "json_schema"
    finally:
        db.close()

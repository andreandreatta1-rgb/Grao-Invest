from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db import Base
from app.models import FundamentalSnapshot, MarketProviderState, MarketTick, NewsArticle
from app.services.data_quality import build_data_quality_gate_snapshot
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return session_local()


def test_data_quality_gate_detects_coverage_and_freshness_failures() -> None:
    db = _session()
    try:
        now = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
        db.add_all(
            [
                MarketTick(
                    instrument="PETR4",
                    provider="intraday-finnhub",
                    event_time=(now - timedelta(minutes=2)).isoformat(),
                    ingest_time=(now - timedelta(minutes=1)).isoformat(),
                    price=35.2,
                    volume=1000,
                    currency="BRL",
                    source_payload_id="petr4-1",
                ),
                MarketTick(
                    instrument="VALE3",
                    provider="intraday-finnhub",
                    event_time=(now - timedelta(hours=2)).isoformat(),
                    ingest_time=(now - timedelta(hours=2)).isoformat(),
                    price=61.9,
                    volume=900,
                    currency="BRL",
                    source_payload_id="vale3-1",
                ),
                FundamentalSnapshot(
                    instrument="PETR4",
                    source_name="Provider A",
                    source_type="market_data_api",
                    reference_time=(now - timedelta(days=1)).isoformat(),
                    availability_time=(now - timedelta(hours=10)).isoformat(),
                    pe_ratio=8.0,
                    pb_ratio=1.3,
                    ev_ebitda=4.7,
                    dividend_yield=9.8,
                    roe=18.1,
                    net_margin=12.0,
                    revenue_growth=5.4,
                    payout_ratio=48.0,
                    version_tag="petr4-v1",
                ),
                FundamentalSnapshot(
                    instrument="VALE3",
                    source_name="Provider A",
                    source_type="market_data_api",
                    reference_time=(now - timedelta(days=14)).isoformat(),
                    availability_time=(now - timedelta(days=14)).isoformat(),
                    pe_ratio=6.1,
                    pb_ratio=1.9,
                    ev_ebitda=5.8,
                    dividend_yield=7.4,
                    roe=14.2,
                    net_margin=20.3,
                    revenue_growth=3.2,
                    payout_ratio=52.0,
                    version_tag="vale3-v1",
                ),
                NewsArticle(
                    instrument="PETR4",
                    headline="Petroleo sobe com ajuste de oferta",
                    source_name="Agencia X",
                    source_type="financial_media",
                    credibility_score=82.0,
                    anti_hype_score=78.0,
                    published_at=(now - timedelta(days=1)).isoformat(),
                    captured_at=(now - timedelta(days=1)).isoformat(),
                ),
                MarketProviderState(
                    provider_name="provider-sem-dado",
                    role="secondary",
                    status="healthy",
                    consecutive_failures=0,
                    last_event_time=now.isoformat(),
                    failover_threshold=3,
                    is_active=False,
                    details="{}",
                ),
            ]
        )
        db.commit()

        payload = build_data_quality_gate_snapshot(
            db,
            instruments=["PETR4", "VALE3", "ITUB4"],
            market_max_lag_seconds=1800,
            market_min_fresh_coverage_pct=95.0,
            fundamentals_min_coverage_pct=90.0,
            fundamentals_max_staleness_days=1,
            fundamentals_min_fresh_coverage_pct=90.0,
            news_lookback_days=7,
            news_min_coverage_pct=80.0,
            max_critical_providers=0,
            max_no_data_providers=0,
        )

        assert payload["summary"]["gate_status"] == "fail"
        failed_ids = {
            item["check_id"]
            for item in payload["checks"]
            if item["status"] == "fail"
        }
        assert "market_fresh_coverage_pct" in failed_ids
        assert "fundamentals_coverage_pct" in failed_ids
        assert "fundamentals_fresh_coverage_pct" in failed_ids
        assert "news_recent_coverage_pct" in failed_ids
        assert "provider_no_data_count" in failed_ids
        assert payload["recommended_actions"]
    finally:
        db.close()


def test_data_quality_gate_passes_with_fresh_full_scope() -> None:
    db = _session()
    try:
        now = datetime.now(UTC)
        for instrument, price in (("PETR4", 36.0), ("VALE3", 62.8)):
            db.add(
                MarketTick(
                    instrument=instrument,
                    provider="intraday-finnhub",
                    event_time=(now - timedelta(minutes=2)).isoformat(),
                    ingest_time=(now - timedelta(seconds=30)).isoformat(),
                    price=price,
                    volume=1200,
                    currency="BRL",
                    source_payload_id=f"{instrument}-ok",
                )
            )
            db.add(
                FundamentalSnapshot(
                    instrument=instrument,
                    source_name="Provider A",
                    source_type="market_data_api",
                    reference_time=(now - timedelta(days=1)).isoformat(),
                    availability_time=(now - timedelta(hours=5)).isoformat(),
                    pe_ratio=10.0,
                    pb_ratio=1.5,
                    ev_ebitda=6.0,
                    dividend_yield=6.0,
                    roe=15.0,
                    net_margin=11.0,
                    revenue_growth=4.0,
                    payout_ratio=45.0,
                    version_tag=f"{instrument}-v1",
                )
            )
            db.add(
                NewsArticle(
                    instrument=instrument,
                    headline=f"Noticia recente de {instrument}",
                    source_name="Agencia Y",
                    source_type="financial_media",
                    credibility_score=80.0,
                    anti_hype_score=85.0,
                    published_at=(now - timedelta(days=1)).isoformat(),
                    captured_at=(now - timedelta(days=1)).isoformat(),
                )
            )
        db.commit()

        payload = build_data_quality_gate_snapshot(
            db,
            instruments=["PETR4", "VALE3"],
            market_max_lag_seconds=1800,
            market_min_fresh_coverage_pct=95.0,
            fundamentals_min_coverage_pct=90.0,
            fundamentals_max_staleness_days=2,
            fundamentals_min_fresh_coverage_pct=90.0,
            news_lookback_days=7,
            news_min_coverage_pct=90.0,
            max_critical_providers=0,
            max_no_data_providers=0,
        )

        assert payload["summary"]["gate_status"] == "pass"
        assert payload["summary"]["failed_checks"] == 0
        assert payload["recommended_actions"] == []
    finally:
        db.close()


def test_data_quality_gate_does_not_require_fundamentals_for_crypto_assets() -> None:
    db = _session()
    try:
        now = datetime.now(UTC)
        for instrument, price in (("PETR4", 36.0), ("BTCUSDT", 65000.0)):
            db.add(
                MarketTick(
                    instrument=instrument,
                    provider="intraday-provider",
                    event_time=(now - timedelta(minutes=2)).isoformat(),
                    ingest_time=(now - timedelta(seconds=30)).isoformat(),
                    price=price,
                    volume=1200,
                    currency="BRL" if instrument == "PETR4" else "USDT",
                    source_payload_id=f"{instrument}-ok",
                )
            )
            db.add(
                NewsArticle(
                    instrument=instrument,
                    headline=f"Noticia recente de {instrument}",
                    source_name="Agencia Y",
                    source_type="financial_media",
                    credibility_score=80.0,
                    anti_hype_score=85.0,
                    published_at=(now - timedelta(days=1)).isoformat(),
                    captured_at=(now - timedelta(days=1)).isoformat(),
                )
            )
        db.add(
            FundamentalSnapshot(
                instrument="PETR4",
                source_name="Provider A",
                source_type="market_data_api",
                reference_time=(now - timedelta(days=1)).isoformat(),
                availability_time=(now - timedelta(hours=5)).isoformat(),
                pe_ratio=10.0,
                pb_ratio=1.5,
                ev_ebitda=6.0,
                dividend_yield=6.0,
                roe=15.0,
                net_margin=11.0,
                revenue_growth=4.0,
                payout_ratio=45.0,
                version_tag="PETR4-v1",
            )
        )
        db.commit()

        payload = build_data_quality_gate_snapshot(
            db,
            instruments=["PETR4", "BTCUSDT"],
            market_max_lag_seconds=1800,
            market_min_fresh_coverage_pct=95.0,
            fundamentals_min_coverage_pct=90.0,
            fundamentals_max_staleness_days=2,
            fundamentals_min_fresh_coverage_pct=90.0,
            news_lookback_days=7,
            news_min_coverage_pct=90.0,
            max_critical_providers=0,
            max_no_data_providers=0,
        )

        assert payload["summary"]["gate_status"] == "pass"
        assert payload["fundamentals"]["covered_instrument_count"] == 1
        assert payload["fundamentals"]["missing_instrument_count"] == 0
        assert payload["fundamentals"]["fresh_coverage_pct"] == 100.0
    finally:
        db.close()


def test_data_quality_gate_allows_b3_daily_feed_window_with_fresh_crypto() -> None:
    db = _session()
    try:
        now = datetime.now(UTC)
        for instrument, price, ingest_delta in (
            ("PETR4", 36.0, timedelta(hours=8)),
            ("BTCUSDT", 65000.0, timedelta(seconds=30)),
        ):
            db.add(
                MarketTick(
                    instrument=instrument,
                    provider="b3-cotahist" if instrument == "PETR4" else "crypto-binance-5m",
                    event_time=(now - ingest_delta).isoformat(),
                    ingest_time=(now - ingest_delta).isoformat(),
                    price=price,
                    volume=1200,
                    currency="BRL" if instrument == "PETR4" else "USDT",
                    source_payload_id=f"{instrument}-ok",
                )
            )
            db.add(
                NewsArticle(
                    instrument=instrument,
                    headline=f"Noticia recente de {instrument}",
                    source_name="Agencia Y",
                    source_type="financial_media",
                    credibility_score=80.0,
                    anti_hype_score=85.0,
                    published_at=(now - timedelta(days=1)).isoformat(),
                    captured_at=(now - timedelta(days=1)).isoformat(),
                )
            )
        db.add(
            FundamentalSnapshot(
                instrument="PETR4",
                source_name="Provider A",
                source_type="market_data_api",
                reference_time=(now - timedelta(days=1)).isoformat(),
                availability_time=(now - timedelta(hours=5)).isoformat(),
                pe_ratio=10.0,
                pb_ratio=1.5,
                ev_ebitda=6.0,
                dividend_yield=6.0,
                roe=15.0,
                net_margin=11.0,
                revenue_growth=4.0,
                payout_ratio=45.0,
                version_tag="PETR4-v1",
            )
        )
        db.commit()

        payload = build_data_quality_gate_snapshot(
            db,
            instruments=["PETR4", "BTCUSDT"],
            market_max_lag_seconds=1800,
            market_min_fresh_coverage_pct=95.0,
            fundamentals_min_coverage_pct=90.0,
            fundamentals_max_staleness_days=2,
            fundamentals_min_fresh_coverage_pct=90.0,
            news_lookback_days=7,
            news_min_coverage_pct=90.0,
            max_critical_providers=0,
            max_no_data_providers=0,
        )

        assert payload["summary"]["gate_status"] == "pass"
        assert payload["market"]["fresh_coverage_pct"] == 100.0
    finally:
        db.close()

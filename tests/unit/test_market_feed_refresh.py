from __future__ import annotations

from datetime import UTC, datetime

from app.db import Base
from app.models import MarketTick
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scripts import refresh_market_feeds


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_crypto_refresh_inserts_candles_and_ignores_duplicates(monkeypatch) -> None:
    session_local = _session_factory()
    candles = [
        {
            "instrument": "BTCUSDT",
            "provider_symbol": "BTCUSDT",
            "provider_name": "binance",
            "interval": "5m",
            "event_time": datetime(2026, 5, 8, 10, 0, tzinfo=UTC),
            "price": 64000.0,
            "volume": 12,
            "currency": "USDT",
            "source_payload_id": "bnc:BTCUSDT:5m:1",
        },
        {
            "instrument": "BTCUSDT",
            "provider_symbol": "BTCUSDT",
            "provider_name": "binance",
            "interval": "5m",
            "event_time": datetime(2026, 5, 8, 10, 5, tzinfo=UTC),
            "price": 64100.0,
            "volume": 13,
            "currency": "USDT",
            "source_payload_id": "bnc:BTCUSDT:5m:2",
        },
    ]

    monkeypatch.setattr(
        refresh_market_feeds,
        "fetch_historical_crypto_candles",
        lambda *args, **kwargs: candles,
    )

    with session_local() as db:
        first = refresh_market_feeds.refresh_crypto_history(
            db,
            provider_name="binance",
            instruments=["BTCUSDT"],
            interval="5m",
            lookback_hours=2,
            max_candles_per_instrument=50,
            auto_recompute_indicators=False,
        )
        second = refresh_market_feeds.refresh_crypto_history(
            db,
            provider_name="binance",
            instruments=["BTCUSDT"],
            interval="5m",
            lookback_hours=2,
            max_candles_per_instrument=50,
            auto_recompute_indicators=False,
        )
        rows = db.scalars(select(MarketTick)).all()

    assert first["inserted"] == 2
    assert first["duplicates_ignored"] == 0
    assert second["inserted"] == 0
    assert second["duplicates_ignored"] == 2
    assert len(rows) == 2
    assert rows[-1].event_time == "2026-05-08T10:05:00+00:00"


def test_b3_cycle_runs_feed_refresh_before_current_thesis_generation() -> None:
    script = refresh_market_feeds.REPO_ROOT.joinpath(
        "scripts",
        "run_b3_automation_cycle.ps1",
    ).read_text(encoding="utf-8-sig")

    assert "refresh_market_feeds.py" in script
    assert script.index("refresh_market_feeds.py") < script.index(
        "run_current_thesis_by_front_job.py"
    )

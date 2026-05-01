from __future__ import annotations

from datetime import UTC, datetime

from app.db import Base
from app.models import MarketTick
from app.services.fundamentals_external import (
    fundamentals_coverage_snapshot,
    sync_external_fundamentals,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _quote_summary_payload(
    *,
    pe: float | None,
    pb: float | None,
    ev_ebitda: float | None,
    dividend_yield: float | None,
    roe: float | None,
    net_margin: float | None,
    revenue_growth: float | None,
    payout_ratio: float | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "defaultKeyStatistics": {
            "lastFiscalYearEnd": {"raw": 1703980800},
        },
        "summaryDetail": {},
        "financialData": {},
        "price": {"regularMarketTime": {"raw": 1714000000}},
    }
    default_stats = payload["defaultKeyStatistics"]
    summary_detail = payload["summaryDetail"]
    financial_data = payload["financialData"]
    if not isinstance(default_stats, dict):
        raise AssertionError("defaultKeyStatistics deve ser dict.")
    if not isinstance(summary_detail, dict):
        raise AssertionError("summaryDetail deve ser dict.")
    if not isinstance(financial_data, dict):
        raise AssertionError("financialData deve ser dict.")
    if pe is not None:
        default_stats["trailingPE"] = {"raw": pe}
    if pb is not None:
        default_stats["priceToBook"] = {"raw": pb}
    if ev_ebitda is not None:
        default_stats["enterpriseToEbitda"] = {"raw": ev_ebitda}
    if payout_ratio is not None:
        default_stats["payoutRatio"] = {"raw": payout_ratio}
    if dividend_yield is not None:
        summary_detail["dividendYield"] = {"raw": dividend_yield}
    if roe is not None:
        financial_data["returnOnEquity"] = {"raw": roe}
    if net_margin is not None:
        financial_data["profitMargins"] = {"raw": net_margin}
    if revenue_growth is not None:
        financial_data["revenueGrowth"] = {"raw": revenue_growth}
    return payload


def test_sync_external_fundamentals_is_incremental_and_coverage_reports_gaps(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        db.add_all(
            [
                MarketTick(
                    instrument="PETR4",
                    provider="demo",
                    event_time=datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
                    ingest_time=datetime(2026, 4, 20, 12, 1, tzinfo=UTC).isoformat(),
                    price=32.0,
                    volume=1000,
                    currency="BRL",
                    source_payload_id="petr4-1",
                ),
                MarketTick(
                    instrument="ITUB4",
                    provider="demo",
                    event_time=datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
                    ingest_time=datetime(2026, 4, 20, 12, 1, tzinfo=UTC).isoformat(),
                    price=38.0,
                    volume=900,
                    currency="BRL",
                    source_payload_id="itub4-1",
                ),
                MarketTick(
                    instrument="VALE3",
                    provider="demo",
                    event_time=datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
                    ingest_time=datetime(2026, 4, 20, 12, 1, tzinfo=UTC).isoformat(),
                    price=61.0,
                    volume=800,
                    currency="BRL",
                    source_payload_id="vale3-1",
                ),
            ]
        )
        db.commit()

        def fake_fetch(provider_symbol: str) -> dict[str, object]:
            if provider_symbol == "PETR4.SA":
                return _quote_summary_payload(
                    pe=8.2,
                    pb=1.4,
                    ev_ebitda=5.1,
                    dividend_yield=0.11,
                    roe=0.22,
                    net_margin=0.16,
                    revenue_growth=0.07,
                    payout_ratio=0.54,
                )
            if provider_symbol == "ITUB4.SA":
                return _quote_summary_payload(
                    pe=9.5,
                    pb=1.9,
                    ev_ebitda=None,
                    dividend_yield=None,
                    roe=0.18,
                    net_margin=0.12,
                    revenue_growth=0.05,
                    payout_ratio=0.45,
                )
            raise AssertionError(f"Ativo inesperado no teste: {provider_symbol}")

        monkeypatch.setattr(
            "app.services.fundamentals_external._fetch_yahoo_quote_summary",
            fake_fetch,
        )

        first_sync = sync_external_fundamentals(
            db,
            user_id=1,
            provider_name="yahoo",
            instruments=["PETR4", "ITUB4"],
            only_missing=False,
            max_instruments=10,
        )
        assert first_sync["inserted"] == 2
        assert first_sync["duplicates_ignored"] == 0
        assert first_sync["failed"] == 0
        assert "ev_ebitda" in first_sync["by_instrument"]["ITUB4"]["missing_fields"]
        assert first_sync["by_instrument"]["ITUB4"]["completeness_pct"] < 100

        second_sync = sync_external_fundamentals(
            db,
            user_id=1,
            provider_name="yahoo",
            instruments=["PETR4", "ITUB4"],
            only_missing=False,
            max_instruments=10,
        )
        assert second_sync["inserted"] == 0
        assert second_sync["duplicates_ignored"] == 2
        assert second_sync["failed"] == 0

        coverage = fundamentals_coverage_snapshot(db, max_rows=20)
        assert coverage["total_market_instruments"] == 3
        assert coverage["market_instruments_with_fundamentals"] == 2
        assert coverage["missing_fundamental_instruments"] == 1
        assert coverage["coverage_pct"] == 66.6667
        assert any(
            row["instrument"] == "VALE3" and row["has_fundamentals"] is False
            for row in coverage["rows"]
        )
    finally:
        db.close()


def test_sync_external_fundamentals_auto_fallback_uses_brapi(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        db.add(
            MarketTick(
                instrument="PETR4",
                provider="demo",
                event_time=datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
                ingest_time=datetime(2026, 4, 20, 12, 1, tzinfo=UTC).isoformat(),
                price=32.0,
                volume=1000,
                currency="BRL",
                source_payload_id="petr4-auto",
            )
        )
        db.commit()

        def fake_yahoo(_provider_symbol: str) -> dict[str, object]:
            raise ValueError("HTTP Error 401: Unauthorized")

        monkeypatch.setattr(
            "app.services.fundamentals_external._fetch_yahoo_quote_summary",
            fake_yahoo,
        )
        monkeypatch.setattr(
            "app.services.fundamentals_external._fetch_brapi_quote_summary",
            lambda _instrument: _quote_summary_payload(
                pe=7.9,
                pb=None,
                ev_ebitda=None,
                dividend_yield=None,
                roe=None,
                net_margin=None,
                revenue_growth=None,
                payout_ratio=None,
            ),
        )

        sync_payload = sync_external_fundamentals(
            db,
            user_id=1,
            provider_name="auto",
            instruments=["PETR4"],
            only_missing=False,
            max_instruments=10,
        )
        assert sync_payload["inserted"] == 1
        assert sync_payload["failed"] == 0
        assert sync_payload["by_instrument"]["PETR4"]["status"] == "inserted"
        assert sync_payload["by_instrument"]["PETR4"]["provider_symbol"] == "PETR4"
    finally:
        db.close()

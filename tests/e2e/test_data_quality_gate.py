from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _ingest_market_tick(client: TestClient, instrument: str, event_time: datetime) -> None:
    response = client.post(
        "/api/market/ticks/ingest-live",
        json={
            "instrument": instrument,
            "provider": "intraday-finnhub",
            "event_time": event_time.isoformat(),
            "price": 35.0,
            "volume": 1200,
            "currency": "BRL",
            "source_payload_id": f"{instrument}-{int(event_time.timestamp())}",
            "auto_recompute_indicators": False,
        },
    )
    assert response.status_code == 200


def _ingest_fundamental(client: TestClient, instrument: str, availability_time: datetime) -> None:
    response = client.post(
        "/api/fundamentals/ingest",
        json={
            "instrument": instrument,
            "source_name": "Provider A",
            "source_type": "market_data_api",
            "reference_time": (availability_time - timedelta(days=1)).isoformat(),
            "availability_time": availability_time.isoformat(),
            "pe_ratio": 9.3,
            "pb_ratio": 1.5,
            "ev_ebitda": 6.1,
            "dividend_yield": 5.4,
            "roe": 16.2,
            "net_margin": 10.5,
            "revenue_growth": 4.2,
            "payout_ratio": 42.0,
            "version_tag": f"{instrument}-v1",
        },
    )
    assert response.status_code == 200


def _ingest_news(client: TestClient, instrument: str, published_at: datetime) -> None:
    response = client.post(
        "/api/news/ingest",
        json={
            "instrument": instrument,
            "headline": f"Noticia relevante de {instrument}",
            "source_name": "Agencia Teste",
            "source_type": "financial_media",
            "published_at": published_at.isoformat(),
        },
    )
    assert response.status_code == 200


def test_data_quality_gate_endpoint_returns_pass_and_fail_paths(client: TestClient) -> None:
    now = datetime.now(UTC)
    _ingest_market_tick(client, "PETR4", now - timedelta(minutes=2))
    _ingest_market_tick(client, "VALE3", now - timedelta(minutes=2))
    _ingest_fundamental(client, "PETR4", now - timedelta(hours=6))
    _ingest_fundamental(client, "VALE3", now - timedelta(hours=6))
    _ingest_news(client, "PETR4", now - timedelta(days=1))
    _ingest_news(client, "VALE3", now - timedelta(days=1))

    pass_response = client.get(
        "/api/data-quality/gate",
        params={
            "instruments": "PETR4,VALE3",
            "market_min_fresh_coverage_pct": 95,
            "fundamentals_min_coverage_pct": 90,
            "fundamentals_max_staleness_days": 2,
            "fundamentals_min_fresh_coverage_pct": 90,
            "news_lookback_days": 7,
            "news_min_coverage_pct": 90,
        },
    )
    assert pass_response.status_code == 200
    pass_payload = pass_response.json()
    assert pass_payload["summary"]["gate_status"] == "pass"
    assert pass_payload["summary"]["failed_checks"] == 0

    fail_response = client.get(
        "/api/data-quality/gate",
        params={
            "instruments": "PETR4,VALE3,ITUB4",
            "market_min_fresh_coverage_pct": 95,
            "fundamentals_min_coverage_pct": 90,
            "fundamentals_max_staleness_days": 2,
            "fundamentals_min_fresh_coverage_pct": 90,
            "news_lookback_days": 7,
            "news_min_coverage_pct": 90,
        },
    )
    assert fail_response.status_code == 200
    fail_payload = fail_response.json()
    assert fail_payload["summary"]["gate_status"] == "fail"
    assert fail_payload["summary"]["failed_checks"] >= 1
    failed_check_ids = {
        item["check_id"]
        for item in fail_payload["checks"]
        if item["status"] == "fail"
    }
    assert "fundamentals_coverage_pct" in failed_check_ids

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _signup_and_authenticate(client: TestClient, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Fundamentals Sync Lab",
            "full_name": "User Fundamentals Sync",
            "email": email,
            "password": DEFAULT_PASSWORD,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert signup_response.status_code == 200
    user_id = signup_response.json()["user_id"]

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return user_id


def _quote_summary_payload(
    *,
    pe: float,
    pb: float,
    ev_ebitda: float,
    dividend_yield: float,
    roe: float,
    net_margin: float,
    revenue_growth: float,
    payout_ratio: float,
) -> dict[str, object]:
    return {
        "defaultKeyStatistics": {
            "trailingPE": {"raw": pe},
            "priceToBook": {"raw": pb},
            "enterpriseToEbitda": {"raw": ev_ebitda},
            "payoutRatio": {"raw": payout_ratio},
            "lastFiscalYearEnd": {"raw": 1703980800},
        },
        "summaryDetail": {"dividendYield": {"raw": dividend_yield}},
        "financialData": {
            "returnOnEquity": {"raw": roe},
            "profitMargins": {"raw": net_margin},
            "revenueGrowth": {"raw": revenue_growth},
        },
        "price": {"regularMarketTime": {"raw": 1714000000}},
    }


def test_fundamentals_external_sync_and_coverage_endpoint(client, monkeypatch) -> None:
    user_id = _signup_and_authenticate(client, "external-fundamentals@example.com")
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    for index, instrument in enumerate(["PETR4", "ITUB4", "B3SA3"]):
        ingest_response = client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": instrument,
                "provider": "demo-primary",
                "event_time": base_time.isoformat(),
                "price": 30 + index,
                "volume": 1000 + index * 50,
                "currency": "BRL",
                "source_payload_id": f"fund-sync-{instrument}",
            },
        )
        assert ingest_response.status_code == 200

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
                pe=9.3,
                pb=1.8,
                ev_ebitda=6.1,
                dividend_yield=0.08,
                roe=0.18,
                net_margin=0.12,
                revenue_growth=0.05,
                payout_ratio=0.47,
            )
        raise AssertionError(f"Ativo inesperado no teste: {provider_symbol}")

    monkeypatch.setattr(
        "app.services.fundamentals_external._fetch_yahoo_quote_summary",
        fake_fetch,
    )

    payload = {
        "user_id": user_id,
        "provider_name": "yahoo",
        "instruments": ["PETR4", "ITUB4"],
        "max_instruments": 10,
        "only_missing": False,
    }
    first_sync = client.post("/api/fundamentals/external/sync", json=payload)
    assert first_sync.status_code == 200
    first_sync_payload = first_sync.json()
    assert first_sync_payload["inserted"] == 2
    assert first_sync_payload["duplicates_ignored"] == 0
    assert first_sync_payload["failed"] == 0

    second_sync = client.post("/api/fundamentals/external/sync", json=payload)
    assert second_sync.status_code == 200
    second_sync_payload = second_sync.json()
    assert second_sync_payload["inserted"] == 0
    assert second_sync_payload["duplicates_ignored"] == 2
    assert second_sync_payload["failed"] == 0

    coverage = client.get("/api/fundamentals/coverage", params={"max_rows": 20})
    assert coverage.status_code == 200
    coverage_payload = coverage.json()
    assert coverage_payload["total_market_instruments"] == 3
    assert coverage_payload["market_instruments_with_fundamentals"] == 2
    assert coverage_payload["missing_fundamental_instruments"] == 1
    assert coverage_payload["coverage_pct"] == 66.6667
    assert any(
        row["instrument"] == "B3SA3" and row["has_fundamentals"] is False
        for row in coverage_payload["rows"]
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _signup_and_authenticate(client: TestClient, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Intraday Lab",
            "full_name": "User Intraday",
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


def test_intraday_fetch_live_updates_market_and_exposes_health(client, monkeypatch) -> None:
    user_id = _signup_and_authenticate(client, "intraday-health@example.com")
    reference = datetime.now(UTC)

    def fake_fetch_intraday_quotes(provider_name, instruments, symbol_overrides=None):  # noqa: ANN001
        del symbol_overrides
        assert provider_name == "finnhub"
        return [
            {
                "instrument": "PETR4",
                "provider_symbol": "BVMF:PETR4",
                "provider_name": "finnhub",
                "event_time": reference - timedelta(hours=2),
                "price": 38.9,
                "volume": 1200,
                "currency": "BRL",
                "source_payload_id": "finnhub:PETR4:1",
            },
            {
                "instrument": "VALE3",
                "provider_symbol": "BVMF:VALE3",
                "provider_name": "finnhub",
                "event_time": reference - timedelta(minutes=5),
                "price": 63.4,
                "volume": 980,
                "currency": "BRL",
                "source_payload_id": "finnhub:VALE3:1",
            },
        ]

    monkeypatch.setattr("app.main.fetch_intraday_quotes", fake_fetch_intraday_quotes)

    intraday_response = client.post(
        "/api/market/intraday/fetch-live",
        json={
            "user_id": user_id,
            "provider_name": "finnhub",
            "instruments": ["PETR4", "VALE3"],
            "auto_recompute_indicators": False,
        },
    )
    assert intraday_response.status_code == 200
    intraday_payload = intraday_response.json()
    assert intraday_payload["processed_count"] == 2
    assert intraday_payload["failed_count"] == 0
    assert intraday_payload["processed"][0]["algorithm_update"]["learning_status"] == "warming_up"

    health_response = client.get(
        "/api/market/feed/health",
        params={"stale_threshold_seconds": 7200, "latency_threshold_seconds": 60},
    )
    assert health_response.status_code == 200
    health_payload = health_response.json()
    providers = health_payload["providers"]
    intraday_provider = next(
        item for item in providers if item["provider_name"] == "intraday-finnhub"
    )
    assert intraday_provider["health_status"] == "warning"
    assert "high_market_lag" in intraday_provider["health_issues"]

    coverage_response = client.get("/api/market/universe/coverage", params={"max_rows": 10})
    assert coverage_response.status_code == 200
    coverage_payload = coverage_response.json()
    assert coverage_payload["total_instruments_covered"] >= 2
    assert len(coverage_payload["instruments"]) >= 2
    assert coverage_payload["instruments"][0]["provider"].startswith("intraday-")

    dashboard_response = client.get(f"/api/dashboard/summary/{user_id}")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["market_coverage"] is not None
    assert dashboard_payload["market_coverage"]["total_instruments_covered"] >= 2


def test_intraday_fetch_live_requires_token_for_real_provider(client, monkeypatch) -> None:
    user_id = _signup_and_authenticate(client, "intraday-real-provider@example.com")
    monkeypatch.delenv("FINNHUB_API_TOKEN", raising=False)
    intraday_response = client.post(
        "/api/market/intraday/fetch-live",
        json={
            "user_id": user_id,
            "provider_name": "finnhub",
            "instruments": ["PETR4"],
            "auto_recompute_indicators": False,
        },
    )
    assert intraday_response.status_code == 400
    assert "FINNHUB_API_TOKEN" in intraday_response.json()["detail"]

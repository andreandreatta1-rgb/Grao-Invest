from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _signup_and_login(client: TestClient, *, email: str, full_name: str = "User Realtime") -> int:
    signup = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Realtime Lab",
            "full_name": full_name,
            "email": email,
            "password": DEFAULT_PASSWORD,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert signup.status_code == 200
    user_id = int(signup.json()["user_id"])
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return user_id


def _seed_instrument_ticks(
    client: TestClient,
    *,
    instrument: str,
    base_time: datetime,
    start_price: float,
    step: float,
    volume: int = 3000,
) -> None:
    for index in range(70):
        response = client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": instrument,
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": round(start_price + (step * index), 4),
                "volume": volume + index * 25,
                "currency": "BRL",
                "source_payload_id": f"{instrument}-rt-{index}",
            },
        )
        assert response.status_code == 200
    recompute = client.post(
        "/api/analysis/indicators/recompute",
        json={"instrument": instrument},
    )
    assert recompute.status_code == 200


def test_ws_signals_stream_and_fallback_polling_endpoint(client: TestClient) -> None:
    user_id = _signup_and_login(client, email="ws-signals@example.com")
    base_time = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)

    _seed_instrument_ticks(
        client,
        instrument="PETR4",
        base_time=base_time,
        start_price=35.0,
        step=0.09,
    )
    news = client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras atualiza projecoes operacionais com dados oficiais",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": (base_time + timedelta(minutes=10)).isoformat(),
        },
    )
    assert news.status_code == 200

    with client.websocket_connect(f"/ws/signals?user_id={user_id}") as websocket:
        first_signal = client.post(
            "/api/signals/generate",
            json={"user_id": user_id, "instrument": "PETR4"},
        )
        assert first_signal.status_code == 200
        message_1 = websocket.receive_json()
        assert message_1["type"] == "new_signal"
        assert message_1["payload"]["signal_status"] == "active"
        first_signal_id = int(message_1["payload"]["signal_id"])

        second_signal = client.post(
            "/api/signals/generate",
            json={"user_id": user_id, "instrument": "PETR4"},
        )
        assert second_signal.status_code == 200

        message_2 = websocket.receive_json()
        message_3 = websocket.receive_json()
        event_types = {message_2["type"], message_3["type"]}
        assert "new_signal" in event_types
        assert "signal_expired" in event_types
        expired_payload = (
            message_2["payload"] if message_2["type"] == "signal_expired" else message_3["payload"]
        )
        assert int(expired_payload["signal_id"]) == first_signal_id
        assert expired_payload["signal_status"] == "expired"

    active_poll = client.get(
        "/api/signals",
        params={"user_id": user_id, "status": "active", "limit": 10},
    )
    assert active_poll.status_code == 200
    active_rows = active_poll.json()
    assert len(active_rows) >= 1
    assert all(row["signal_status"] == "active" for row in active_rows)

    expired_poll = client.get(
        "/api/signals",
        params={"user_id": user_id, "status": "expired", "limit": 10},
    )
    assert expired_poll.status_code == 200
    expired_rows = expired_poll.json()
    assert len(expired_rows) >= 1
    assert all(row["signal_status"] == "expired" for row in expired_rows)


def test_ws_agent_and_portfolio_allocate_pipeline(client: TestClient) -> None:
    user_id = _signup_and_login(client, email="allocate@example.com", full_name="User Allocate")
    suitability = client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    assert suitability.status_code == 200

    base_time = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    instruments = [
        ("PETR4", 35.0, 0.10),
        ("VALE3", 61.0, 0.08),
        ("ITUB4", 29.0, 0.05),
        ("B3SA3", 13.0, 0.03),
        ("WEGE3", 42.0, 0.07),
        ("BBAS3", 24.0, 0.05),
        ("ABEV3", 15.0, 0.02),
        ("RENT3", 52.0, 0.06),
    ]
    for symbol, start_price, step in instruments:
        _seed_instrument_ticks(
            client,
            instrument=symbol,
            base_time=base_time,
            start_price=start_price,
            step=step,
        )

    with client.websocket_connect("/ws/agent") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "worker_status"
        payload = event["payload"]
        assert payload["summary"]["total_workers"] >= 8
        assert payload["feed_health"]["provider_count"] >= 0

    allocation = client.post(
        "/api/portfolio/allocate",
        json={
            "user_id": user_id,
            "capital_brl": 100000.0,
            "risk_profile": "moderado",
            "universe": "custom",
            "custom_instruments": [symbol for symbol, _, _ in instruments],
        },
    )
    assert allocation.status_code == 200
    plan = allocation.json()
    assert plan["version"] == 1
    assert len(plan["assets"]) >= 8
    assert plan["expected_sharpe"] >= 0
    for asset in plan["assets"]:
        if asset["ticker"] == "CASH-BRL":
            continue
        assert asset["weight_pct"] <= 15.0001

    latest = client.get("/api/portfolio/allocation/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["plan_id"] == plan["plan_id"]

    by_id = client.get(f"/api/portfolio/allocation/{plan['plan_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["plan_id"] == plan["plan_id"]

    rebalance = client.post(
        "/api/portfolio/rebalance",
        json={"user_id": user_id, "plan_id": plan["plan_id"]},
    )
    assert rebalance.status_code == 200
    rebalance_payload = rebalance.json()
    assert rebalance_payload["allocation_plan_id"] == plan["plan_id"]
    assert rebalance_payload["total_drift_pct"] >= 0

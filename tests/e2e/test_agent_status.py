from __future__ import annotations

from app.main import AUTH_DISABLED
from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _authenticate(client: TestClient, *, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Agent Status Lab",
            "full_name": "User Agent Status",
            "email": email,
            "password": DEFAULT_PASSWORD,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert signup_response.status_code == 200
    user_id = int(signup_response.json()["user_id"])
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return user_id


def test_agent_status_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/agent/status")
    if AUTH_DISABLED:
        assert response.status_code == 200
    else:
        assert response.status_code == 401


def test_agent_status_returns_worker_snapshot(client: TestClient) -> None:
    _authenticate(client, email="agent-status@example.com")
    response = client.get("/api/agent/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_workers"] >= 8
    assert payload["summary"]["error_workers"] >= 0
    assert payload["llm_cost_today_usd"] >= 0
    assert payload["runtime"]["running"] in {True, False}
    assert payload["feed_health"]["provider_count"] >= 0
    assert payload["data_coverage"]["instruments_covered"] >= 0
    worker_names = {item["worker_name"] for item in payload["workers"]}
    assert "intraday_price_worker" in worker_names
    assert "signal_generator_worker" in worker_names

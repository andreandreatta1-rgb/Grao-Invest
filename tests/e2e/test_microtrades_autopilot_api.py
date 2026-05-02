from __future__ import annotations

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _authenticate(client: TestClient, *, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Microtrades Lab",
            "full_name": "User Microtrades",
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


def test_microtrades_autopilot_cron_requires_authorization(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    response = client.post("/api/cron/microtrades-autopilot")
    assert response.status_code == 401


def test_microtrades_autopilot_cron_runs_cycle(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_ENABLED", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_USER_ID", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_INSTRUMENTS", "BTCUSDT,ETHUSDT")
    captured: dict[str, object] = {}

    def fake_run(_db, *, config):  # noqa: ANN001, ANN202
        captured["config"] = dict(config)
        return {
            "status": "success",
            "error": None,
            "run_started_at": "2026-05-02T10:00:00+00:00",
            "run_finished_at": "2026-05-02T10:00:10+00:00",
            "steps": [],
        }

    monkeypatch.setattr("app.main.run_microtrades_autopilot_cycle", fake_run)

    response = client.post(
        "/api/cron/microtrades-autopilot",
        headers={"Authorization": "Bearer cron-secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["error"] is None
    config = dict(captured["config"])
    assert config["user_id"] == 1
    assert config["instruments"] == ["BTCUSDT", "ETHUSDT"]


def test_microtrades_autopilot_manual_run_uses_current_user(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot@example.com")
    captured: dict[str, object] = {}

    def fake_run(_db, *, config):  # noqa: ANN001, ANN202
        captured["config"] = dict(config)
        return {
            "status": "partial",
            "error": None,
            "run_started_at": "2026-05-02T10:00:00+00:00",
            "run_finished_at": "2026-05-02T10:00:10+00:00",
            "steps": [],
        }

    monkeypatch.setattr("app.main.run_microtrades_autopilot_cycle", fake_run)

    response = client.post(
        "/api/microtrades/autopilot/run",
        json={
            "user_id": user_id,
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "interval": "5m",
            "lookback_hours": 72,
            "publish_decisions": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    config = dict(captured["config"])
    assert config["user_id"] == user_id
    assert config["instruments"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

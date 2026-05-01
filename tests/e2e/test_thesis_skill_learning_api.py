from __future__ import annotations

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _signup_and_authenticate(client: TestClient, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Thesis Skill Lab",
            "full_name": "User Thesis Skill",
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


def test_thesis_skill_learning_endpoint_runs_cycle(client, monkeypatch) -> None:
    user_id = _signup_and_authenticate(client, "thesis-skill-api@example.com")

    monkeypatch.setattr(
        "app.main.run_thesis_skill_learning_cycle",
        lambda *args, **kwargs: {  # noqa: ARG005
            "generated_at": "2026-04-22T00:00:00+00:00",
            "scan_scope": {"instrument_count": 1},
            "profile_path": "data/thesis_skill_profile.json",
            "profile": {
                "generated_at": "2026-04-22T00:00:00+00:00",
                "sample_size": 120,
                "calibration": {
                    "confidence_multiplier": 0.95,
                    "confidence_bias_points": -1.2,
                    "avg_predicted_confidence_pct": 66.0,
                    "realized_success_rate_pct": 61.0,
                    "brier_score": 0.22,
                },
                "confidence_bands": [],
                "blindspots": [],
            },
            "summary": {
                "success_rate_pct": 61.0,
                "avg_expected_financial_pct": 2.1,
                "avg_realized_financial_pct": 1.2,
                "avg_confidence_tese_pct": 66.0,
                "blindspot_count": 0.0,
            },
        },
    )

    response = client.post(
        "/api/theses/skill/learn",
        json={
            "user_id": user_id,
            "instruments": ["PETR4"],
            "horizon_bars": 12,
            "max_candidates": 400,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["sample_size"] == 120
    assert payload["summary"]["success_rate_pct"] == 61.0

from __future__ import annotations

import httpx


def _settings_payload(user_id: int) -> dict[str, object]:
    return {
        "user_id": user_id,
        "phone_number": "+55 11 97106-2620",
        "display_name": "Andre",
        "opt_in": True,
        "categories": {
            "thesis_new": True,
            "thesis_update": True,
            "stock_alert": True,
            "daily_digest": True,
        },
        "thresholds": {
            "thesis_confidence_pct": 55,
            "thesis_expected_pct": 0,
            "thesis_progress_delta_pct": 20,
            "stock_price_move_pct": 3,
            "news_magnitude": 0.75,
            "signal_confidence": 0.6,
        },
    }


def test_whatsapp_settings_and_test_endpoint(client, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")

    def fake_post(url: str, **kwargs: object) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(
            200,
            json={
                "messaging_product": "whatsapp",
                "messages": [{"id": "wamid.api-test"}],
            },
        )

    monkeypatch.setattr("app.services.notifications.httpx.post", fake_post)

    response = client.put("/api/notifications/whatsapp", json=_settings_payload(1))
    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_number"] == "+5511971062620"
    assert payload["opt_in"] is True
    assert payload["categories"]["thesis_new"] is True

    test_response = client.post("/api/notifications/whatsapp/test", json={"user_id": 1})
    assert test_response.status_code == 200
    test_payload = test_response.json()
    assert test_payload["status"] == "sent"
    assert test_payload["provider_message_id"] == "wamid.api-test"

    settings_response = client.get("/api/notifications/whatsapp?user_id=1")
    assert settings_response.status_code == 200
    deliveries = settings_response.json()["recent_deliveries"]
    assert deliveries[0]["status"] == "sent"


def test_whatsapp_webhook_verify_and_pause_command(client, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-token")
    response = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-token",
            "hub.challenge": "challenge-ok",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-ok"

    settings_response = client.put("/api/notifications/whatsapp", json=_settings_payload(1))
    assert settings_response.status_code == 200

    webhook_response = client.post(
        "/api/webhooks/whatsapp",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "5511971062620",
                                        "text": {"body": "PAUSAR"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()["commands"][0]["action"] == "paused"

    refreshed = client.get("/api/notifications/whatsapp?user_id=1")
    assert refreshed.status_code == 200
    assert refreshed.json()["paused"] is True
    assert refreshed.json()["opt_in"] is False

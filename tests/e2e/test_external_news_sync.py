from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _signup_and_authenticate(client: TestClient, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "News Sync Lab",
            "full_name": "User News Sync",
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


def test_news_external_sync_period_ingests_and_dedupes(client, monkeypatch) -> None:
    user_id = _signup_and_authenticate(client, "external-news@example.com")
    t0 = datetime(2026, 4, 20, 14, 0, tzinfo=UTC)

    def fake_fetch_google_news_items(  # noqa: ANN202
        *,
        instrument: str,
        start_date,  # noqa: ANN001
        end_date,  # noqa: ANN001
        max_items: int,
        language: str,
    ):
        del start_date, end_date, language
        rows = {
            "PETR4": [
                {
                    "instrument": "PETR4",
                    "headline": "Petrobras revisa guidance de investimento para 2026",
                    "source_name": "Reuters",
                    "source_type": "regulated_media",
                    "published_at": t0,
                    "source_url": "https://example.com/news/petr4/1",
                    "language": "pt-BR",
                },
                {
                    "instrument": "PETR4",
                    "headline": "Petrobras confirma agenda de resultados trimestrais",
                    "source_name": "Valor",
                    "source_type": "regulated_media",
                    "published_at": t0.replace(hour=15),
                    "source_url": "https://example.com/news/petr4/2",
                    "language": "pt-BR",
                },
            ],
            "VALE3": [
                {
                    "instrument": "VALE3",
                    "headline": "Vale atualiza guidance de producao para minerio de ferro",
                    "source_name": "Bloomberg",
                    "source_type": "regulated_media",
                    "published_at": t0.replace(day=19, hour=16),
                    "source_url": "https://example.com/news/vale3/1",
                    "language": "pt-BR",
                }
            ],
        }
        return rows.get(instrument, [])[:max_items]

    monkeypatch.setattr(
        "app.services.news_external._fetch_google_news_items",
        fake_fetch_google_news_items,
    )

    payload = {
        "user_id": user_id,
        "start_date": "2026-04-19",
        "end_date": "2026-04-21",
        "instruments": ["PETR4", "VALE3"],
        "max_articles_per_instrument": 80,
        "language": "pt-BR",
    }
    first_response = client.post("/api/news/external/sync-period", json=payload)
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["fetched"] == 3
    assert first_payload["inserted"] == 3
    assert first_payload["duplicates_ignored"] == 0
    assert first_payload["failed"] == 0
    assert first_payload["by_instrument"]["PETR4"] == 2
    assert first_payload["by_instrument"]["VALE3"] == 1

    second_response = client.post("/api/news/external/sync-period", json=payload)
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["fetched"] == 3
    assert second_payload["inserted"] == 0
    assert second_payload["duplicates_ignored"] == 3
    assert second_payload["failed"] == 0

    dashboard_response = client.get(f"/api/dashboard/summary/{user_id}")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    instruments = {row["instrument"] for row in dashboard_payload["latest_news"]}
    assert "PETR4" in instruments
    assert "VALE3" in instruments


def test_news_external_sync_period_rejects_invalid_date_range(client) -> None:
    user_id = _signup_and_authenticate(client, "external-news-invalid-range@example.com")
    response = client.post(
        "/api/news/external/sync-period",
        json={
            "user_id": user_id,
            "start_date": "2026-04-21",
            "end_date": "2026-04-20",
            "instruments": ["PETR4"],
            "max_articles_per_instrument": 20,
            "language": "pt-BR",
        },
    )
    assert response.status_code == 400
    assert "start_date" in response.json()["detail"]

from __future__ import annotations


def test_data_context_refresh_requires_cron_authorization(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")

    response = client.post("/api/ops/data-context-refresh")

    assert response.status_code == 401


def test_data_context_refresh_dry_run_returns_bounded_config(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_USER_ID", "1")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_INSTRUMENTS", "PETR4,VALE3,ITUB4")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_NEWS_LOOKBACK_DAYS", "5")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_MAX_INSTRUMENTS", "2")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_MAX_ARTICLES_PER_INSTRUMENT", "12")

    response = client.post(
        "/api/ops/data-context-refresh?dry_run=true",
        headers={"Authorization": "Bearer cron-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["mode"] == "data_context_refresh"
    assert payload["config"]["user_id"] == 1
    assert payload["config"]["instruments"] == ["PETR4", "VALE3"]
    assert payload["config"]["news_lookback_days"] == 5
    assert payload["config"]["max_articles_per_instrument"] == 12
    assert payload["config"]["run_fundamentals"] is True
    assert payload["config"]["run_news"] is True


def test_data_context_refresh_calls_fundamentals_news_and_returns_gate(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    monkeypatch.setenv("DATA_CONTEXT_REFRESH_USER_ID", "1")
    captured: dict[str, object] = {}

    def fake_fundamentals(
        _db,
        *,
        user_id,
        provider_name,
        instruments,
        only_missing,
        max_instruments,
    ):  # noqa: ANN001, ANN202
        captured["fundamentals"] = {
            "user_id": user_id,
            "provider_name": provider_name,
            "instruments": instruments,
            "only_missing": only_missing,
            "max_instruments": max_instruments,
        }
        return {
            "source": "fake fundamentals",
            "provider_name": provider_name,
            "requested_instruments": len(instruments),
            "selected_instruments": instruments,
            "inserted": 2,
            "duplicates_ignored": 0,
            "failed": 0,
            "by_instrument": {},
        }

    def fake_news(
        _db,
        *,
        user_id,
        start_date,
        end_date,
        instruments,
        max_articles_per_instrument,
        language,
    ):  # noqa: ANN001, ANN202
        captured["news"] = {
            "user_id": user_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "instruments": instruments,
            "max_articles_per_instrument": max_articles_per_instrument,
            "language": language,
        }
        return {
            "source": "fake news",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "instruments": instruments,
            "fetched": 4,
            "inserted": 4,
            "duplicates_ignored": 0,
            "failed": 0,
            "by_instrument": {instrument: 1 for instrument in instruments},
            "sample_headlines": [],
        }

    def fake_gate(_db, **kwargs):  # noqa: ANN001, ANN202
        captured["gate"] = kwargs
        return {
            "generated_at": "2026-05-05T12:00:00+00:00",
            "summary": {
                "gate_status": "pass",
                "passed_checks": 6,
                "failed_checks": 0,
                "total_checks": 6,
                "quality_score_pct": 100.0,
            },
        }

    monkeypatch.setattr("app.main.sync_external_fundamentals", fake_fundamentals)
    monkeypatch.setattr("app.main.sync_external_news_period", fake_news)
    monkeypatch.setattr("app.main.build_data_quality_gate_snapshot", fake_gate)

    response = client.post(
        "/api/ops/data-context-refresh"
        "?instruments=PETR4,VALE3,ITUB4"
        "&max_instruments=2"
        "&news_lookback_days=3"
        "&max_articles_per_instrument=7"
        "&fundamentals_provider=brapi"
        "&fundamentals_only_missing=false"
        "&fundamentals_max_staleness_days=10",
        headers={"Authorization": "Bearer cron-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["mode"] == "data_context_refresh"
    assert payload["fundamentals"]["inserted"] == 2
    assert payload["news"]["inserted"] == 4
    assert payload["data_quality"]["summary"]["gate_status"] == "pass"
    assert captured["fundamentals"] == {
        "user_id": 1,
        "provider_name": "brapi",
        "instruments": ["PETR4", "VALE3"],
        "only_missing": False,
        "max_instruments": 2,
    }
    news_call = dict(captured["news"])
    assert news_call["user_id"] == 1
    assert news_call["instruments"] == ["PETR4", "VALE3"]
    assert news_call["max_articles_per_instrument"] == 7
    assert news_call["language"] == "pt-BR"
    gate_call = dict(captured["gate"])
    assert gate_call["instruments"] == ["PETR4", "VALE3"]
    assert gate_call["fundamentals_max_staleness_days"] == 10
    assert gate_call["news_lookback_days"] == 3

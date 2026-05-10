from __future__ import annotations

import json
from datetime import datetime

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
    assert payload["cron_mode"] == "external_fetches"
    assert payload["cron_policy"] == {
        "allow_external_fetches": True,
        "publish_decisions": False,
    }
    config = dict(captured["config"])
    assert config["user_id"] == 1
    assert config["instruments"] == ["BTCUSDT", "ETHUSDT"]
    assert config["allow_external_fetches"] is True
    assert config["publish_decisions"] is False


def test_microtrades_autopilot_cron_allows_explicit_heavy_mode(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_ENABLED", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_USER_ID", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_CRON_EXTERNAL_FETCHES", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_CRON_PUBLISH_DECISIONS", "1")
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
    assert payload["cron_mode"] == "external_fetches"
    assert payload["cron_policy"] == {
        "allow_external_fetches": True,
        "publish_decisions": True,
    }
    config = dict(captured["config"])
    assert config["allow_external_fetches"] is True
    assert config["publish_decisions"] is True


def test_microtrades_data_refresh_requires_cron_authorization(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    response = client.post("/api/ops/microtrades-data-refresh")
    assert response.status_code == 401


def test_microtrades_data_refresh_uses_bounded_external_fetch_config(client, monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_ENABLED", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_USER_ID", "1")
    monkeypatch.setenv("MICROTRADES_AUTOPILOT_INSTRUMENTS", "BTCUSDT,ETHUSDT")
    captured: dict[str, object] = {}

    def fake_refresh(
        _db,
        *,
        config,
        lookback_hours,
        max_candles_per_instrument,
        run_backfill,
        run_live_ingestion,
    ):  # noqa: ANN001, ANN202
        captured["config"] = dict(config)
        captured["lookback_hours"] = lookback_hours
        captured["max_candles_per_instrument"] = max_candles_per_instrument
        captured["run_backfill"] = run_backfill
        captured["run_live_ingestion"] = run_live_ingestion
        return {
            "status": "success",
            "mode": "data_refresh",
            "run_started_at": "2026-05-05T10:00:00+00:00",
            "run_finished_at": "2026-05-05T10:00:05+00:00",
            "backfill": {"processed_count": 120},
            "live_ingestion": {"processed_count": 2},
            "data_quality": {"summary": {"gate_status": "pass"}},
            "error": None,
        }

    monkeypatch.setattr("app.main.run_microtrades_data_refresh", fake_refresh)

    response = client.post(
        "/api/ops/microtrades-data-refresh?lookback_hours=2&max_candles_per_instrument=75&run_live_ingestion=false",
        headers={"Authorization": "Bearer cron-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["mode"] == "data_refresh"
    config = dict(captured["config"])
    assert config["user_id"] == 1
    assert config["instruments"] == ["BTCUSDT", "ETHUSDT"]
    assert config["allow_external_fetches"] is True
    assert config["publish_decisions"] is False
    assert captured["lookback_hours"] == 2
    assert captured["max_candles_per_instrument"] == 75
    assert captured["run_backfill"] is True
    assert captured["run_live_ingestion"] is False


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


def test_microtrades_autopilot_latest_returns_last_cycle_snapshot(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot-latest@example.com")

    def fake_run(_db, *, config):  # noqa: ANN001, ANN202
        assert config["user_id"] == user_id
        return {
            "status": "partial",
            "error": "Token Finnhub ausente. Etapa live ignorada.",
            "run_started_at": "2026-05-04T10:00:00+00:00",
            "run_finished_at": "2026-05-04T10:00:12+00:00",
            "user_id": user_id,
            "config": {
                "interval": "5m",
                "instruments": ["BTCUSDT", "ETHUSDT"],
            },
            "steps": [
                {"title": "historico", "status": "ok", "meta": "100 candles processados."},
                {"title": "cotacao", "status": "warning", "meta": "Token Finnhub ausente. Etapa live ignorada."},
            ],
            "backfill": {"status": "ok", "processed_count": 100},
            "live_ingestion": {"status": "warning", "processed_count": 0},
            "signal": {"status": "ok", "instrument": "BTCUSDT"},
            "case_study": {"status": "warning"},
            "monitor": {
                "thesis_count": 2,
                "summary": {
                    "monitoring_count": 2,
                    "needs_attention_count": 1,
                },
            },
            "decision": {"status": "created", "decision_id": "dec-42"},
        }

    monkeypatch.setattr("app.main.run_microtrades_autopilot_cycle", fake_run)

    run_response = client.post(
        "/api/microtrades/autopilot/run",
        json={
            "user_id": user_id,
            "instruments": ["BTCUSDT", "ETHUSDT"],
            "interval": "5m",
            "lookback_hours": 72,
            "publish_decisions": True,
        },
    )
    assert run_response.status_code == 200

    latest_response = client.get("/api/microtrades/autopilot/latest")
    assert latest_response.status_code == 200
    payload = latest_response.json()
    assert payload["status"] == "partial"
    assert payload["monitor"]["thesis_count"] == 2
    assert payload["decision"]["status"] == "created"
    assert payload["runtime"]["running"] in {True, False}
    assert payload["worker"]["worker_name"] == "microtrades_autopilot_worker"
    assert payload["worker"]["status"] == "idle"


def test_microtrades_autopilot_latest_runs_cycle_when_runtime_snapshot_is_missing(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot-refresh@example.com")
    captured: dict[str, object] = {}

    def fake_load(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        captured["load_user_id"] = user_id
        captured["load_include_bootstrap"] = include_bundled_bootstrap
        return None

    def fake_build(user_id: int, **kwargs):  # noqa: ANN001, ANN202
        captured["config_user_id"] = user_id
        return {
            "user_id": user_id,
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "provider_name": "finnhub",
            "history_provider_name": "binance",
            "interval": "5m",
            "lookback_hours": 168,
            "max_candles_per_instrument": 1200,
            "horizon_bars": 8,
            "thesis_count": 8,
            "recent_bars_window": 7,
            "auto_recompute_indicators": True,
            "publish_decisions": False,
            "decision_cooldown_minutes": 45,
        }

    def fake_execute(_db, *, config):  # noqa: ANN001, ANN202
        captured["executed_config"] = dict(config)
        return {
            "status": "success",
            "error": None,
            "run_started_at": "2026-05-04T19:30:00+00:00",
            "run_finished_at": "2026-05-04T19:30:12+00:00",
            "user_id": user_id,
            "config": {
                "interval": "5m",
                "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            },
            "steps": [],
            "backfill": {"status": "ok"},
            "live_ingestion": {"status": "warning"},
            "signal": {"status": "ok"},
            "case_study": {"status": "warning"},
            "monitor": {"thesis_count": 1, "summary": {"monitoring_count": 1, "needs_attention_count": 0}},
            "decision": {"status": "skipped"},
        }

    monkeypatch.setattr("app.main.load_latest_microtrades_autopilot_snapshot", fake_load)
    monkeypatch.setattr(
        "app.main.load_latest_current_thesis_monitor",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("app.main._build_default_microtrades_autopilot_config", fake_build)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fake_execute)

    response = client.get("/api/microtrades/autopilot/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["monitor"]["thesis_count"] == 1
    assert captured["load_user_id"] == user_id
    assert captured["load_include_bootstrap"] is False
    assert captured["config_user_id"] == user_id
    assert captured["executed_config"]["publish_decisions"] is False


def test_microtrades_autopilot_latest_rebuilds_when_runtime_snapshot_is_stale(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot-stale@example.com")
    captured: dict[str, object] = {}

    stale_payload = {
        "status": "success",
        "error": None,
        "run_started_at": "2026-05-04T19:30:00+00:00",
        "run_finished_at": "2026-05-04T19:30:12+00:00",
        "user_id": user_id,
        "config": {
            "interval": "5m",
            "instruments": ["BTCUSDT", "ETHUSDT"],
        },
        "steps": [],
        "backfill": {"status": "ok"},
        "live_ingestion": {"status": "warning"},
        "signal": {"status": "ok"},
        "case_study": {"status": "warning"},
        "monitor": {
            "thesis_count": 8,
            "summary": {
                "monitoring_count": 7,
                "needs_attention_count": 1,
            },
        },
        "decision": {"status": "skipped"},
    }

    def fake_load(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        captured["load_user_id"] = user_id
        captured["load_include_bootstrap"] = include_bundled_bootstrap
        return stale_payload

    def fake_build(user_id: int, **kwargs):  # noqa: ANN001, ANN202
        captured["config_user_id"] = user_id
        return {
            "user_id": user_id,
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "provider_name": "finnhub",
            "history_provider_name": "binance",
            "interval": "5m",
            "lookback_hours": 168,
            "max_candles_per_instrument": 1200,
            "horizon_bars": 8,
            "thesis_count": 8,
            "recent_bars_window": 7,
            "auto_recompute_indicators": True,
            "publish_decisions": False,
            "decision_cooldown_minutes": 45,
        }

    def fake_execute(_db, *, config):  # noqa: ANN001, ANN202
        captured["executed_config"] = dict(config)
        return {
            "status": "success",
            "error": None,
            "run_started_at": "2026-05-04T20:59:00+00:00",
            "run_finished_at": "2026-05-04T20:59:12+00:00",
            "user_id": user_id,
            "config": {
                "interval": "5m",
                "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            },
            "steps": [],
            "backfill": {"status": "ok"},
            "live_ingestion": {"status": "warning"},
            "signal": {"status": "ok"},
            "case_study": {"status": "warning"},
            "monitor": {
                "thesis_count": 0,
                "summary": {
                    "monitoring_count": 0,
                    "needs_attention_count": 0,
                    "notes": ["Nao ha dados de mercado frescos para monitorar teses atuais."],
                },
            },
            "decision": {"status": "skipped"},
        }

    monkeypatch.setattr("app.main.load_latest_microtrades_autopilot_snapshot", fake_load)
    monkeypatch.setattr(
        "app.main.load_latest_current_thesis_monitor",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("app.main._build_default_microtrades_autopilot_config", fake_build)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fake_execute)
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-04T21:15:00+00:00"),
    )

    response = client.get("/api/microtrades/autopilot/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["monitor"]["thesis_count"] == 0
    assert payload["monitor"]["summary"]["notes"] == [
        "Nao ha dados de mercado frescos para monitorar teses atuais."
    ]
    assert captured["load_user_id"] == user_id
    assert captured["load_include_bootstrap"] is False
    assert captured["config_user_id"] == user_id
    assert captured["executed_config"]["publish_decisions"] is False


def test_microtrades_autopilot_latest_reuses_fast_snapshot_after_first_rebuild(
    client,
    monkeypatch,
    tmp_path,
) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot-fast-cache@example.com")
    stale_payload = {
        "status": "success",
        "error": None,
        "run_started_at": "2026-05-04T19:30:00+00:00",
        "run_finished_at": "2026-05-04T19:30:12+00:00",
        "user_id": user_id,
        "config": {
            "interval": "5m",
            "instruments": ["BTCUSDT", "ETHUSDT"],
        },
        "steps": [],
        "backfill": {"status": "ok"},
        "live_ingestion": {"status": "warning"},
        "signal": {"status": "ok"},
        "case_study": {"status": "warning"},
        "monitor": {
            "generated_at": "2026-05-04T19:30:10+00:00",
            "thesis_count": 8,
            "summary": {
                "monitoring_count": 7,
                "needs_attention_count": 1,
            },
            "theses": [
                {
                    "instrument": "BTCUSDT",
                    "latest_event_time": "2026-05-04T19:20:00+00:00",
                    "suggested_exit_time": "2026-05-04T19:40:00+00:00",
                }
            ],
        },
        "decision": {"status": "skipped"},
    }
    fresh_payload = {
        "status": "success",
        "error": None,
        "run_started_at": "2026-05-04T21:10:00+00:00",
        "run_finished_at": "2026-05-04T21:10:12+00:00",
        "user_id": user_id,
        "config": {
            "interval": "5m",
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        },
        "steps": [],
        "backfill": {"status": "ok"},
        "live_ingestion": {"status": "warning"},
        "signal": {"status": "ok"},
        "case_study": {"status": "warning"},
        "monitor": {
            "generated_at": "2026-05-04T21:10:10+00:00",
            "thesis_count": 1,
            "summary": {
                "monitoring_count": 1,
                "needs_attention_count": 0,
            },
            "theses": [
                {
                    "instrument": "BTCUSDT",
                    "latest_event_time": "2026-05-04T21:05:00+00:00",
                    "suggested_exit_time": "2026-05-04T21:25:00+00:00",
                }
            ],
        },
        "decision": {"status": "skipped"},
    }
    stale_path = tmp_path / "microtrades_autopilot_latest.json"
    stale_path.write_text(json.dumps(stale_payload), encoding="utf-8")
    call_count = {"run": 0}

    monkeypatch.setattr("app.services.microtrades_autopilot.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "app.main.load_latest_current_thesis_monitor",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-04T21:15:00+00:00"),
    )
    monkeypatch.setattr(
        "app.main._build_default_microtrades_autopilot_config",
        lambda user_id, **kwargs: {
            "user_id": user_id,
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "provider_name": "finnhub",
            "history_provider_name": "binance",
            "interval": "5m",
            "lookback_hours": 168,
            "max_candles_per_instrument": 1200,
            "horizon_bars": 8,
            "thesis_count": 8,
            "recent_bars_window": 7,
            "auto_recompute_indicators": True,
            "allow_external_fetches": False,
            "publish_decisions": False,
            "decision_cooldown_minutes": 45,
        },
    )

    def fake_run(_db, *, config):  # noqa: ANN001, ANN202
        call_count["run"] += 1
        return dict(fresh_payload)

    monkeypatch.setattr("app.main.run_microtrades_autopilot_cycle", fake_run)

    first_response = client.get("/api/microtrades/autopilot/latest")
    second_response = client.get("/api/microtrades/autopilot/latest")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["monitor"]["thesis_count"] == 1
    assert second_response.json()["monitor"]["thesis_count"] == 1
    assert second_response.json()["run_finished_at"] == "2026-05-04T21:10:12+00:00"
    assert call_count["run"] == 1


def test_microtrades_autopilot_latest_reuses_current_monitor_snapshot_when_available(
    client,
    monkeypatch,
) -> None:
    user_id = _authenticate(client, email="microtrades-autopilot-monitor-reuse@example.com")
    captured: dict[str, object] = {}
    stale_payload = {
        "status": "success",
        "error": None,
        "run_started_at": "2026-05-04T19:30:00+00:00",
        "run_finished_at": "2026-05-04T19:30:12+00:00",
        "user_id": user_id,
        "config": {
            "interval": "5m",
            "instruments": ["BTCUSDT", "ETHUSDT"],
        },
        "steps": [],
        "backfill": {"status": "ok"},
        "live_ingestion": {"status": "warning"},
        "signal": {"status": "ok"},
        "case_study": {"status": "warning"},
        "monitor": {
            "generated_at": "2026-05-04T19:30:10+00:00",
            "thesis_count": 8,
            "summary": {
                "monitoring_count": 7,
                "needs_attention_count": 1,
            },
            "theses": [
                {
                    "instrument": "BTCUSDT",
                    "latest_event_time": "2026-05-04T19:20:00+00:00",
                    "suggested_exit_time": "2026-05-04T19:40:00+00:00",
                }
            ],
        },
        "decision": {"status": "skipped"},
    }
    current_monitor_payload = {
        "generated_at": "2026-05-04T21:12:00+00:00",
        "user_id": user_id,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 1,
        "scan_scope": {
            "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "candidate_count": 1,
            "current_candidate_count": 1,
        },
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 1,
            "avg_unrealized_financial_pct": 0.2,
            "executive_status_counts": {"mantida": 1},
            "needs_attention_count": 0,
        },
        "theses": [
            {
                "thesis_id": "TH-BTCUSDT-LIVE-0001",
                "instrument": "BTCUSDT",
                "latest_event_time": "2026-05-04T21:05:00+00:00",
                "suggested_exit_time": "2026-05-04T21:25:00+00:00",
            }
        ],
        "disclaimer": "simulado",
    }

    def fake_load_autopilot(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        captured["autopilot_user_id"] = user_id
        captured["autopilot_include_bootstrap"] = include_bundled_bootstrap
        return stale_payload

    def fake_load_monitor(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        captured["monitor_user_id"] = user_id
        captured["monitor_include_bootstrap"] = include_bundled_bootstrap
        return current_monitor_payload

    monkeypatch.setattr("app.main.load_latest_microtrades_autopilot_snapshot", fake_load_autopilot)
    monkeypatch.setattr("app.main.load_latest_current_thesis_monitor", fake_load_monitor)
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-04T21:15:00+00:00"),
    )
    monkeypatch.setattr(
        "app.main._execute_microtrades_autopilot",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria recalcular quando o current monitor ja esta fresco")
        ),
    )

    response = client.get("/api/microtrades/autopilot/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["monitor"]["thesis_count"] == 1
    assert payload["run_finished_at"] == "2026-05-04T21:12:00+00:00"
    assert payload["config"]["interval"] == "5m"
    assert payload["config"]["instruments"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert payload["decision"]["status"] == "skipped"
    assert captured["autopilot_user_id"] == user_id
    assert captured["autopilot_include_bootstrap"] is False
    assert captured["monitor_user_id"] == user_id
    assert captured["monitor_include_bootstrap"] is False

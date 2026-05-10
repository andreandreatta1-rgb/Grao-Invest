from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _authenticate(client: TestClient, *, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Current Monitor Lab",
            "full_name": "User Current Monitor",
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


def test_current_monitor_latest_rebuilds_from_autopilot_when_runtime_snapshot_is_missing(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="current-monitor-refresh@example.com")
    captured: dict[str, object] = {}
    monkeypatch.setenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", "0")

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

    monitor_payload = {
        "generated_at": "2026-05-04T19:40:00+00:00",
        "user_id": user_id,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 1, "current_candidate_count": 1},
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
                "direction": "bullish",
                "why_thesis": ["momento_bullish_2.80pct"],
                "thesis_raised_at": "2026-05-04T19:40:00+00:00",
                "suggested_entry_time": "2026-05-04T19:40:00+00:00",
                "suggested_exit_time": "2026-05-04T20:20:00+00:00",
                "entry_price": 65000.0,
                "target_price": 65520.0,
                "stop_price": 64688.0,
                "latest_price": 65000.0,
                "latest_event_time": "2026-05-04T19:40:00+00:00",
                "monitor_status": "monitoring",
                "suggested_action": "manter_monitoramento",
                "expected_financial_pct": 0.8,
                "unrealized_financial_pct": 0.0,
                "confidence_tese_pct": 74.0,
                "confidence_now_pct": 73.0,
                "confidence_delta_pct": -1.0,
                "support_rate_pct": 61.0,
                "technical_support_pct": 68.0,
                "fundamental_support_pct": 55.0,
                "news_support_pct": 52.0,
                "geo_oil_support_pct": 50.0,
                "fundamental_available": True,
                "news_available": True,
                "geo_oil_available": False,
                "progress_to_target_pct": 0.0,
                "distance_to_stop_pct": 0.48,
                "executive_status": "mantida",
                "executive_status_label": "Mantida",
                "executive_action": "manter_monitoramento",
                "thesis_validity": "valida",
                "revaluation_reason": "teste",
                "next_trigger": "acompanhar",
                "learning_signal": "neutro",
                "operation_revaluation": {
                    "executive_status": "mantida",
                    "executive_status_label": "Mantida",
                    "thesis_validity": "valida",
                    "suggested_action": "manter_monitoramento",
                    "confidence_initial_pct": 74.0,
                    "confidence_now_pct": 73.0,
                    "confidence_delta_pct": -1.0,
                    "next_trigger": "acompanhar",
                    "revaluation_reason": "teste",
                    "learning_signal": "neutro",
                    "risk_flags": [],
                    "postmortem_penalty_points": 0.0,
                    "matched_postmortem_rules": [],
                    "blocked_by_postmortem": False,
                },
                "monitoring_events": [
                    {
                        "event_time": "2026-05-04T19:40:00+00:00",
                        "event_type": "entry_snapshot",
                        "severity": "info",
                        "message": "Operacao estruturada iniciada em simulacao.",
                        "market_price": 65000.0,
                    }
                ],
            }
        ],
        "disclaimer": "simulado",
    }

    def fake_execute(_db, *, config):  # noqa: ANN001, ANN202
        captured["executed_config"] = dict(config)
        return {
            "status": "success",
            "error": None,
            "run_started_at": "2026-05-04T19:40:00+00:00",
            "run_finished_at": "2026-05-04T19:40:12+00:00",
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
            "monitor": monitor_payload,
            "decision": {"status": "skipped"},
        }

    monkeypatch.setattr("app.main.load_latest_current_thesis_monitor", fake_load)
    monkeypatch.setattr("app.main._build_default_microtrades_autopilot_config", fake_build)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fake_execute)
    monkeypatch.setenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", "0")

    response = client.get("/api/theses/current-monitor/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["thesis_count"] == 1
    assert payload["theses"][0]["instrument"] == "BTCUSDT"
    assert captured["load_user_id"] == user_id
    assert captured["load_include_bootstrap"] is False
    assert captured["config_user_id"] == user_id
    assert captured["executed_config"]["publish_decisions"] is False


def test_current_monitor_latest_uses_dashboard_seed_when_snapshot_is_stale(
    client,
    monkeypatch,
) -> None:
    user_id = _authenticate(client, email="current-monitor-seed-fallback@example.com")

    stale_monitor_payload = {
        "generated_at": "2026-05-07T00:50:13+00:00",
        "user_id": user_id,
        "thesis_count": 1,
        "scan_scope": {
            "instruments": ["BTCUSDT"],
            "candidate_count": 1,
            "current_candidate_count": 1,
        },
        "summary": {"monitoring_count": 1},
        "theses": [
            {
                "thesis_id": "TH-BTCUSDT-STALE-0001",
                "instrument": "BTCUSDT",
                "latest_event_time": "2026-05-07T00:30:00+00:00",
            }
        ],
    }

    dashboard_seed = {
        "generated_at": "2026-05-08T12:03:06+00:00",
        "thesis_open_operations": [
            {
                "phase": "pos_go_live",
                "thesis_id": "TH-PETR4-range-0007",
                "thesis_raised_at": "2026-05-07T00:00:00+00:00",
                "action": "PETR4",
                "thesis_reason": "Tese atual publicada pelo seed operacional.",
                "expected_result_pct": 0.8627,
                "operation_plan": "Neutra ate 2026-05-17.",
                "structured_operation": "Iron Condor | ganho max 2.40% | perda max 3.80%",
                "entry_price_brl": 47.27,
                "current_price_brl": 46.22,
                "latest_price_at": "2026-05-07T00:00:00+00:00",
                "planned_exit_at": "2026-05-17",
                "exit_rule": "Reavaliar na proxima barra.",
                "status": "Aberta - Atencao",
                "outcome": "Atencao",
                "moment_result_pct": -1.0672,
                "learning_note": "Aprendizado registrado.",
                "is_open": True,
            },
            {
                "phase": "historico",
                "thesis_id": "TH-OLD",
                "action": "VALE3",
                "is_open": False,
            },
        ],
    }

    def fake_load(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        return stale_monitor_payload

    def fake_seed_loader(filename: str):  # noqa: ANN202
        assert filename == "dashboard_seed.json"
        return dashboard_seed

    def fail_execute(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError(
            "autopilot should not run when production dashboard seed has current operations"
        )

    monkeypatch.setenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", "1")
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-08T12:10:00+00:00"),
    )
    monkeypatch.setattr("app.main.load_latest_current_thesis_monitor", fake_load)
    monkeypatch.setattr("app.main._load_runtime_or_bundled_json_payload", fake_seed_loader)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fail_execute)

    response = client.get("/api/theses/current-monitor/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_quality"]["status"] == "fresh"
    assert payload["data_quality"]["reason"] == "dashboard_seed_current_operations"
    assert payload["thesis_count"] == 1
    assert payload["scan_scope"]["fresh_instruments"] == ["PETR4"]
    assert payload["theses"][0]["instrument"] == "PETR4"
    assert payload["theses"][0]["monitor_status"] == "monitoring"


def test_current_monitor_latest_uses_dashboard_seed_by_default_when_snapshot_is_stale(
    client,
    monkeypatch,
) -> None:
    user_id = _authenticate(client, email="current-monitor-default-seed@example.com")
    stale_monitor_payload = {
        "generated_at": "2026-05-07T00:50:13+00:00",
        "user_id": user_id,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["BTCUSDT"]},
        "summary": {"monitoring_count": 1},
        "theses": [
            {
                "thesis_id": "TH-BTCUSDT-STALE-0001",
                "instrument": "BTCUSDT",
                "latest_event_time": "2026-05-07T00:30:00+00:00",
            }
        ],
    }
    dashboard_seed = {
        "generated_at": "2026-05-08T12:03:06+00:00",
        "thesis_open_operations": [
            {
                "phase": "pos_go_live",
                "thesis_id": "TH-PETR4-range-0007",
                "thesis_raised_at": "2026-05-07T00:00:00+00:00",
                "action": "PETR4",
                "expected_result_pct": 0.8627,
                "operation_plan": "Neutra ate 2026-05-17.",
                "structured_operation": "Iron Condor",
                "entry_price_brl": 47.27,
                "current_price_brl": 46.22,
                "latest_price_at": "2026-05-07T00:00:00+00:00",
                "exit_rule": "Reavaliar na proxima barra.",
                "status": "Aberta - Atencao",
                "outcome": "Atencao",
                "moment_result_pct": -1.0672,
                "is_open": True,
            },
        ],
    }

    def fake_load(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        return stale_monitor_payload

    def fake_seed_loader(filename: str):  # noqa: ANN202
        assert filename == "dashboard_seed.json"
        return dashboard_seed

    def fail_execute(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("autopilot should not run while seed fallback is enabled")

    monkeypatch.delenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", raising=False)
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-08T12:10:00+00:00"),
    )
    monkeypatch.setattr("app.main.load_latest_current_thesis_monitor", fake_load)
    monkeypatch.setattr("app.main._load_runtime_or_bundled_json_payload", fake_seed_loader)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fail_execute)

    response = client.get("/api/theses/current-monitor/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_quality"]["status"] == "fresh"
    assert payload["data_quality"]["reason"] == "dashboard_seed_current_operations"
    assert payload["theses"][0]["instrument"] == "PETR4"


def test_current_monitor_latest_rebuilds_when_runtime_snapshot_is_stale(client, monkeypatch) -> None:
    user_id = _authenticate(client, email="current-monitor-stale@example.com")
    captured: dict[str, object] = {}
    monkeypatch.setenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", "0")

    stale_monitor_payload = {
        "generated_at": "2026-05-04T19:40:00+00:00",
        "user_id": user_id,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 1, "current_candidate_count": 1},
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
                "thesis_id": "TH-BTCUSDT-STALE-0001",
                "instrument": "BTCUSDT",
                "direction": "bullish",
                "why_thesis": ["momento_bullish_1.80pct"],
                "thesis_raised_at": "2026-05-04T19:00:00+00:00",
                "suggested_entry_time": "2026-05-04T19:00:00+00:00",
                "suggested_exit_time": "2026-05-04T19:40:00+00:00",
                "entry_price": 65000.0,
                "target_price": 65520.0,
                "stop_price": 64688.0,
                "latest_price": 65010.0,
                "latest_event_time": "2026-05-04T19:20:00+00:00",
                "monitor_status": "monitoring",
                "suggested_action": "manter_monitoramento",
                "expected_financial_pct": 0.8,
                "unrealized_financial_pct": 0.1,
                "confidence_tese_pct": 74.0,
                "confidence_now_pct": 73.0,
                "confidence_delta_pct": -1.0,
                "support_rate_pct": 61.0,
                "technical_support_pct": 68.0,
                "fundamental_support_pct": 55.0,
                "news_support_pct": 52.0,
                "geo_oil_support_pct": 50.0,
                "fundamental_available": True,
                "news_available": True,
                "geo_oil_available": False,
                "progress_to_target_pct": 0.0,
                "distance_to_stop_pct": 0.48,
                "executive_status": "mantida",
                "executive_status_label": "Mantida",
                "executive_action": "manter_monitoramento",
                "thesis_validity": "valida",
                "revaluation_reason": "teste",
                "next_trigger": "acompanhar",
                "learning_signal": "neutro",
                "operation_revaluation": {
                    "executive_status": "mantida",
                    "executive_status_label": "Mantida",
                    "thesis_validity": "valida",
                    "suggested_action": "manter_monitoramento",
                    "confidence_initial_pct": 74.0,
                    "confidence_now_pct": 73.0,
                    "confidence_delta_pct": -1.0,
                    "next_trigger": "acompanhar",
                    "revaluation_reason": "teste",
                    "learning_signal": "neutro",
                    "risk_flags": [],
                    "postmortem_penalty_points": 0.0,
                    "matched_postmortem_rules": [],
                    "blocked_by_postmortem": False,
                },
                "monitoring_events": [
                    {
                        "event_time": "2026-05-04T19:00:00+00:00",
                        "event_type": "entry_snapshot",
                        "severity": "info",
                        "message": "Operacao estruturada iniciada em simulacao.",
                        "market_price": 65000.0,
                    }
                ],
            }
        ],
        "disclaimer": "simulado",
    }

    def fake_load(_db, *, user_id, include_bundled_bootstrap=True):  # noqa: ANN001, ANN202
        captured["load_user_id"] = user_id
        captured["load_include_bootstrap"] = include_bundled_bootstrap
        return stale_monitor_payload

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

    fresh_monitor_payload = {
        "generated_at": "2026-05-04T21:14:00+00:00",
        "user_id": user_id,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 0,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 0, "current_candidate_count": 0},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 0,
            "avg_unrealized_financial_pct": 0.0,
            "executive_status_counts": {},
            "needs_attention_count": 0,
            "notes": ["Nao ha dados de mercado frescos para monitorar teses atuais."],
        },
        "theses": [],
        "disclaimer": "simulado",
    }

    def fake_execute(_db, *, config):  # noqa: ANN001, ANN202
        captured["executed_config"] = dict(config)
        return {
            "status": "success",
            "error": None,
            "run_started_at": "2026-05-04T21:14:00+00:00",
            "run_finished_at": "2026-05-04T21:14:12+00:00",
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
            "monitor": fresh_monitor_payload,
            "decision": {"status": "skipped"},
        }

    monkeypatch.setattr("app.main.load_latest_current_thesis_monitor", fake_load)
    monkeypatch.setattr("app.main._build_default_microtrades_autopilot_config", fake_build)
    monkeypatch.setattr("app.main._execute_microtrades_autopilot", fake_execute)
    monkeypatch.setenv("DASHBOARD_SEED_CURRENT_MONITOR_FALLBACK", "0")
    monkeypatch.setattr(
        "app.main.utc_now",
        lambda: datetime.fromisoformat("2026-05-04T21:15:00+00:00"),
    )

    response = client.get("/api/theses/current-monitor/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["thesis_count"] == 1
    assert payload["theses"][0]["thesis_id"] == "TH-BTCUSDT-STALE-0001"
    assert payload["summary"]["notes"] == [
        "Dados de mercado sem frescor; mantendo ultimo monitor valido."
    ]
    assert payload["data_quality"]["status"] == "stale_reused"
    assert captured["load_user_id"] == user_id
    assert captured["load_include_bootstrap"] is False
    assert captured["config_user_id"] == user_id
    assert captured["executed_config"]["publish_decisions"] is False

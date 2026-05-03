from __future__ import annotations

import json

import pytest
from app.main import AUTH_DISABLED


def test_dashboard_summary_closes_overdue_current_operation(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monitor_payload = {
        "generated_at": "2026-05-03T12:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 20,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["PETR4"]},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 1,
            "avg_unrealized_financial_pct": -0.6,
            "executive_status_counts": {},
            "needs_attention_count": 0,
        },
        "theses": [
            {
                "thesis_id": "TH-PETR4-bullish-123",
                "instrument": "PETR4",
                "direction": "bullish",
                "why_thesis": ["momento_alta"],
                "reason_category": "grafico/tecnico",
                "thesis_raised_at": "2026-04-20T10:00:00+00:00",
                "suggested_entry_time": "2026-04-20T10:00:00+00:00",
                "suggested_exit_time": "2026-04-22T10:00:00+00:00",
                "entry_price": 40.0,
                "target_price": 42.0,
                "stop_price": 38.5,
                "suggested_operation": {
                    "strategy_id": "BULL_CALL_SPREAD",
                    "strategy_name": "Bull Call Spread",
                    "max_gain_pct": 5.4,
                    "max_loss_pct": 2.2,
                },
                "latest_price": 40.2,
                "latest_event_time": "2026-05-03T12:00:00+00:00",
                "monitor_status": "monitoring",
                "suggested_action": "manter_monitoramento",
                "expected_financial_pct": 3.1,
                "unrealized_financial_pct": 0.4,
                "confidence_tese_pct": 72.0,
                "confidence_now_pct": 68.0,
                "confidence_delta_pct": -4.0,
                "support_rate_pct": 40.0,
                "technical_support_pct": 70.0,
                "fundamental_support_pct": 75.0,
                "news_support_pct": 65.0,
                "geo_oil_support_pct": 0.0,
                "fundamental_available": True,
                "news_available": True,
                "geo_oil_available": False,
                "progress_to_target_pct": 10.0,
                "distance_to_stop_pct": 4.25,
                "executive_status": "mantida",
                "executive_status_label": "Mantida",
                "executive_action": "manter_monitoramento",
                "thesis_validity": "valida",
                "revaluation_reason": "Sem eventos de encerramento.",
                "next_trigger": "Reavaliar na proxima barra.",
                "learning_signal": "Sem aprendizado adicional.",
                "operation_revaluation": {
                    "executive_status": "mantida",
                    "executive_status_label": "Mantida",
                    "thesis_validity": "valida",
                    "suggested_action": "manter_monitoramento",
                    "confidence_initial_pct": 72.0,
                    "confidence_now_pct": 68.0,
                    "confidence_delta_pct": -4.0,
                    "next_trigger": "Reavaliar na proxima barra.",
                    "revaluation_reason": "Sem eventos de encerramento.",
                    "learning_signal": "Sem aprendizado adicional.",
                    "risk_flags": [],
                    "postmortem_penalty_points": 0.0,
                    "matched_postmortem_rules": [],
                    "blocked_by_postmortem": False,
                },
                "monitoring_events": [
                    {
                        "event_time": "2026-04-20T10:00:00+00:00",
                        "event_type": "entry_snapshot",
                        "severity": "info",
                        "message": "Entrada da simulacao.",
                        "market_price": 40.0,
                    }
                ],
            }
        ],
        "disclaimer": "simulado",
    }
    (runtime_dir / "current_thesis_monitor_latest.json").write_text(
        json.dumps(monitor_payload),
        encoding="utf-8",
    )

    original_data_dir = main_module.data_dir
    original_bundled_data_dir = main_module.bundled_data_dir
    main_module.data_dir = runtime_dir
    main_module.bundled_data_dir = runtime_dir
    try:
        response = client.get("/api/dashboard/summary/1")
        assert response.status_code == 200
        payload = response.json()
    finally:
        main_module.data_dir = original_data_dir
        main_module.bundled_data_dir = original_bundled_data_dir

    current_rows = [row for row in payload["thesis_open_operations"] if row["phase"] == "pos_go_live"]
    assert len(current_rows) == 1
    row = current_rows[0]
    assert row["status"] == "Fechada"
    assert row["outcome"] == "Tempo"
    assert row["is_open"] is False

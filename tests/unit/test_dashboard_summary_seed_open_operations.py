from __future__ import annotations

import json

import pytest
from app.main import AUTH_DISABLED


def test_dashboard_summary_promotes_seed_open_operations_over_thin_vercel_runtime(
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
        "generated_at": "2026-05-08T12:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 2000,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 1},
        "summary": {"target_hits": 0, "stop_alerts": 0, "monitoring_count": 1},
        "theses": [
            {
                "thesis_id": "TH-BTCUSDT-runtime",
                "instrument": "BTCUSDT",
                "direction": "range",
                "thesis_raised_at": "2026-05-08T11:55:00+00:00",
                "suggested_entry_time": "2026-05-08T11:55:00+00:00",
                "suggested_exit_time": "2026-05-08T12:35:00+00:00",
                "entry_price": 100.0,
                "target_price": 100.0,
                "stop_price": 98.5,
                "range_lower_price": 98.5,
                "range_upper_price": 101.5,
                "latest_price": 100.5,
                "latest_event_time": "2026-05-08T12:00:00+00:00",
                "monitor_status": "monitoring",
                "expected_financial_pct": 0.8,
                "unrealized_financial_pct": 0.2,
                "suggested_operation": {
                    "strategy_id": "IRON_CONDOR",
                    "strategy_name": "Iron Condor",
                    "max_gain_pct": 2.4,
                    "max_loss_pct": 3.8,
                },
                "operation_revaluation": {
                    "executive_status": "mantida",
                    "executive_status_label": "Mantida",
                    "next_trigger": "Reavaliar na proxima barra.",
                    "learning_signal": "Sem aprendizado adicional.",
                },
                "monitoring_events": [],
            }
        ],
        "disclaimer": "simulado",
    }
    seed_payload = {
        "generated_at": "2026-05-08T12:05:00+00:00",
        "thesis_history_overview": {"total_tested": 10},
        "historical_analysis_summary": {"thesis_count": 10},
        "thesis_executive_summary": {},
        "thesis_open_operations": [
            {"thesis_id": "seed-1", "thesis_number": 3970, "action": "PETR4", "phase": "pos_go_live"},
            {"thesis_id": "seed-2", "thesis_number": 3982, "action": "BTCUSDT", "phase": "pos_go_live"},
        ],
    }
    (runtime_dir / "current_thesis_monitor_latest.json").write_text(
        json.dumps(monitor_payload),
        encoding="utf-8",
    )
    (runtime_dir / "dashboard_seed.json").write_text(
        json.dumps(seed_payload),
        encoding="utf-8",
    )

    original_data_dir = main_module.data_dir
    original_bundled_data_dir = main_module.bundled_data_dir
    monkeypatch.setenv("VERCEL", "1")
    main_module.data_dir = runtime_dir
    main_module.bundled_data_dir = runtime_dir
    try:
        response = client.get("/api/dashboard/summary/1")
        assert response.status_code == 200
        payload = response.json()
    finally:
        main_module.data_dir = original_data_dir
        main_module.bundled_data_dir = original_bundled_data_dir

    assert [item["thesis_id"] for item in payload["thesis_open_operations"]] == [
        "seed-1",
        "seed-2",
    ]
    assert [item["thesis_number"] for item in payload["thesis_open_operations"]] == [
        3970,
        3982,
    ]

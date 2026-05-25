from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.main import AUTH_DISABLED, _select_dashboard_data_quality_gate


def test_dashboard_summary_exposes_ops_health(client, tmp_path) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ops_health = {
        "generated_at": "2026-05-08T03:00:00+00:00",
        "user_id": 1,
        "status": "blocked",
        "message": "Feed de mercado stale.",
        "stages": {
            "market_feed": {
                "status": "blocked",
                "message": "Feed de mercado stale.",
            }
        },
        "recommended_actions": ["Atualizar feed B3/Cripto."],
    }
    (runtime_dir / "ops_health_latest.json").write_text(
        json.dumps(ops_health),
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

    assert payload["ops_health"] == ops_health


def test_dashboard_summary_exposes_quality_artifacts_from_runtime_files(
    client,
    tmp_path,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ops_health = {
        "generated_at": "2026-05-09T03:00:00+00:00",
        "user_id": 1,
        "status": "ok",
        "message": "Ciclo operacional saudavel.",
        "stages": {
            "market_feed": {
                "fronts": {
                    "b3": {"age_days": 0.1, "max_age_days": 4},
                    "crypto": {"age_days": 0.01, "max_age_days": 1},
                }
            }
        },
    }
    data_quality_gate = {
        "generated_at": "2026-05-09T03:00:00+00:00",
        "summary": {
            "gate_status": "pass",
            "failed_checks": 0,
            "quality_score_pct": 100.0,
        },
    }
    dashboard_seed = {
        "thesis_history_overview": {"total_tested": 3, "success_rate_pct": 66.67},
        "historical_analysis_summary": {"thesis_count": 3},
        "thesis_open_operations": [
            {
                "thesis_id": "TH-PETR4-bullish-001",
                "action": "PETR4",
                "phase": "historico",
                "status": "Fechada",
                "is_open": False,
                "moment_result_pct": 2.1,
            },
            {
                "thesis_id": "TH-BTCUSDT-range-001",
                "action": "BTCUSDT",
                "phase": "historico",
                "status": "Fechada",
                "is_open": False,
                "moment_result_pct": 1.2,
            },
            {
                "thesis_id": "IM-RADAR-1",
                "front": "imoveis",
                "action": "Apto Centro",
                "phase": "historico",
                "status": "Fechada",
                "is_open": False,
                "moment_result_pct": -2.0,
                "real_estate_analysis": {"score": 63, "confidence": 51},
            },
        ],
    }
    (runtime_dir / "ops_health_latest.json").write_text(json.dumps(ops_health), encoding="utf-8")
    (runtime_dir / "data_quality_gate_latest.json").write_text(
        json.dumps(data_quality_gate),
        encoding="utf-8",
    )
    (runtime_dir / "dashboard_seed.json").write_text(
        json.dumps(dashboard_seed),
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

    assert payload["ops_health"] == ops_health
    assert payload["data_quality_gate"] == data_quality_gate
    assert payload["front_overview"]["b3"]["total_tested"] == 1
    assert payload["front_overview"]["crypto"]["total_tested"] == 1
    assert payload["front_overview"]["real_estate"]["total_tested"] == 1
    assert payload["front_overview"]["real_estate"]["radar_total"] == 1
    assert payload["front_overview"]["real_estate"]["open_count"] == 0
    assert payload["front_overview"]["real_estate"]["closed_count"] == 1
    assert payload["front_overview"]["real_estate"]["counting_policy"] == "radar_candidates"


def test_dashboard_summary_promotes_seed_data_quality_when_vercel_runtime_is_thin(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    seed_quality = {
        "generated_at": "2026-05-09T03:00:00+00:00",
        "summary": {
            "gate_status": "pass",
            "failed_checks": 0,
            "quality_score_pct": 100.0,
        },
    }
    dashboard_seed = {
        "thesis_history_overview": {"total_tested": 879, "success_rate_pct": 76.2},
        "historical_analysis_summary": {"thesis_count": 879},
        "data_quality_gate": seed_quality,
        "front_overview": {
            "b3": {"total_tested": 800, "success_rate_pct": 76.0},
            "crypto": {"total_tested": 67, "success_rate_pct": 71.0},
            "real_estate": {"total_tested": 12, "success_rate_pct": 12.5},
        },
        "thesis_open_operations": [
            {
                "thesis_id": "TH-PETR4-bullish-001",
                "action": "PETR4",
                "phase": "historico",
                "status": "Fechada",
                "is_open": False,
                "moment_result_pct": 2.1,
            }
        ],
    }
    (runtime_dir / "dashboard_seed.json").write_text(
        json.dumps(dashboard_seed),
        encoding="utf-8",
    )
    (runtime_dir / "ops_health_latest.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "stages": {
                    "market_feed": {
                        "fronts": {
                            "b3": {"age_days": 0.1, "max_age_days": 4},
                            "crypto": {"age_days": 0.01, "max_age_days": 1},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_gate(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "summary": {
                "gate_status": "fail",
                "failed_checks": 3,
                "quality_score_pct": 50.0,
            }
        }

    original_data_dir = main_module.data_dir
    original_bundled_data_dir = main_module.bundled_data_dir
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(main_module, "build_data_quality_gate_snapshot", fake_gate)
    main_module.data_dir = runtime_dir
    main_module.bundled_data_dir = runtime_dir
    try:
        response = client.get("/api/dashboard/summary/1")
        assert response.status_code == 200
        payload = response.json()
    finally:
        main_module.data_dir = original_data_dir
        main_module.bundled_data_dir = original_bundled_data_dir

    assert payload["data_quality_gate"] == seed_quality
    assert payload["front_overview"]["b3"]["total_tested"] == 812
    assert payload["front_overview"]["b3"]["total_tested"] + payload["front_overview"]["crypto"]["total_tested"] == 879


def test_dashboard_summary_normalizes_seed_front_overview_to_historical_basis(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    dashboard_seed = {
        "thesis_history_overview": {"total_tested": 1168, "success_rate_pct": 76.2},
        "historical_analysis_summary": {"thesis_count": 1168},
        "data_quality_gate": {
            "summary": {
                "gate_status": "pass",
                "failed_checks": 0,
                "quality_score_pct": 100.0,
            },
        },
        "front_overview": {
            "b3": {
                "total_tested": 1173,
                "resolved_count": 1166,
                "success_rate_pct": 76.16,
                "counting_policy": "resolved_historical",
            },
            "crypto": {
                "total_tested": 2,
                "resolved_count": 2,
                "success_rate_pct": 100.0,
                "counting_policy": "resolved_historical",
            },
            "real_estate": {
                "total_tested": 12,
                "resolved_count": 8,
                "success_rate_pct": 12.5,
                "counting_policy": "radar_candidates",
            },
        },
        "thesis_open_operations": [],
    }
    (runtime_dir / "dashboard_seed.json").write_text(
        json.dumps(dashboard_seed),
        encoding="utf-8",
    )
    (runtime_dir / "ops_health_latest.json").write_text(
        json.dumps({"status": "ok"}),
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

    fronts = payload["front_overview"]
    assert fronts["b3"]["total_tested"] == 1166
    assert fronts["crypto"]["total_tested"] == 2
    assert fronts["real_estate"]["total_tested"] == 12
    assert fronts["real_estate"]["radar_total"] == 12
    assert fronts["real_estate"]["open_count"] == 4
    assert fronts["real_estate"]["closed_count"] == 8
    assert fronts["real_estate"]["counting_policy"] == "radar_candidates"
    assert fronts["b3"]["total_tested"] + fronts["crypto"]["total_tested"] == 1168


def test_data_quality_selector_prefers_passed_seed_on_vercel_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_quality = {
        "summary": {
            "gate_status": "fail",
            "failed_checks": 3,
            "quality_score_pct": 50.0,
        }
    }
    seed_quality = {
        "summary": {
            "gate_status": "pass",
            "failed_checks": 0,
            "quality_score_pct": 100.0,
        }
    }

    monkeypatch.setenv("VERCEL", "1")

    selected = _select_dashboard_data_quality_gate(
        runtime_quality,
        {"data_quality_gate": seed_quality},
        None,
    )

    assert selected == seed_quality


def test_data_quality_selector_prefers_passed_latest_when_runtime_fails_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_quality = {
        "summary": {
            "gate_status": "fail",
            "failed_checks": 1,
            "quality_score_pct": 83.33,
        }
    }
    seed_quality = {
        "summary": {
            "gate_status": "pass",
            "failed_checks": 0,
            "quality_score_pct": 100.0,
        }
    }
    latest_quality = {
        "summary": {
            "gate_status": "pass",
            "failed_checks": 0,
            "quality_score_pct": 100.0,
        },
        "source": "data_quality_gate_latest",
    }

    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("DASHBOARD_SEED_CANONICAL_HISTORY", raising=False)

    selected = _select_dashboard_data_quality_gate(
        runtime_quality,
        {"data_quality_gate": seed_quality},
        latest_quality,
    )

    assert selected == latest_quality


def test_vercel_deploy_includes_operational_quality_artifacts() -> None:
    ignore_rules = Path(".vercelignore").read_text(encoding="utf-8")

    assert "!data/ops_health_latest.json" in ignore_rules
    assert "!data/data_quality_gate_latest.json" in ignore_rules

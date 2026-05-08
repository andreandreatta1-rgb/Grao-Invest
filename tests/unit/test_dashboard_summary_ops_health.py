from __future__ import annotations

import json

import pytest
from app.main import AUTH_DISABLED


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

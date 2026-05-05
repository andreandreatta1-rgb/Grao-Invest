from __future__ import annotations

import pytest
from app.main import AUTH_DISABLED


def test_dashboard_summary_turns_real_estate_candidates_into_thesis_rows(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    active_response = client.post(
        "/api/real-estate/candidates",
        json={
            "title": "Apto Caixa Sao Miguel",
            "source_url": "https://example.com/caixa-sao-miguel",
            "origin": "Caixa Venda Online",
            "strategy": "Leilao/venda online",
            "city": "Sao Paulo",
            "neighborhood": "Sao Miguel Paulista",
            "property_type": "Apartamento",
            "asking_price": 118465.05,
            "appraisal_value": 196000.0,
            "market_value_estimate": 196000.0,
            "estimated_sale_conservative": 176000.0,
            "estimated_sale_base": 196000.0,
            "renovation_type": "leve",
            "renovation_budget": 17000.0,
            "carrying_months": 7,
            "monthly_carrying_cost": 850.0,
            "acquisition_costs": 7900.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 54538.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "has_edital": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 1,
            "rent_comparables_count": 1,
            "plan_a": "Treinar leitura de edital e preco maximo antes de qualquer lance.",
            "plan_b": "Descartar se ocupado ou se debitos consumirem a margem.",
        },
    )
    assert active_response.status_code == 200

    discarded_response = client.post(
        "/api/real-estate/candidates",
        json={
            "title": "Apto Mercado Colonia",
            "source_url": "https://example.com/mercado-colonia",
            "origin": "VivaReal",
            "strategy": "House flipping leve",
            "city": "Sao Paulo",
            "neighborhood": "Colonia Zona Leste",
            "property_type": "Apartamento",
            "asking_price": 215000.0,
            "market_value_estimate": 240000.0,
            "estimated_sale_conservative": 225000.0,
            "estimated_sale_base": 240000.0,
            "renovation_type": "leve",
            "renovation_budget": 18000.0,
            "carrying_months": 5,
            "monthly_carrying_cost": 1100.0,
            "acquisition_costs": 12000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 78000.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 2,
            "rent_comparables_count": 2,
            "plan_a": "Validar anuncio e tentar desconto antes de proposta.",
            "plan_b": "Usar apenas como comparavel se margem conservadora continuar negativa.",
        },
    )
    assert discarded_response.status_code == 200

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
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

    real_estate_rows = [
        row for row in payload["thesis_open_operations"] if row.get("front") == "imoveis"
    ]
    assert len(real_estate_rows) == 2

    active_row = next(row for row in real_estate_rows if row["action"] == "Apto Caixa Sao Miguel")
    assert active_row["thesis_id"].startswith("IM-RADAR-")
    assert active_row["phase"] == "pos_go_live"
    assert active_row["status"] == "Aberta - Atencao"
    assert active_row["is_open"] is True
    assert active_row["expected_result_pct"] == 64.04
    assert active_row["entry_price_brl"] == 118465.05
    assert active_row["current_price_brl"] == 196000.0
    assert active_row["source_url"] == "https://example.com/caixa-sao-miguel"
    assert "Teto de compra" in active_row["operation_plan"]
    assert "Leilao/venda online" in active_row["structured_operation"]
    assert active_row["exit_rule"] == "Confirmar ocupacao"
    assert "Confirmar ocupacao" in active_row["learning_note"]
    assert active_row["real_estate_analysis"]["score"] == 80
    assert active_row["real_estate_analysis"]["confidence"] == 36
    assert active_row["real_estate_analysis"]["price_ceiling_status"] == "Dentro do teto"
    assert active_row["real_estate_analysis"]["scenarios"]["base"]["roi_pct"] == 64.04
    assert {item["key"] for item in active_row["real_estate_analysis"]["pending_items"]} >= {
        "occupancy",
        "registration",
        "condo_debt",
    }
    assert {item["key"] for item in active_row["real_estate_analysis"]["clarified_items"]} >= {
        "edital",
        "renovation_budget",
        "plan_b",
    }

    closed_row = next(row for row in real_estate_rows if row["action"] == "Apto Mercado Colonia")
    assert closed_row["status"] == "Fechada"
    assert closed_row["outcome"] == "Descartado pelo radar"
    assert closed_row["is_open"] is False
    assert closed_row["real_estate_analysis"]["suggested_status"] == "Descartado"

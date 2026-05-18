from __future__ import annotations

import pytest
from app.main import AUTH_DISABLED
from app.services.real_estate_source_validation import SourceValidationResult


def _stub_valid_source_validation(monkeypatch: pytest.MonkeyPatch, main_module) -> None:
    monkeypatch.setattr(
        main_module,
        "validate_real_estate_source_url",
        lambda url: SourceValidationResult(
            url=url,
            status="valid",
            reason="Fonte individual validada.",
            checked_at="2026-05-18T12:00:00+00:00",
            http_status=200,
        ),
    )


def test_dashboard_summary_turns_real_estate_candidates_into_thesis_rows(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    _stub_valid_source_validation(monkeypatch, main_module)

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


def test_dashboard_summary_replaces_stale_seed_real_estate_candidate_with_database_state(
    client,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    _stub_valid_source_validation(monkeypatch, main_module)

    create_response = client.post(
        "/api/real-estate/candidates",
        json={
            "title": "REAL - Jardim das Colinas SJC 65m2 regiao Shopping",
            "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
            "origin": "Imovelweb",
            "strategy": "Arbitragem sem reforma + venda direta",
            "city": "Sao Jose dos Campos",
            "neighborhood": "Jardim das Colinas",
            "property_type": "Apartamento",
            "asking_price": 460000.0,
            "market_value_estimate": 598650.0,
            "estimated_sale_base": 598650.0,
            "renovation_type": "maquiagem",
            "renovation_budget": 26000.0,
            "carrying_months": 7,
            "monthly_carrying_cost": 700.0,
            "acquisition_costs": 23000.0,
            "selling_commission_pct": 6.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 1,
            "rent_comparables_count": 0,
            "plan_b": "Arbitragem sem obra pesada, com maquiagem e revenda abaixo do m2 do ranking.",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    thesis_id = f"IM-RADAR-{created['id']}"

    discard_response = client.post(
        f"/api/real-estate/candidates/{created['id']}/discard",
        json={"reason": "Anuncio Imovelweb finalizado pelo anunciante."},
    )
    assert discard_response.status_code == 200

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "dashboard_seed.json").write_text(
        main_module.json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_id": thesis_id,
                        "front": "imoveis",
                        "action": "REAL - Jardim das Colinas SJC 65m2 regiao Shopping",
                        "phase": "pos_go_live",
                        "status": "Aberta - Atencao",
                        "outcome": "Pendencias abertas",
                        "is_open": True,
                        "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-finalizado.html",
                        "structured_operation": "Arbitragem sem reforma + venda direta | Imovelweb",
                        "operation_plan": "Preco pedido R$ 460,000.00 | Caixa necessario R$ 145,900.00",
                        "real_estate_analysis": {"score": 72, "confidence": 30},
                    }
                ]
            }
        ),
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

    row = next(item for item in payload["thesis_open_operations"] if item["thesis_id"] == thesis_id)
    assert row["status"] == "Fechada"
    assert row["outcome"] == "Descartado pelo radar"
    assert row["is_open"] is False
    assert row["exit_rule"] == "Anuncio Imovelweb finalizado pelo anunciante."

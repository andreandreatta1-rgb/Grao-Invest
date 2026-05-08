from __future__ import annotations


def test_real_estate_candidate_api_roundtrip(client) -> None:
    empty_response = client.get("/api/real-estate/candidates")
    assert empty_response.status_code == 200
    assert empty_response.json()["summary"]["total"] == 0

    create_response = client.post(
        "/api/real-estate/candidates",
        json={
            "title": "Apto Sao Miguel Caixa",
            "source_url": "https://example.com/imovel",
            "origin": "Leilao Caixa",
            "strategy": "Revenda rapida",
            "city": "Sao Paulo",
            "neighborhood": "Sao Miguel Paulista",
            "property_type": "Apartamento",
            "asking_price": 139015.11,
            "appraisal_value": 230000.0,
            "market_value_estimate": 200000.0,
            "estimated_sale_conservative": 180000.0,
            "estimated_sale_base": 200000.0,
            "renovation_type": "leve",
            "renovation_budget": 12000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 1500.0,
            "acquisition_costs": 8500.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 85000.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 1,
            "rent_comparables_count": 0,
            "plan_b": "Alugar se a venda atrasar.",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["id"] > 0
    assert created["analysis"]["suggested_status"] == "Aberto com pendencias"
    assert created["analysis"]["next_action"] == "Confirmar ocupacao"

    update_response = client.patch(
        f"/api/real-estate/candidates/{created['id']}",
        json={
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["analysis"]["confidence"] > created["analysis"]["confidence"]

    list_response = client.get("/api/real-estate/candidates")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["summary"]["total"] == 1
    assert payload["items"][0]["title"] == "Apto Sao Miguel Caixa"

    discard_response = client.post(
        f"/api/real-estate/candidates/{created['id']}/discard",
        json={"reason": "Exercicio encerrado sem decisao de compra."},
    )
    assert discard_response.status_code == 200
    discarded = discard_response.json()
    assert discarded["status"] == "Descartado"
    assert discarded["discard_reason"] == "Exercicio encerrado sem decisao de compra."


def test_real_estate_strategy_territory_candidates_api(client) -> None:
    response = client.get("/api/real-estate/strategy-territory-candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["strategy_count"] == 7
    assert payload["summary"]["territory_count"] == 7
    assert payload["summary"]["matrix_brief_count"] == 49
    assert payload["summary"]["source_confirmed_requalification_count"] >= 4
    assert payload["matrix_briefs"][0]["trust_level"] == "hypothesis"
    assert payload["condominium_requalification_watchlist"][0]["trust_level"] == (
        "source_confirmed"
    )

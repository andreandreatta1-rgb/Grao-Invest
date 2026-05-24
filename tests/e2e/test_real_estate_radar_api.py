from __future__ import annotations

from app.models import RealEstateCandidate
from app.services.real_estate_source_validation import SourceValidationResult


def test_real_estate_candidate_api_roundtrip(client, monkeypatch) -> None:
    from app import main as main_module

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
            "payment_terms": [
                {
                    "key": "cash_discount",
                    "label": "A vista com 10% de desconto",
                    "kind": "cash_discount",
                    "discount_pct": 10,
                }
            ],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["id"] > 0
    assert "payment_terms_json" not in RealEstateCandidate.__table__.columns
    assert created["analysis"]["suggested_status"] == "Aberto com pendencias"
    assert created["analysis"]["next_action"] == "Confirmar ocupacao"
    assert created["payment_terms"][0]["key"] == "cash_discount"
    assert created["analysis"]["commercial_terms"]["recommended_scenario_key"] == "cash_discount"

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
    assert payload["candidates"][0]["title"] == "Apto Sao Miguel Caixa"

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
    assert payload["summary"]["strategy_count"] >= 8
    assert payload["summary"]["territory_count"] >= 12
    assert payload["summary"]["matrix_brief_count"] == (
        payload["summary"]["strategy_count"] * payload["summary"]["territory_count"]
    )
    assert payload["summary"]["source_candidate_count"] >= (
        payload["summary"]["strategy_count"] * 2
    )
    assert payload["summary"]["source_confirmed_requalification_count"] >= 4
    assert payload["summary"]["auctioneer_directory_count"] == 1
    assert payload["summary"]["auctioneer_contact_count"] >= 12
    assert payload["matrix_briefs"][0]["trust_level"] == "hypothesis"
    assert payload["strategy_candidate_watchlist"][0]["trust_level"] == "source_listed"
    assert payload["condominium_requalification_watchlist"][0]["trust_level"] == (
        "source_confirmed"
    )
    assert payload["auctioneer_sourcing"]["official_directories"][0]["contact_strategy"]
    assert payload["auctioneer_sourcing"]["official_contacts"][0]["competition_tier"]

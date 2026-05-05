from __future__ import annotations

from app.services.real_estate_radar import build_candidate_analysis


def test_candidate_with_open_p0_items_keeps_partial_score_but_waits_for_diligence() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Caixa",
            "strategy": "Revenda rapida",
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
            "plan_b": "Alugar se a venda demorar.",
        }
    )

    assert analysis["score"] >= 60
    assert analysis["confidence"] < 60
    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["next_action"] == "Confirmar ocupacao"
    assert {item["title"] for item in analysis["pending_items"]} >= {
        "Confirmar ocupacao",
        "Confirmar divida de condominio",
        "Buscar 3 comparaveis de venda",
    }
    assert analysis["breakeven_sale_price"] > 170000
    assert {item["key"] for item in analysis["score_breakdown"]} == {
        "location_liquidity",
        "discount",
        "value_creation",
        "renovation",
        "time",
        "legal",
        "cash",
        "plan_b",
    }
    assert sum(item["points"] for item in analysis["score_breakdown"]) == analysis["score"]
    assert sum(item["points"] for item in analysis["confidence_breakdown"]) == analysis["confidence"]
    assert {item["key"] for item in analysis["pending_items"]} >= {
        "occupancy",
        "registration",
        "condo_debt",
    }
    assert {item["key"] for item in analysis["clarified_items"]} >= {
        "renovation_budget",
        "plan_b",
    }


def test_strong_candidate_without_p0_items_becomes_candidate_for_diligence() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Venda direta vendedor",
            "strategy": "House flipping",
            "asking_price": 420000.0,
            "market_value_estimate": 560000.0,
            "estimated_sale_conservative": 530000.0,
            "estimated_sale_base": 560000.0,
            "renovation_type": "leve",
            "renovation_budget": 35000.0,
            "carrying_months": 5,
            "monthly_carrying_cost": 2200.0,
            "acquisition_costs": 18000.0,
            "selling_commission_pct": 5.0,
            "cash_needed": 155000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Alugar por R$ 3.300 se a revenda atrasar.",
        }
    )

    assert analysis["score"] >= 80
    assert analysis["confidence"] >= 85
    assert analysis["suggested_status"] == "Candidato forte"
    assert analysis["pending_items"] == []
    assert analysis["scenarios"]["base"]["net_profit"] > 40000


def test_occupied_first_operation_is_blocked_even_when_discount_looks_good() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda rapida",
            "asking_price": 180000.0,
            "appraisal_value": 310000.0,
            "market_value_estimate": 300000.0,
            "estimated_sale_conservative": 265000.0,
            "estimated_sale_base": 285000.0,
            "renovation_type": "maquiagem",
            "renovation_budget": 10000.0,
            "cash_needed": 75000.0,
            "occupancy_status": "ocupado",
            "first_operation": True,
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "plan_b": "Aluguel apos desocupacao.",
        }
    )

    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Descartar ou travar decisao"
    assert any(item["priority"] == "P0" for item in analysis["pending_items"])


def test_analysis_calculates_conservative_purchase_ceiling_for_negotiation() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Venda direta vendedor",
            "strategy": "House flipping leve",
            "asking_price": 200000.0,
            "estimated_sale_conservative": 220000.0,
            "estimated_sale_base": 235000.0,
            "renovation_budget": 18000.0,
            "carrying_months": 5,
            "monthly_carrying_cost": 1100.0,
            "acquisition_costs": 12000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 76000.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": True,
            "sale_comparables_count": 2,
            "renovation_type": "leve",
            "plan_b": "Locar se a venda demorar.",
        }
    )

    assert analysis["target_roi_pct"] == 20.0
    assert analysis["max_purchase_price"] == 156100.0
    assert analysis["price_gap_to_ceiling"] == 43900.0
    assert analysis["price_ceiling_status"] == "Acima do teto"

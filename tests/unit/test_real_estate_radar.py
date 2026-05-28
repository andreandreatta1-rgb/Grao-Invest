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


def test_known_debt_costs_reduce_profit_and_raise_breakeven() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda",
            "asking_price": 100000.0,
            "market_value_estimate": 150000.0,
            "estimated_sale_conservative": 140000.0,
            "estimated_sale_base": 150000.0,
            "estimated_sale_optimistic": 155000.0,
            "renovation_type": "leve",
            "renovation_budget": 0.0,
            "carrying_months": 0,
            "monthly_carrying_cost": 0.0,
            "acquisition_costs": 5000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 50000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "condo_debt_amount_brl": 20000.0,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
            "plan_b": "Alugar se a venda atrasar.",
        }
    )

    assert analysis["debt_costs_assumed_brl"] == 20000.0
    assert analysis["scenarios"]["base"]["net_profit"] == 16000.0
    assert analysis["scenarios"]["base"]["roi_pct"] == 32.0
    assert analysis["breakeven_sale_price"] > 132000.0


def test_condo_debt_above_threshold_discards_candidate() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda",
            "asking_price": 1200000.0,
            "estimated_sale_conservative": 2600000.0,
            "estimated_sale_base": 2800000.0,
            "estimated_sale_optimistic": 2900000.0,
            "renovation_type": "leve",
            "renovation_budget": 0.0,
            "carrying_months": 8,
            "monthly_carrying_cost": 4500.0,
            "acquisition_costs": 90000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 1300000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "condo_debt_amount_brl": 600000.0,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
            "plan_b": "Alugar se a venda atrasar.",
        }
    )

    assert analysis["suggested_status"] == "Descartado"
    assert "condominio" in analysis["next_action"].lower()


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


def test_auction_candidate_without_official_edital_waits_for_documentation() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Caixa",
            "strategy": "Revenda rapida",
            "asking_price": 260000.0,
            "market_value_estimate": 420000.0,
            "estimated_sale_conservative": 390000.0,
            "estimated_sale_base": 420000.0,
            "renovation_type": "leve",
            "renovation_budget": 15000.0,
            "cash_needed": 120000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": False,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Alugar se a venda demorar.",
        }
    )

    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["next_action"] == "Buscar edital oficial"
    edital_items = [item for item in analysis["pending_items"] if item["key"] == "edital"]
    assert edital_items and edital_items[0]["priority"] == "P0"


def test_unknown_debt_responsibility_blocks_cost_total_before_margin() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda rapida",
            "asking_price": 240000.0,
            "market_value_estimate": 390000.0,
            "estimated_sale_conservative": 360000.0,
            "estimated_sale_base": 390000.0,
            "renovation_type": "leve",
            "renovation_budget": 12000.0,
            "cash_needed": 95000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Alugar se a venda demorar.",
        }
    )

    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["next_action"] == "Confirmar custo total de debitos"
    debt_items = [item for item in analysis["pending_items"] if item["key"] == "debt_total"]
    assert debt_items and debt_items[0]["priority"] == "P0"
    iptu_items = [item for item in analysis["pending_items"] if item["key"] == "iptu_debt"]
    assert iptu_items and iptu_items[0]["priority"] == "P0"


def test_occupied_with_buyer_eviction_responsibility_is_discarded_without_approved_plan() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Caixa",
            "strategy": "Revenda com desocupacao",
            "listing_description": (
                "Imovel ocupado. Desocupacao por conta do adquirente, sem acordo de "
                "desocupacao ou imissao planejada informada no edital."
            ),
            "asking_price": 300000.0,
            "market_value_estimate": 520000.0,
            "estimated_sale_conservative": 480000.0,
            "estimated_sale_base": 520000.0,
            "renovation_type": "leve",
            "renovation_budget": 20000.0,
            "cash_needed": 150000.0,
            "occupancy_status": "desconhecido",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Alugar se a venda demorar.",
        }
    )

    assert analysis["listing_reading"]["buyer_responsible_for_eviction"] is True
    assert analysis["suggested_status"] == "Descartado"
    assert "posse" in analysis["next_action"].lower()


def test_listing_reading_marks_desocupado_without_false_occupied_flag() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda rapida",
            "asking_price": 180000.0,
            "market_value_estimate": 260000.0,
            "estimated_sale_conservative": 240000.0,
            "estimated_sale_base": 260000.0,
            "renovation_type": "leve",
            "renovation_budget": 12000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 1500.0,
            "acquisition_costs": 9000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 82000.0,
            "occupancy_status": "desconhecido",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 0,
            "listing_description": (
                "IMOVEL DESOCUPADO. Apartamento com area util ou privativa de 74,14 m2. "
                "Edital menciona condicoes de pagamento e diligencia."
            ),
        }
    )

    assert analysis["listing_reading"]["occupancy_status"] == "desocupado"
    assert analysis["listing_reading"]["private_area_m2"] == 74.14
    occupancy_items = [item for item in analysis["confidence_breakdown"] if item["key"] == "occupancy"]
    assert occupancy_items and occupancy_items[0]["points"] == 15


def test_listing_reading_flags_rights_over_asset_and_adds_p0_pending() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Mega Leiloes",
            "strategy": "Leilao judicial + diligencia",
            "title": "Direitos sobre Apartamento 31 m2 (01 vaga) - Vila Sao Francisco - Sao Paulo - SP",
            "asking_price": 197782.59,
            "market_value_estimate": 329637.64,
            "estimated_sale_conservative": 200000.0,
            "estimated_sale_base": 215000.0,
            "estimated_sale_optimistic": 230000.0,
            "private_area_m2": 31.0,
            "renovation_type": "leve",
            "renovation_budget": 35000.0,
            "carrying_months": 10,
            "monthly_carrying_cost": 1800.0,
            "acquisition_costs": 15822.61,
            "selling_commission_pct": 6.0,
            "cash_needed": 0.0,
            "occupancy_status": "desconhecido",
            "has_registration": True,
            "condo_debt_known": False,
            "iptu_debt_known": True,
            "sale_comparables_count": 2,
            "sale_comparables": [
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/a/",
                    "price": 236380.0,
                    "area_m2": 32.0,
                    "evidence_type": "asking_listing",
                },
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/b/",
                    "price": 259700.0,
                    "area_m2": 41.0,
                    "evidence_type": "asking_listing",
                },
            ],
            "plan_b": "Alugar se a revenda atrasar.",
        }
    )

    assert analysis["listing_reading"]["rights_over_asset"] is True
    rights_items = [item for item in analysis["pending_items"] if item["key"] == "rights_over_asset"]
    assert rights_items and rights_items[0]["priority"] == "P0"
    assert analysis["suggested_status"] == "Descartado"
    assert "direitos" in analysis["next_action"].lower()


def test_fractional_interest_candidate_is_discarded_as_legal_blocker() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Imovel",
            "strategy": "Fracao comercial em eixo premium + tese juridica",
            "title": "Fracao ideal de conjunto comercial na Faria Lima",
            "property_type": "Fracao de conjunto comercial",
            "asking_price": 704997.27,
            "market_value_estimate": 1409994.54,
            "estimated_sale_conservative": 1200000.0,
            "estimated_sale_base": 1400000.0,
            "private_area_m2": 153.0,
            "renovation_type": "comercial leve",
            "renovation_budget": 60000.0,
            "carrying_months": 10,
            "monthly_carrying_cost": 6200.0,
            "acquisition_costs": 45000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 705000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
            "plan_b": "Somente com advogado e comprador final mapeado.",
        }
    )

    assert analysis["listing_reading"]["fractional_interest"] is True
    assert analysis["suggested_status"] == "Descartado"
    assert "fracao" in analysis["next_action"].lower()


def test_bare_ownership_candidate_is_discarded_as_legal_blocker() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Nua propriedade + tese juridica",
            "title": "Nua propriedade de apartamento em leilao",
            "listing_description": "Oferta da nua propriedade, com usufruto vigente sobre o imovel.",
            "asking_price": 250000.0,
            "market_value_estimate": 500000.0,
            "estimated_sale_conservative": 430000.0,
            "estimated_sale_base": 500000.0,
            "private_area_m2": 70.0,
            "renovation_type": "leve",
            "renovation_budget": 25000.0,
            "carrying_months": 8,
            "monthly_carrying_cost": 2200.0,
            "acquisition_costs": 18000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 250000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
            "plan_b": "Nao avancar sem propriedade plena.",
        }
    )

    assert analysis["listing_reading"]["bare_ownership"] is True
    assert analysis["suggested_status"] == "Descartado"
    assert "nua propriedade" in analysis["next_action"].lower()


def test_listing_reading_does_not_override_existing_private_area_with_smaller_value() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda rapida",
            "asking_price": 304261.69,
            "market_value_estimate": 507102.82,
            "private_area_m2": 67.85,
            "renovation_type": "leve",
            "renovation_budget": 0.0,
            "carrying_months": 0,
            "monthly_carrying_cost": 0.0,
            "acquisition_costs": 0.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 0.0,
            "occupancy_status": "desconhecido",
            "has_registration": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 2,
            "rent_comparables_count": 0,
            "sale_comparables": [
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://example.com/a",
                    "price": 500000.0,
                    "area_m2": 50.0,
                    "price_per_m2": 10000.0,
                    "evidence_type": "asking_listing",
                },
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://example.com/b",
                    "price": 600000.0,
                    "area_m2": 50.0,
                    "price_per_m2": 12000.0,
                    "evidence_type": "asking_listing",
                },
            ],
            "listing_description": (
                "MATRICULA VAGA DE GARAGEM ... contendo area util de 8,400 m2, area comum de 16,217 m2 "
                "e area total de 24,617 m2. E, UNIDADE ... contendo area util de 67,850 m2."
            ),
        }
    )

    assert analysis["valuation_evidence"]["source"] == "sale_comparables"
    assert analysis["valuation_evidence"]["base_sale_price"] >= 500000.0


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


def test_negative_conservative_margin_above_ceiling_is_discarded() -> None:
    analysis = build_candidate_analysis(
        {
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
            "source_validation_status": "valid",
            "source_validation_reason": "Fonte individual validada.",
        }
    )

    assert analysis["scenarios"]["conservative"]["net_profit"] < 0
    assert analysis["price_ceiling_status"] == "Acima do teto"
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Rever preco maximo ou descartar"


def test_comparable_listing_rebases_active_candidate_exit_scenarios() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Frazao Leiloes / Itau",
            "strategy": "Leilao + HF",
            "city": "Sao Paulo",
            "neighborhood": "Saude",
            "property_type": "Apartamento",
            "private_area_m2": 74.14,
            "asking_price": 388700.0,
            "market_value_estimate": 500000.0,
            "estimated_sale_conservative": 465000.0,
            "estimated_sale_base": 500000.0,
            "estimated_sale_optimistic": 525000.0,
            "renovation_type": "leve",
            "renovation_budget": 28000.0,
            "carrying_months": 8,
            "monthly_carrying_cost": 2200.0,
            "acquisition_costs": 23322.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 166097.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 0,
            "rent_comparables_count": 0,
            "sale_comparables": [
                {
                    "source": "Imovelweb",
                    "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-com-3-dormitorios-a-venda-74-m-por-r$-3034844612.html",
                    "price": 600000.0,
                    "area_m2": 74.0,
                    "evidence_type": "asking_listing",
                    "note": "Rua Abagiba, Saude, 74m2, 3 dormitorios, 2 vagas.",
                }
            ],
        }
    )

    assert analysis["scenarios"]["conservative"]["sale_price"] == 550000.0
    assert analysis["scenarios"]["base"]["sale_price"] == 600000.0
    assert analysis["scenarios"]["optimistic"]["sale_price"] == 650000.0
    assert analysis["scenarios"]["base"]["net_profit"] == 106378.0
    assert analysis["price_ceiling_status"] == "Dentro do teto"
    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["valuation_evidence"]["source"] == "sale_comparables"
    assert analysis["valuation_evidence"]["sale_comparables_count"] == 1
    assert "anuncio" in analysis["valuation_evidence"]["caveat"].lower()


def test_high_dispersion_sale_comparables_reduce_confidence_and_add_p0_exit_validation() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "ChavesNaMao",
            "strategy": "Revenda",
            "asking_price": 500000.0,
            "city": "Sao Paulo",
            "neighborhood": "Alto da Mooca",
            "property_type": "Apartamento",
            "private_area_m2": 100.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "renovation_type": "leve",
            "renovation_budget": 30000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 2000.0,
            "acquisition_costs": 25000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 200000.0,
            "sale_comparables": [
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/a/",
                    "price": 500000.0,
                    "area_m2": 100.0,
                    "evidence_type": "asking_listing",
                },
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/b/",
                    "price": 1200000.0,
                    "area_m2": 100.0,
                    "evidence_type": "asking_listing",
                },
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/c/",
                    "price": 1300000.0,
                    "area_m2": 100.0,
                    "evidence_type": "asking_listing",
                },
            ],
        }
    )

    assert analysis["valuation_evidence"]["source"] == "sale_comparables"
    assert analysis["valuation_evidence"]["quality_warning"] is True
    assert any(item["key"] == "exit_value_dispersion" for item in analysis["pending_items"])
    assert analysis["next_action"] == "Validar valor de saida"
    sale_items = [item for item in analysis["confidence_breakdown"] if item["key"] == "sale_comparables"]
    assert sale_items and sale_items[0]["status"] == "parcial"
    assert sale_items[0]["points"] <= 5

def test_access_required_source_becomes_user_credential_p0() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Imovel / WebLeiloes",
            "strategy": "Leilao extrajudicial + HF leve",
            "source_url": "https://www.webleiloes.com.br/lote/12345",
            "source_validation_status": "access_required",
            "source_validation_reason": "Fonte exige cadastro/login para continuar.",
            "source_checked_at": "2026-05-25T10:00:00+00:00",
            "source_validation": {
                "status": "access_required",
                "reason": "Fonte exige cadastro/login para continuar.",
                "requires_user_action": True,
                "user_action": "Criar cadastro/login no leiloeiro e anexar credenciais.",
                "credential_file_hint": "data/secure/real_estate_sources/www.webleiloes.com.br.credentials.json",
                "official_url": "https://www.webleiloes.com.br/lote/12345",
                "edital_url": "https://suporteleiloes.com.br/editais/2803839-edital.pdf",
            },
            "city": "Sao Paulo",
            "neighborhood": "Pinheiros",
            "street": "Rua Alves Guimaraes",
            "property_type": "Apartamento",
            "asking_price": 420000.0,
            "market_value_estimate": 650000.0,
            "estimated_sale_base": 650000.0,
            "private_area_m2": 45.0,
            "renovation_budget": 30000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 2500.0,
            "acquisition_costs": 40000.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 180000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "financing_validated": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
        }
    )

    source_item = next(item for item in analysis["pending_items"] if item["key"] == "source_access")

    assert source_item["priority"] == "P0"
    assert source_item["title"] == "Acesso ao leiloeiro necessario"
    assert "www.webleiloes.com.br.credentials.json" in source_item["action"]
    assert analysis["next_action"] == "Acesso ao leiloeiro necessario"
    assert analysis["source_validation"]["requires_user_action"] is True
    assert (
        analysis["source_validation"]["credential_file_hint"]
        == "data/secure/real_estate_sources/www.webleiloes.com.br.credentials.json"
    )


def test_same_address_comparable_below_reference_rebases_exit_downward() -> None:
    comparable_url = (
        "https://www.chavesnamao.com.br/imovel/apartamento-a-venda-2-quartos-"
        "com-garagem-sp-sao-paulo-campo-belo-RS680000/id-42367031/"
    )

    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Imovel / Vieira de Moraes Leiloeiro",
            "strategy": "Leilao de alto ticket + comprador final",
            "source_url": "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-extrajudicial-categoria-residenciais-cod-do-leilao-0109-26-imovel-2824988",
            "source_validation_status": "ambiguous",
            "source_validation_reason": (
                "Ocupado; precisa validar prazo, custo de imissao e perfil de comprador antes de lance."
            ),
            "city": "Sao Paulo",
            "neighborhood": "Campo Belo",
            "street": "Rua Vieira de Morais, 2098",
            "property_type": "Apartamento",
            "asking_price": 852901.69,
            "market_value_estimate": 1109278.83,
            "estimated_sale_conservative": 1020536.52,
            "estimated_sale_base": 1109278.83,
            "estimated_sale_optimistic": 1164742.77,
            "private_area_m2": 128.99,
            "listing_description": (
                "Apartamento n° 27, localizado no Condomínio Helbor Apto. Campo Belo, "
                "situado na Rua Vieira de Morais, n° 2.098, Campo Belo, na cidade de "
                "São Paulo/SP, com direito de usar 01 (uma) vaga indeterminada de garagem "
                "para veículo. Matrícula nº 256.212 do 15º CRI de São Paulo/SP. Área "
                "privativa de 65,09m². Área comum de 63,90m². Área total de 128,99m². "
                "Obs.: Ocupado. Desocupação por conta do adquirente, nos termos do art. "
                "30 da lei 9.514/97. O Vendedor se exime de qualquer responsabilidade "
                "quanto a verificação de documentos e diligências relacionadas ao imóvel. "
                "Cabe exclusivamente ao interessado a leitura e conferência das condições "
                "previstas no edital e matrícula, ações judiciais e HIS/HMP."
            ),
            "renovation_type": "retrofit leve",
            "renovation_budget": 70000.0,
            "carrying_months": 12,
            "monthly_carrying_cost": 5200.0,
            "acquisition_costs": 68232.14,
            "selling_commission_pct": 6.0,
            "cash_needed": 371212.48,
            "occupancy_status": "ocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 0,
            "rent_comparables_count": 0,
            "sale_comparables": [
                {
                    "source": "Chaves na Mao",
                    "source_url": comparable_url,
                    "price": 680000.0,
                    "area_m2": 65.09,
                    "evidence_type": "asking_listing_same_address",
                    "note": "Mesmo endereco, 65,09m2 privativos, 2 quartos e 1 vaga.",
                }
            ],
            "plan_b": "So avancar com comprador final mapeado.",
        }
    )

    assert analysis["listing_reading"]["private_area_m2"] == 65.09
    assert analysis["listing_reading"]["total_area_m2"] == 128.99
    assert analysis["listing_reading"]["buyer_responsible_for_eviction"] is True
    assert analysis["scenarios"]["base"]["sale_price"] == 680000.0
    assert analysis["scenarios"]["conservative"]["sale_price"] == 625000.0
    assert analysis["valuation_evidence"]["base_sale_price"] == 680000.0
    assert analysis["valuation_evidence"]["comparables"][0]["source_url"] == comparable_url
    assert analysis["price_ceiling_status"] == "Acima do teto"
    assert analysis["suggested_status"] == "Descartado"
    assert any(item["key"] == "eviction_risk" for item in analysis["pending_items"])
    assert any(
        item["key"] == "auction_due_diligence_disclaimer"
        for item in analysis["pending_items"]
    )


def test_same_address_comparable_takes_priority_over_neighborhood_comparables() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Imovel / Bradesco",
            "strategy": "Leilao + revenda",
            "city": "Sao Paulo",
            "neighborhood": "Pinheiros",
            "street": "Rua Padre Carvalho, 129",
            "property_type": "Casa em vila",
            "asking_price": 1610827.63,
            "market_value_estimate": 2800000.0,
            "private_area_m2": 150.0,
            "occupancy_status": "ocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "renovation_type": "pesada",
            "renovation_budget": 250000.0,
            "carrying_months": 12,
            "monthly_carrying_cost": 8000.0,
            "acquisition_costs": 128866.21,
            "selling_commission_pct": 6.0,
            "sale_comparables": [
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/casa-a-venda-padre-carvalho/",
                    "price": 3200000.0,
                    "area_m2": 150.0,
                    "evidence_type": "same_address_listing",
                    "note": "Mesmo endereco, casa de vila, 2 quartos, 1 vaga.",
                },
                {
                    "source": "ChavesNaMao",
                    "source_url": "https://www.chavesnamao.com.br/imovel/casa-a-venda-pinheiros-1/",
                    "price": 1600000.0,
                    "area_m2": 150.0,
                    "evidence_type": "neighborhood_listing",
                    "note": "Mesmo bairro, condicao inferior.",
                },
                {
                    "source": "Imovelweb",
                    "source_url": "https://www.imovelweb.com.br/propriedades/casa-pinheiros/",
                    "price": 2000000.0,
                    "area_m2": 150.0,
                    "evidence_type": "neighborhood_listing",
                    "note": "Mesmo bairro, rua diferente.",
                },
            ],
            "plan_b": "So ofertar com validacao de ocupacao e saida.",
        }
    )

    evidence = analysis["valuation_evidence"]
    assert evidence["source"] == "sale_comparables"
    assert evidence["valuation_scope"] == "same_address"
    assert evidence["base_sale_price"] == 3200000.0
    assert evidence["used_comparables_count"] == 1
    assert evidence["excluded_lower_priority_comparables_count"] == 2
    assert analysis["scenarios"]["base"]["sale_price"] == 3200000.0


def test_structured_notes_can_carry_same_address_comparable_for_active_candidate() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Imovel / Bradesco",
            "strategy": "Leilao + revenda",
            "city": "Sao Paulo",
            "neighborhood": "Pinheiros",
            "street": "Rua Padre Carvalho, 129",
            "property_type": "Casa em vila",
            "asking_price": 1610827.63,
            "market_value_estimate": 2866823.71,
            "private_area_m2": 180.0,
            "occupancy_status": "ocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "renovation_type": "pesada",
            "renovation_budget": 250000.0,
            "carrying_months": 12,
            "monthly_carrying_cost": 8000.0,
            "acquisition_costs": 128866.21,
            "selling_commission_pct": 6.0,
            "notes": (
                '[SALE_COMPARABLE] {"source":"ChavesNaMao","source_url":"https://www.chavesnamao.com.br/imovel/casa-a-venda-2-quartos-com-garagem-sp-sao-paulo-pinheiros-200m2-RS3200000/id-39888317/","price":3200000,"area_m2":200,"evidence_type":"same_address_listing","note":"Mesmo endereco, casa de vila na Rua Padre Carvalho, 129."}'
            ),
            "plan_b": "So ofertar com validacao de ocupacao e saida.",
        }
    )

    evidence = analysis["valuation_evidence"]
    assert evidence["valuation_scope"] == "same_address"
    assert evidence["base_sale_price"] == 2880000.0
    assert evidence["comparables"][0]["source"] == "ChavesNaMao"


def test_neighborhood_benchmark_cannot_create_false_discount_without_asset_comparables() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Flora Imoveis",
            "strategy": "House flipping leve + venda direta",
            "source_url": "https://www.floraimoveis.com.br/imovel/campinas/apartamento/3226394",
            "city": "Campinas",
            "neighborhood": "Cambui",
            "property_type": "Apartamento",
            "asking_price": 328000.0,
            "market_value_estimate": 609795.0,
            "estimated_sale_conservative": 548815.0,
            "estimated_sale_base": 609795.0,
            "estimated_sale_optimistic": 640285.0,
            "private_area_m2": 45.17,
            "bedrooms": 1,
            "parking_spaces": 0,
            "renovation_type": "leve",
            "renovation_budget": 42000.0,
            "sale_comparables_count": 1,
            "rent_comparables_count": 1,
            "carrying_months": 8,
            "monthly_carrying_cost": 850.0,
            "cash_needed": 130800.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "plan_b": "Alugar mobiliado se revenda atrasar.",
            "notes": (
                "Lead veio do Reel @saopaulointerior: Cambui aparece como 1o bairro "
                "do ranking FipeZAP+ 2026 a R$ 13.500/m2."
            ),
        }
    )

    assert analysis["score"] <= 65
    assert analysis["price_ceiling_status"] == "Teto a validar"
    assert analysis["valuation_evidence"]["risk_flag"] == "weak_neighborhood_benchmark"
    assert analysis["valuation_evidence"]["sale_comparables_count"] == 1
    assert any(item["key"] == "exit_value_validation" for item in analysis["pending_items"])
    assert any(
        item["key"] == "discount" and item["points"] <= 6
        for item in analysis["score_breakdown"]
    )
    assert any(
        item["key"] == "value_creation" and item["points"] <= 6
        for item in analysis["score_breakdown"]
    )


def test_large_morumbi_apartment_without_local_buyer_demand_is_closed() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Frazao Leiloes / Itau",
            "strategy": "Leilao + HF",
            "city": "Sao Paulo",
            "neighborhood": "Butanta / Morumbi",
            "property_type": "Apartamento",
            "title": "REAL - Frazao Itau Butanta Piazza Morumbi 232m2",
            "asking_price": 749600.0,
            "market_value_estimate": 1040000.0,
            "estimated_sale_conservative": 950000.0,
            "estimated_sale_base": 1040000.0,
            "estimated_sale_optimistic": 1110000.0,
            "private_area_m2": 232.23,
            "parking_spaces": 3,
            "renovation_type": "retrofit controlado",
            "renovation_budget": 120000.0,
            "sale_comparables_count": 0,
            "rent_comparables_count": 0,
            "carrying_months": 8,
            "monthly_carrying_cost": 4200.0,
            "cash_needed": 385976.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "notes": "Apartamento grande no Piazza Morumbi; preco por m2 barato depende de publico comprador.",
        }
    )

    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Fechar candidato: demanda local reprovada"
    assert analysis["confidence"] <= 30
    assert analysis["local_demand_evidence"]["risk_level"] == "critico"
    assert analysis["local_demand_evidence"]["should_discard"] is True
    assert any(item["key"] == "local_buyer_demand" for item in analysis["pending_items"])
    assert any(
        item["key"] == "location_liquidity" and item["points"] <= 5
        for item in analysis["score_breakdown"]
    )


def test_payment_terms_create_commercial_scenarios_and_influence_score() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Frazao Leiloes / Itau",
            "strategy": "Leilao + HF",
            "source_url": "https://www.frazaoleiloes.com.br/Auction/LotDetails/37570",
            "source_validation_status": "valid",
            "source_validation_reason": "Fonte individual validada.",
            "asking_price": 399400.0,
            "market_value_estimate": 585000.0,
            "estimated_sale_conservative": 545000.0,
            "estimated_sale_base": 585000.0,
            "renovation_type": "leve",
            "renovation_budget": 42000.0,
            "carrying_months": 8,
            "monthly_carrying_cost": 2400.0,
            "acquisition_costs": 23964.0,
            "selling_commission_pct": 6.0,
            "cash_needed": 165844.0,
            "occupancy_status": "desconhecido",
            "has_registration": False,
            "condo_debt_known": False,
            "iptu_debt_known": False,
            "sale_comparables_count": 1,
            "payment_terms": [
                {
                    "key": "cash_discount",
                    "label": "A vista com 10% de desconto",
                    "kind": "cash_discount",
                    "discount_pct": 10,
                },
                {
                    "key": "down_20_8x_no_interest",
                    "label": "20% de sinal + 8 parcelas sem juros",
                    "kind": "installments_no_interest",
                    "down_payment_pct": 20,
                    "installments": 8,
                },
                {
                    "key": "down_25_24x_price_ipca",
                    "label": "25% de sinal + 24 parcelas Price + IPCA",
                    "kind": "price_table",
                    "down_payment_pct": 25,
                    "installments": 24,
                    "annual_interest_pct": 10,
                    "indexed_to": "IPCA",
                },
                {
                    "key": "down_30_78x_price_ipca",
                    "label": "30% de sinal + 78 parcelas Price + IPCA",
                    "kind": "price_table",
                    "down_payment_pct": 30,
                    "installments": 78,
                    "annual_interest_pct": 10,
                    "indexed_to": "IPCA",
                },
            ],
        }
    )

    commercial = analysis["commercial_terms"]
    assert commercial["source"] == "Frazao Leiloes / Itau"
    assert commercial["recommended_scenario_key"] == "cash_discount"
    assert commercial["recommended_decision"] == "melhora_margem"
    assert commercial["summary"] == (
        "A vista com desconto melhora a margem; parcelamento longo com IPCA vira risco financeiro."
    )

    scenarios = {item["key"]: item for item in commercial["scenarios"]}
    assert scenarios["cash_discount"]["effective_purchase_price"] == 359460.0
    assert scenarios["cash_discount"]["initial_cash"] == 359460.0
    assert scenarios["cash_discount"]["discount_value"] == 39940.0
    assert scenarios["down_20_8x_no_interest"]["initial_cash"] == 79880.0
    assert scenarios["down_20_8x_no_interest"]["monthly_payment"] == 39940.0
    assert scenarios["down_20_8x_no_interest"]["present_value_cost"] == 385488.01
    assert scenarios["down_30_78x_price_ipca"]["decision"] == "alto_custo_financeiro"
    assert scenarios["down_30_78x_price_ipca"]["risk_level"] == "alto"
    assert scenarios["down_30_78x_price_ipca"]["total_nominal_cost"] == 496380.83

    assert any(item["key"] == "commercial_terms" for item in analysis["score_breakdown"])
    assert any(item["key"] == "commercial_terms" for item in analysis["confidence_breakdown"])
    assert any(item["key"] == "commercial_terms_ipca" for item in analysis["pending_items"])
    assert any(item["key"] == "commercial_terms" for item in analysis["clarified_items"])


def test_missing_purchase_price_adds_p0_pending_item_and_zeroes_cash_needed() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Revenda rapida",
            "asking_price": 0.0,
            "market_value_estimate": 260000.0,
            "estimated_sale_conservative": 240000.0,
            "estimated_sale_base": 260000.0,
            "renovation_type": "leve",
            "renovation_budget": 12000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 1500.0,
            "selling_commission_pct": 6.0,
            "occupancy_status": "desconhecido",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 0,
        }
    )

    assert any(
        item["key"] == "purchase_price" and item["priority"] == "P0" for item in analysis["pending_items"]
    )
    assert analysis["cash_needed"] == 0.0
    assert analysis["scenarios"]["base"]["roi_pct"] == 0.0


def test_default_cash_needed_is_conservative_when_missing() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Venda direta vendedor",
            "strategy": "House flipping",
            "asking_price": 200000.0,
            "estimated_sale_conservative": 220000.0,
            "estimated_sale_base": 235000.0,
            "estimated_sale_optimistic": 245000.0,
            "renovation_budget": 10000.0,
            "carrying_months": 6,
            "monthly_carrying_cost": 1000.0,
            "selling_commission_pct": 6.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 1,
            "plan_b": "Locar se a venda demorar.",
        }
    )

    assert analysis["cash_needed"] == 226000.0


def test_auction_financing_or_fgts_dependency_adds_p0_until_validated() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Caixa",
            "strategy": "Revenda com FGTS e financiamento como premissa de entrada",
            "asking_price": 260000.0,
            "market_value_estimate": 420000.0,
            "estimated_sale_conservative": 390000.0,
            "estimated_sale_base": 420000.0,
            "renovation_type": "leve",
            "renovation_budget": 15000.0,
            "cash_needed": 70000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": False,
            "plan_b": "Revender; alugar se a saida atrasar.",
        }
    )

    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["next_action"] == "Validar financiamento/FGTS"
    financing_items = [item for item in analysis["pending_items"] if item["key"] == "financing_dependency"]
    assert financing_items and financing_items[0]["priority"] == "P0"


def test_suspicious_auction_payment_instruction_discards_candidate() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao extrajudicial",
            "strategy": "Revenda rapida",
            "source_url": "https://leilao-exemplo.com/lote-123",
            "source_validation_status": "valid",
            "source_validation_reason": "Link individual abre, mas instrui Pix em conta de terceiro fora do edital.",
            "asking_price": 240000.0,
            "market_value_estimate": 390000.0,
            "estimated_sale_conservative": 360000.0,
            "estimated_sale_base": 390000.0,
            "renovation_type": "leve",
            "renovation_budget": 12000.0,
            "cash_needed": 95000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Revender; alugar se a venda demorar.",
        }
    )

    assert analysis["listing_reading"]["suspicious_payment_instruction"] is True
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Fechar candidato: fonte/pagamento nao oficial"
    assert any(item["key"] == "source_payment_risk" and item["priority"] == "P0" for item in analysis["pending_items"])


def test_fiduciary_auction_nullity_action_discards_candidate_from_standard_radar() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Mega Leiloes / Bradesco",
            "strategy": "Leilao extrajudicial AF + revenda",
            "source_url": "https://www.megaleiloes.com.br/leiloes-realizados/imoveis/casas/sp/sao-paulo/casa-80-m2-sao-paulo-sp-rua-padre-carvalho-129-pinheiros-x123972",
            "source_validation_status": "valid",
            "source_validation_reason": "Fonte oficial com edital e matricula.",
            "listing_description": (
                "Casa 04. Ocupada (AF). Consta Acao Declaratoria de Nulidade da "
                "Consolidacao da Propriedade Fiduciaria e dos Leiloes Extrajudiciais, "
                "processo 4057062-13.2026.8.26.0100."
            ),
            "asking_price": 1179000.0,
            "market_value_estimate": 1800000.0,
            "estimated_sale_conservative": 1650000.0,
            "estimated_sale_base": 1800000.0,
            "renovation_type": "leve",
            "renovation_budget": 50000.0,
            "cash_needed": 1350000.0,
            "occupancy_status": "ocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "eviction_plan": "Imissao planejada com advogado.",
            "plan_b": "Revender somente se a posse sair limpa.",
        }
    )

    assert analysis["listing_reading"]["fiduciary_auction_nullity_action"] is True
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Fechar candidato: acao judicial ataca consolidacao/leilao"
    assert any(
        item["key"] == "fiduciary_auction_nullity_action" and item["priority"] == "P0"
        for item in analysis["pending_items"]
    )
    assert analysis["sourcing"]["tier"] == "bloqueado_por_p0"


def test_occupied_fiduciary_auction_without_nullity_action_can_remain_legal_watchlist() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Zuk / Banco Bradesco",
            "strategy": "2a praca extrajudicial AF + casa em vila",
            "source_url": "https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/rua-padre-carvalho-129/36388-226112",
            "source_validation_status": "valid",
            "source_validation_reason": "Fonte oficial Zuk/Banco Bradesco validada.",
            "listing_description": (
                "Casa 5. Ocupado (AF). Desocupacao por conta do adquirente, "
                "nos termos do art. 30 da Lei 9.514/97."
            ),
            "asking_price": 1610827.63,
            "market_value_estimate": 2955000.0,
            "estimated_sale_conservative": 2720000.0,
            "estimated_sale_base": 2955000.0,
            "renovation_type": "reforma completa",
            "renovation_budget": 180000.0,
            "cash_needed": 2100000.0,
            "occupancy_status": "ocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 4,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "eviction_plan": "Imissao planejada com advogado antes de qualquer lance.",
            "plan_b": "Watchlist juridica ate validar prazo de posse.",
        }
    )

    assert "fiduciary_auction_nullity_action" not in analysis["listing_reading"]
    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert any(item["key"] == "eviction_risk" for item in analysis["pending_items"])


def test_ambiguous_debt_responsibility_blocks_auction_until_written_confirmation() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leiloeiro oficial",
            "strategy": "Leilao judicial com margem aparente",
            "source_url": "https://www.leiloeiro.example/lote/123",
            "source_validation_status": "valid",
            "source_validation_reason": "Edital oficial aberto.",
            "listing_description": (
                "Leilao judicial. Debitos e obrigacoes: em caso de arrematacao, "
                "o edital nao fala explicitamente que o arrematante assumira o saldo devedor "
                "junto ao credor fiduciario. Duvidas e esclarecimentos devem ser solicitados "
                "perante o oficio judicial ou ao escritorio do leiloeiro por email oficial."
            ),
            "asking_price": 600000.0,
            "market_value_estimate": 1050000.0,
            "estimated_sale_conservative": 950000.0,
            "estimated_sale_base": 1050000.0,
            "renovation_type": "leve",
            "renovation_budget": 40000.0,
            "cash_needed": 720000.0,
            "occupancy_status": "desocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Revenda abaixo do valor base se a divida for esclarecida.",
        }
    )

    assert analysis["listing_reading"]["debt_responsibility_ambiguous"] is True
    assert analysis["suggested_status"] == "Aberto com pendencias"
    assert analysis["next_action"] == "Confirmar responsabilidade por debitos"
    assert any(
        item["key"] == "debt_responsibility_ambiguous" and item["priority"] == "P0"
        for item in analysis["pending_items"]
    )
    assert analysis["sourcing"]["tier"] == "bloqueado_por_p0"


def test_explicit_debt_responsibility_does_not_create_ambiguous_debt_blocker() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leiloeiro oficial",
            "strategy": "Leilao judicial com debitos esclarecidos",
            "source_url": "https://www.leiloeiro.example/lote/124",
            "source_validation_status": "valid",
            "source_validation_reason": "Edital oficial aberto.",
            "listing_description": (
                "Leilao judicial. Os debitos de IPTU anteriores serao quitados com o produto "
                "da arrematacao. O arrematante responde apenas pelas despesas vencidas apos "
                "a imissao na posse."
            ),
            "asking_price": 600000.0,
            "market_value_estimate": 1050000.0,
            "estimated_sale_conservative": 950000.0,
            "estimated_sale_base": 1050000.0,
            "renovation_type": "leve",
            "renovation_budget": 40000.0,
            "cash_needed": 720000.0,
            "occupancy_status": "desocupado",
            "first_operation": False,
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Revenda abaixo do valor base.",
        }
    )

    assert "debt_responsibility_ambiguous" not in analysis["listing_reading"]
    assert not any(item["key"] == "debt_responsibility_ambiguous" for item in analysis["pending_items"])


def test_priscila_backlog_adds_modality_condition_and_exit_plan_pending_items() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao de imoveis",
            "strategy": "Comprar, reformar e vender",
            "listing_description": "Imovel abandonado, sem fotos internas, com obra a orcar antes do lance.",
            "asking_price": 180000.0,
            "market_value_estimate": 320000.0,
            "estimated_sale_conservative": 285000.0,
            "estimated_sale_base": 320000.0,
            "renovation_type": "pesada",
            "renovation_budget": 0.0,
            "cash_needed": 220000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
        }
    )

    pending = {item["key"]: item for item in analysis["pending_items"]}
    assert pending["auction_modality"]["priority"] == "P1"
    assert pending["physical_condition"]["priority"] == "P1"
    assert pending["exit_plan"]["priority"] == "P2"


def test_small_capital_without_reserve_adds_operational_suitability_pending_item() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao Caixa",
            "strategy": "Primeiro imovel em leilao",
            "asking_price": 210000.0,
            "market_value_estimate": 360000.0,
            "estimated_sale_conservative": 330000.0,
            "estimated_sale_base": 360000.0,
            "renovation_type": "leve",
            "renovation_budget": 20000.0,
            "cash_needed": 245000.0,
            "available_capital_brl": 230000.0,
            "minimum_reserve_after_bid_brl": 25000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "plan_b": "Revender; alugar se atrasar.",
        }
    )

    capital_items = [item for item in analysis["pending_items"] if item["key"] == "capital_sizing"]
    assert capital_items and capital_items[0]["priority"] == "P2"


def test_clean_ugly_property_gets_high_positive_sourcing_score_without_relaxing_p0() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leiloeiro regional oficial",
            "source_url": "https://leiloeiro-regional.example/lote-881",
            "source_validation_status": "valid",
            "source_validation_reason": "Lote individual em leiloeiro oficial de cauda longa.",
            "strategy": "Imovel feio com fotos internas, reforma leve e revenda",
            "auction_modality": "extrajudicial",
            "asking_price": 180000.0,
            "market_value_estimate": 320000.0,
            "estimated_sale_conservative": 285000.0,
            "estimated_sale_base": 320000.0,
            "renovation_type": "leve",
            "renovation_budget": 28000.0,
            "cash_needed": 225000.0,
            "available_capital_brl": 290000.0,
            "minimum_reserve_after_bid_brl": 30000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "has_recent_photos": True,
            "low_competition_source": True,
            "plan_b": "Reformar e vender em ate 6 meses; alugar se venda atrasar.",
        }
    )

    assert analysis["pending_items"] == []
    assert analysis["sourcing"]["score"] >= 80
    assert analysis["sourcing"]["tier"] == "garimpo_qualificado"
    assert "reforma precificavel" in analysis["sourcing"]["signals"]
    assert "saida clara" in analysis["sourcing"]["signals"]


def test_blocked_legal_candidate_cannot_become_positive_sourcing_target() -> None:
    analysis = build_candidate_analysis(
        {
            "origin": "Leilao judicial",
            "strategy": "Direitos sobre imovel com desconto alto",
            "title": "Direitos sobre apartamento com 65% de desconto",
            "auction_modality": "judicial",
            "asking_price": 120000.0,
            "market_value_estimate": 300000.0,
            "estimated_sale_conservative": 260000.0,
            "estimated_sale_base": 300000.0,
            "renovation_budget": 15000.0,
            "cash_needed": 160000.0,
            "available_capital_brl": 250000.0,
            "occupancy_status": "desocupado",
            "has_registration": True,
            "has_edital": True,
            "condo_debt_known": True,
            "iptu_debt_known": True,
            "sale_comparables_count": 3,
            "rent_comparables_count": 3,
            "financing_validated": True,
            "has_recent_photos": True,
            "plan_b": "Revender.",
        }
    )

    assert analysis["suggested_status"] == "Descartado"
    assert analysis["sourcing"]["tier"] == "bloqueado_por_p0"
    assert analysis["sourcing"]["score"] <= 45

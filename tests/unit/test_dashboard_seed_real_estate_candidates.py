from __future__ import annotations

import json
from pathlib import Path


PINHEIROS_ALVES_GUIMARAES_SOURCE_URL = (
    "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/"
    "residencial-apto-cobertura-duplex-147m-02-vagas-pinheiros-sao-paulo-sp-"
    "imovel-banco-santander-2810257"
)


def test_folha_frazao_candidates_are_seeded_with_individual_validated_sources() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    rows = [
        row
        for row in payload.get("thesis_open_operations", [])
        if str(row.get("thesis_id", "")).startswith("IM-FOLHA-FRAZAO-")
    ]

    assert {row["thesis_id"] for row in rows} >= {
        "IM-FOLHA-FRAZAO-SAUDE-37528",
        "IM-FOLHA-FRAZAO-PARADA-INGLESA-37570",
        "IM-FOLHA-FRAZAO-CAMPINAS-37386",
        "IM-FOLHA-FRAZAO-BUTANTA-37467",
        "IM-FOLHA-FRAZAO-BELENZINHO-37539",
    }
    for row in rows:
        assert "/Auction/LotDetails/" in row["source_url"]
        assert row["real_estate_analysis"]["source_validation"]["status"] == "valid"
        assert row["real_estate_analysis"]["source_validation"]["reason"] == "Fonte individual validada."
        if row["thesis_id"] == "IM-FOLHA-FRAZAO-BUTANTA-37467":
            assert row["is_open"] is False
            assert row["outcome"] == "Descartado pelo radar"
        else:
            assert row["is_open"] is True


def test_saude_candidate_uses_comparable_supported_exit_value() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    row = next(
        row
        for row in payload.get("thesis_open_operations", [])
        if row.get("thesis_id") == "IM-FOLHA-FRAZAO-SAUDE-37528"
    )
    analysis = row["real_estate_analysis"]
    candidate = analysis["candidate"]

    assert row["current_price_brl"] == 600000
    assert row["expected_result_pct"] == 64.05
    assert analysis["scenarios"]["conservative"]["sale_price"] == 550000
    assert analysis["scenarios"]["base"]["sale_price"] == 600000
    assert analysis["scenarios"]["optimistic"]["sale_price"] == 650000
    assert analysis["scenarios"]["base"]["net_profit"] == 106378
    assert analysis["price_ceiling_status"] == "Dentro do teto"
    assert candidate["estimated_sale_base"] == 600000
    assert candidate["sale_comparables_count"] == 1
    assert analysis["valuation_evidence"]["source"] == "sale_comparables"
    assert analysis["valuation_evidence"]["sale_comparables_count"] == 1


def test_parada_inglesa_seed_includes_commercial_payment_scenarios() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    row = next(
        row
        for row in payload.get("thesis_open_operations", [])
        if row.get("thesis_id") == "IM-FOLHA-FRAZAO-PARADA-INGLESA-37570"
    )

    analysis = row["real_estate_analysis"]
    commercial = analysis["commercial_terms"]
    candidate_terms = analysis["candidate"]["payment_terms"]
    scenarios = {item["key"]: item for item in commercial["scenarios"]}

    assert len(candidate_terms) == 4
    assert commercial["recommended_scenario_key"] == "cash_discount"
    assert commercial["requires_ipca_assumption"] is True
    assert scenarios["cash_discount"]["effective_purchase_price"] == 359460
    assert scenarios["down_20_8x_no_interest"]["initial_cash"] == 79880
    assert scenarios["down_30_78x_price_ipca"]["decision"] == "alto_custo_financeiro"
    assert any(item["key"] == "commercial_terms_ipca" for item in analysis["pending_items"])


def test_seed_candidate_17_is_closed_as_learning_case() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    row = next(
        row
        for row in payload.get("thesis_open_operations", [])
        if row.get("thesis_id") == "IM-RADAR-17"
    )

    assert row["status"] == "Fechada"
    assert row["outcome"] == "Descartado pelo radar"
    assert row["real_estate_analysis"]["suggested_status"] == "Descartado"
    assert row["is_open"] is False
    assert "sem fonte individual" in row["exit_rule"]


def test_seed_butanta_morumbi_candidate_is_closed_by_local_demand_learning() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    row = next(
        row
        for row in payload.get("thesis_open_operations", [])
        if row.get("thesis_id") == "IM-FOLHA-FRAZAO-BUTANTA-37467"
    )
    analysis = row["real_estate_analysis"]

    assert row["status"] == "Fechada"
    assert row["outcome"] == "Descartado pelo radar"
    assert row["is_open"] is False
    assert "demanda local" in row["exit_rule"].lower()
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["local_demand_evidence"]["risk_level"] == "critico"
    assert analysis["local_demand_evidence"]["should_discard"] is True
    assert any(item["key"] == "local_buyer_demand" for item in analysis["pending_items"])


def test_seed_includes_target_neighborhood_pipeline_for_tomorrow() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    rows = [
        row
        for row in payload.get("thesis_open_operations", [])
        if str(row.get("thesis_id", "")).startswith("IM-RADAR-TARGET-")
    ]
    candidates = [
        row.get("real_estate_analysis", {}).get("candidate", {})
        for row in rows
    ]

    assert {candidate.get("neighborhood") for candidate in candidates} >= {
        "Pinheiros",
        "Perdizes",
        "Itaim Bibi",
        "Campo Belo",
        "Paraiso",
    }
    assert len(rows) >= 12
    assert len({candidate.get("strategy") for candidate in candidates}) >= 5
    assert all(row["front"] == "imoveis" for row in rows)
    assert all(row["is_open"] is True for row in rows)


def test_pinheiros_alves_guimaraes_uses_individual_lot_source_url() -> None:
    payload = json.loads(Path("data/dashboard_seed.json").read_text(encoding="utf-8"))
    row = next(
        row
        for row in payload.get("thesis_open_operations", [])
        if row.get("thesis_id") == "IM-RADAR-TARGET-PIN-03"
    )
    candidate = row["real_estate_analysis"]["candidate"]

    assert row["source_url"] == PINHEIROS_ALVES_GUIMARAES_SOURCE_URL
    assert row["source_validation"]["url"] == PINHEIROS_ALVES_GUIMARAES_SOURCE_URL
    assert candidate["source_url"] == PINHEIROS_ALVES_GUIMARAES_SOURCE_URL
    assert candidate["source_validation"]["url"] == PINHEIROS_ALVES_GUIMARAES_SOURCE_URL
    assert "/leilao-de-imovel/sp/sao-paulo/pinheiros" not in row["source_url"]

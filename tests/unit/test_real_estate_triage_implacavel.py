from scripts.run_real_estate_triage_implacavel import _triage_decision


def _row(**overrides):
    base = {
        "thesis_number": 1,
        "thesis_id": "IM-RADAR-TARGET-TEST",
        "front": "imoveis",
        "is_open": True,
        "source_url": "https://example.com/imovel/123",
        "source_validation_status": "valid",
        "expected_result_pct": 25.0,
        "real_estate_analysis": {
            "candidate": {},
            "listing_reading": {},
            "scenarios": {"optimistic": {"roi_pct": 30.0}},
            "valuation_evidence": {},
            "pending_items": [],
        },
    }
    base.update(overrides)
    return base


def test_triage_discards_rights_slug_before_p0_work() -> None:
    row = _row(
        source_url=(
            "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/"
            "residencial-direitos-apto-cond-edificio-imovel-2804088"
        )
    )

    decision = _triage_decision(row, [row])

    assert decision is not None
    assert decision["reason_code"] == "rights_over_asset"


def test_triage_discards_duplicate_padre_carvalho_shadow_case() -> None:
    canonical = _row(
        thesis_number=4180,
        thesis_id="IM-RADAR-TARGET-PIN-06",
        source_url="https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/rua-padre-carvalho-129/36388-226112",
    )
    duplicate = _row(
        thesis_number=4181,
        thesis_id="IM-RADAR-26",
        source_url="https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-casa-a-venda-em-leilao-imovel-bradesco-2844902",
        real_estate_analysis={
            "candidate": {"notes": "Casa 5 na Rua Padre Carvalho, 129."},
            "listing_reading": {},
            "scenarios": {"optimistic": {"roi_pct": 30.0}},
            "valuation_evidence": {},
            "pending_items": [],
        },
    )

    decision = _triage_decision(duplicate, [canonical, duplicate])

    assert decision is not None
    assert decision["reason_code"] == "duplicate_candidate"


def test_triage_keeps_padre_carvalho_canonical_candidate() -> None:
    canonical = _row(
        thesis_number=4180,
        thesis_id="IM-RADAR-TARGET-PIN-06",
        source_url="https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/rua-padre-carvalho-129/36388-226112",
        real_estate_analysis={
            "candidate": {"street": "Rua Padre Carvalho, 129 - Casa 5"},
            "listing_reading": {},
            "scenarios": {"optimistic": {"roi_pct": 40.0}},
            "valuation_evidence": {},
            "pending_items": [{"key": "eviction_risk", "priority": "P0"}],
        },
    )
    duplicate = _row(
        thesis_number=4181,
        thesis_id="IM-RADAR-26",
        source_url="https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-casa-a-venda-em-leilao-imovel-bradesco-2844902",
    )

    decision = _triage_decision(canonical, [canonical, duplicate])

    assert decision is None


def test_triage_discards_missing_individual_source() -> None:
    row = _row(source_url="")

    decision = _triage_decision(row, [row])

    assert decision is not None
    assert decision["reason_code"] == "missing_source"


def test_triage_discards_market_benchmark_without_candidate_signal() -> None:
    row = _row(
        source_url="https://www.floraimoveis.com.br/imovel/campinas/apartamento/3226394",
        expected_result_pct=0.0,
        real_estate_analysis={
            "candidate": {},
            "listing_reading": {},
            "scenarios": {"optimistic": {"roi_pct": 0.0}},
            "valuation_evidence": {"risk_flag": "weak_neighborhood_benchmark"},
            "pending_items": [],
        },
    )

    decision = _triage_decision(row, [row])

    assert decision is not None
    assert decision["reason_code"] == "benchmark_not_candidate"


def test_triage_discards_valid_source_when_optimistic_roi_is_below_target() -> None:
    row = _row(
        expected_result_pct=11.11,
        real_estate_analysis={
            "candidate": {},
            "listing_reading": {},
            "scenarios": {"optimistic": {"roi_pct": 16.67}},
            "valuation_evidence": {},
            "pending_items": [],
        },
    )

    decision = _triage_decision(row, [row])

    assert decision is not None
    assert decision["reason_code"] == "optimistic_roi_below_target"


def test_triage_discards_base_roi_below_target_even_when_optimistic_is_positive() -> None:
    row = _row(
        source_validation_status="ambiguous",
        expected_result_pct=18.69,
        real_estate_analysis={
            "candidate": {},
            "listing_reading": {},
            "scenarios": {
                "base": {"roi_pct": 18.69},
                "optimistic": {"roi_pct": 24.62},
            },
            "valuation_evidence": {},
            "pending_items": [{"key": "debt_total", "priority": "P0"}],
        },
    )

    decision = _triage_decision(row, [row])

    assert decision is not None
    assert decision["reason_code"] == "base_roi_below_target"

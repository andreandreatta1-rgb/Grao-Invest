from __future__ import annotations

from app.services.real_estate_candidate_generation import (
    STRATEGY_BLUEPRINTS,
    TERRITORY_BLUEPRINTS,
    generate_condominium_requalification_watchlist,
    generate_strategy_candidate_watchlist,
    generate_strategy_territory_candidate_briefs,
    strategy_territory_report,
)


def test_strategy_territory_generation_covers_every_strategy_and_territory() -> None:
    briefs = generate_strategy_territory_candidate_briefs()

    assert len(briefs) == len(STRATEGY_BLUEPRINTS) * len(TERRITORY_BLUEPRINTS)
    assert {item["strategy_id"] for item in briefs} == {
        item["strategy_id"] for item in STRATEGY_BLUEPRINTS
    }
    assert {item["territory_id"] for item in briefs} == {
        item["territory_id"] for item in TERRITORY_BLUEPRINTS
    }
    assert len({item["brief_id"] for item in briefs}) == len(briefs)
    assert all(item["trust_level"] == "hypothesis" for item in briefs)
    assert all(item["diligence_checklist"] for item in briefs)


def test_condominium_requalification_watchlist_keeps_source_confirmed_signals_separate() -> None:
    watchlist = generate_condominium_requalification_watchlist()

    assert len(watchlist) >= 4
    assert all(item["brief_type"] == "condominium_requalification_signal" for item in watchlist)
    assert all(item["trust_level"] == "source_confirmed" for item in watchlist)
    assert all(item["source_url"].startswith("https://") for item in watchlist)
    assert {
        "confirmar unidade disponivel no edificio",
        "confirmar ata/escopo da obra condominial",
        "comparar preco pedido contra unidades sem retrofit no mesmo raio",
    }.issubset(set(watchlist[0]["diligence_checklist"]))


def test_strategy_candidate_watchlist_has_sources_for_every_strategy() -> None:
    watchlist = generate_strategy_candidate_watchlist()
    strategy_ids = {item["strategy_id"] for item in STRATEGY_BLUEPRINTS}

    assert len(TERRITORY_BLUEPRINTS) >= 12
    assert len(watchlist) >= len(STRATEGY_BLUEPRINTS) * 2
    assert {item["strategy_id"] for item in watchlist} == strategy_ids
    assert all(item["brief_type"] == "strategy_source_candidate" for item in watchlist)
    assert all(item["trust_level"] == "source_listed" for item in watchlist)
    assert all(str(item["source_url"]).startswith("https://") for item in watchlist)
    assert all("Nao vira tese de compra" in str(item["decision_rule"]) for item in watchlist)
    assert all(item["diligence_checklist"] for item in watchlist)


def test_strategy_territory_report_summarizes_matrix_and_watchlist() -> None:
    report = strategy_territory_report()

    assert report["summary"]["strategy_count"] == len(STRATEGY_BLUEPRINTS)
    assert report["summary"]["territory_count"] == len(TERRITORY_BLUEPRINTS)
    assert report["summary"]["matrix_brief_count"] == (
        len(STRATEGY_BLUEPRINTS) * len(TERRITORY_BLUEPRINTS)
    )
    assert report["summary"]["source_confirmed_requalification_count"] >= 4
    assert report["summary"]["source_candidate_count"] >= len(STRATEGY_BLUEPRINTS) * 2
    assert report["matrix_briefs"]
    assert report["strategy_candidate_watchlist"]
    assert report["condominium_requalification_watchlist"]

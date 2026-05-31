from __future__ import annotations

from app.services.real_estate_candidate_generation import (
    STRATEGY_BLUEPRINTS,
    TERRITORY_BLUEPRINTS,
    generate_auctioneer_sourcing_report,
    generate_active_auction_portal_report,
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


def test_auctioneer_sourcing_report_maps_official_long_tail_contact_sources() -> None:
    report = generate_auctioneer_sourcing_report()

    assert report["summary"]["official_directory_count"] == 1
    assert report["summary"]["official_contact_count"] >= 12
    assert report["summary"]["scope_cities"] == ["Sao Paulo", "Campinas"]
    assert {item["uf"] for item in report["official_directories"]} == {"SP"}
    assert all(item["source_url"].startswith("https://") for item in report["official_directories"])
    assert all(item["contact_strategy"] for item in report["official_directories"])
    assert {item["city"] for item in report["official_contacts"]} <= {"Sao Paulo", "Campinas"}
    assert {"cauda_longa", "estabelecido"}.issubset(
        {item["competition_tier"] for item in report["official_contacts"]}
    )
    sent_contacts = [item for item in report["official_contacts"] if item.get("outreach_sent_at")]
    pending_contacts = [
        item for item in report["official_contacts"] if item.get("outreach_status") == "enviado"
    ]
    response_contacts = [
        item for item in report["official_contacts"] if item.get("response_received_at")
    ]
    assert report["summary"]["outreach_sent_count"] == 4
    assert report["summary"]["outreach_response_count"] == 1
    assert report["summary"]["outreach_no_real_estate_count"] == 1
    assert report["summary"]["outreach_pending_response_count"] == 3
    assert {item["id"] for item in sent_contacts} == {
        "auctioneer-sp-599",
        "auctioneer-sp-602",
        "auctioneer-campinas-843",
        "auctioneer-campinas-911",
    }
    assert all(item["outreach_channel"] == "Gmail" for item in sent_contacts)
    assert all(item["next_follow_up_at"] == "2026-05-22" for item in pending_contacts)
    assert response_contacts[0]["id"] == "auctioneer-sp-599"
    assert response_contacts[0]["outreach_status"] == "respondido_sem_imoveis"
    assert "nao trabalha com imoveis" in response_contacts[0]["response_summary"]
    assert report["outreach_playbook"][0]["stage"] == "coleta_oficial"
    assert "sao paulo capital e campinas" in report["summary"]["actionability"].lower()


def test_active_auction_portal_report_adds_leeilon_and_leilaoimovel_sources() -> None:
    report = generate_active_auction_portal_report()
    sources = report["sources"]

    assert report["summary"]["source_count"] >= 8
    assert report["summary"]["portal_counts"]["Leeilon"] >= 5
    assert report["summary"]["portal_counts"]["Leilao Imovel"] >= 1
    assert report["summary"]["role_counts"]["aggregator_clue"] >= 5
    assert report["summary"]["role_counts"]["primary_legal"] >= 2
    assert all(source["next_search_queries"] for source in sources)
    assert all(source["next_action"].startswith("Abrir a pagina") for source in sources)
    assert any("Pinheiros" in source["neighborhood"] for source in sources)
    assert any("Perdizes" in source["neighborhood"] for source in sources)
    assert any("Campinas" in source["neighborhood"] for source in sources)


def test_strategy_territory_report_summarizes_matrix_and_watchlist() -> None:
    report = strategy_territory_report()

    assert report["summary"]["strategy_count"] == len(STRATEGY_BLUEPRINTS)
    assert report["summary"]["territory_count"] == len(TERRITORY_BLUEPRINTS)
    assert report["summary"]["matrix_brief_count"] == (
        len(STRATEGY_BLUEPRINTS) * len(TERRITORY_BLUEPRINTS)
    )
    assert report["summary"]["source_confirmed_requalification_count"] >= 4
    assert report["summary"]["source_candidate_count"] >= len(STRATEGY_BLUEPRINTS) * 2
    assert report["summary"]["auctioneer_directory_count"] == 1
    assert report["summary"]["auctioneer_contact_count"] >= 12
    assert report["summary"]["active_auction_portal_source_count"] >= 8
    assert report["matrix_briefs"]
    assert report["strategy_candidate_watchlist"]
    assert report["condominium_requalification_watchlist"]
    assert report["auctioneer_sourcing"]["official_directories"]
    assert report["active_auction_portal_discovery"]["sources"]

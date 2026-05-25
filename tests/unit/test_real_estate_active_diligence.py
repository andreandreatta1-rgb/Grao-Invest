from __future__ import annotations

import json
from pathlib import Path

import scripts.run_real_estate_active_diligence as diligence


def test_extracts_primary_evidence_from_frazao_lot_page() -> None:
    html = """
    <html><body>
      <h1>SÃO PAULO/SP - BAIRRO SAÚDE - APARTAMENTO - IMÓVEL OCUPADO.</h1>
      <p>Rua Abagiba nº 583, apto 21, Edifício Missouri.</p>
      <p>Área privativa: 74,140m². Lance mínimo R$ 388.700,00.</p>
      <p>Matrícula: 131.197 do 14º SRI de São Paulo/SP - CNM 111211.2.0131197-89.</p>
      <p>Condomínio e IPTU serão quitados pelo vendedor até a transferência da posse.</p>
      <p>Imovel ocupado. Sem visitacao.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
        html,
    )

    assert evidence["status"] == "validado"
    assert evidence["occupancy_status"] == "ocupado"
    assert evidence["registration"]["matricula"] == "131.197"
    assert evidence["registration"]["registry"] == "14o SRI de Sao Paulo/SP"
    assert evidence["debts"]["seller_pays_condo_iptu_until_possession_transfer"] is True
    assert evidence["minimum_bid_brl"] == 388700.0


def test_extracts_leilaoimovel_chain_to_edital_and_official_auctioneer() -> None:
    html = """
    <html><body>
      <p>O Leilao Imovel nao e leiloeiro. Voce sera redirecionado para o site do leiloeiro WebLeiloes.</p>
      <a href="https://static.suporteleiloes.com.br/webleiloescombr/bens/16156/arquivos/sl-bem-16156-edital.pdf">Edital</a>
      <a href="https://www.webleiloes.com.br/leilao/imovel/16156">Ver anuncio no leiloeiro</a>
      <p>Matricula 81.237 - 13o CRI de Sao Paulo/SP. Contribuinte 013.016.0640-5.</p>
      <p>Debitos da acao R$381.674,72 (maio/2026). 2a Praca R$ 339.845,69.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pinheiros-2803839",
        html,
    )

    assert evidence["status"] == "validado"
    assert evidence["aggregator_url"].startswith("https://www.leilaoimovel.com.br/")
    assert evidence["official_url"] == "https://www.webleiloes.com.br/leilao/imovel/16156"
    assert evidence["edital_url"].endswith("sl-bem-16156-edital.pdf")
    assert evidence["registration"]["matricula"] == "81.237"
    assert evidence["debts"]["action_debt_brl"] == 381674.72


def test_prefers_property_registration_with_registry_over_condominium_land_record() -> None:
    html = """
    <p>terreno descrito na matrícula nº 74773, na qual foi registrada a instituição de condomínio.</p>
    <p>Observações Matrícula Nº: 81.237 - 13º CRI de São Paulo/SP. Contribuinte Nº: 013.016.0640-5.</p>
    """

    evidence = diligence.extract_evidence(
        "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pinheiros-2803839",
        html,
    )

    assert evidence["registration"]["matricula"] == "81.237"
    assert evidence["registration"]["registry"] == "13o CRI de Sao Paulo/SP"


def test_rejects_static_assets_and_404_pages_as_official_evidence() -> None:
    html = """
    <html><body>
      <h1>404: This page could not be found.</h1>
      <script src="/_next/static/chunks/407242e4272f7582.js"></script>
      <a href="/_next/static/chunks/407242e4272f7582.js">chunk</a>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.proleilao.com.br/leilao-de-imoveis/sp/sao-paulo/apartamento_i36034",
        html,
    )

    assert evidence["status"] == "nao_encontrado_apos_busca"
    assert not evidence["official_url"]


def test_applies_diligence_to_open_seed_and_closes_occupied_first_operation(tmp_path: Path) -> None:
    seed_path = tmp_path / "dashboard_seed.json"
    report_json = tmp_path / "diligence.json"
    report_md = tmp_path / "diligence.md"
    seed_path.write_text(
        json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_number": 4033,
                        "thesis_id": "IM-FOLHA-FRAZAO-SAUDE-37528",
                        "front": "imoveis",
                        "is_open": True,
                        "status": "Aberta - Atencao",
                        "outcome": "Pendencias abertas",
                        "source_url": "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528",
                        "source_validation_status": "valid",
                        "real_estate_analysis": {
                            "score": 82,
                            "confidence": 55,
                            "suggested_status": "Aberto com pendencias",
                            "next_action": "Avaliar risco de imovel ocupado",
                            "pending_items": [
                                {"key": "occupied_auction", "title": "Avaliar risco de imovel ocupado", "priority": "P0", "status": "aberta"},
                                {"key": "registration", "title": "Buscar matricula atualizada", "priority": "P0", "status": "aberta"},
                                {"key": "debts", "title": "Confirmar dividas e responsabilidades", "priority": "P0", "status": "aberta"},
                                {"key": "sale_comparables", "title": "Buscar 3 comparaveis de venda", "priority": "P1", "status": "aberta"},
                            ],
                            "clarified_items": [],
                            "candidate": {},
                            "source_validation": {"status": "valid", "reason": "Fonte individual validada."},
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html_by_url = {
        "https://www.frazaoleiloes.com.br/Auction/LotDetails/37528": """
        <h1>SAO PAULO/SP - BAIRRO SAUDE - APARTAMENTO - IMOVEL OCUPADO.</h1>
        <p>Matricula no 131.197 do 14o SRI de Sao Paulo/SP.</p>
        <p>Condominio e IPTU serao quitados pelo vendedor ate transferencia da posse.</p>
        """,
    }

    summary = diligence.run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        fetcher=lambda url: html_by_url[url],
    )

    updated = json.loads(seed_path.read_text(encoding="utf-8"))
    row = updated["thesis_open_operations"][0]
    analysis = row["real_estate_analysis"]

    assert summary["investigated_count"] == 1
    assert row["is_open"] is False
    assert row["status"] == "Fechada"
    assert row["outcome"] == "Descartado pelo radar"
    assert "ocupado" in row["exit_rule"].lower()
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Fechar candidato: imóvel ocupado sem plano aprovado"
    assert {item["key"] for item in analysis["pending_items"]} == {"sale_comparables"}
    assert {item["key"] for item in analysis["clarified_items"]} >= {
        "occupancy",
        "registration",
        "debts",
    }
    assert report_json.exists()
    assert "4033" in report_md.read_text(encoding="utf-8")

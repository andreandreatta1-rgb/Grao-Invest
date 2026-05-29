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


def test_course_antibodies_flag_judicial_without_process_access() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - apartamento em Perdizes</h1>
      <p>2a praca judicial com desconto sobre avaliacao.</p>
      <p>Imovel desocupado. Lance minimo R$ 420.000,00.</p>
      <p>O arrematante deve observar auto de arrematacao e carta de arrematacao.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-perdizes",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "judicial_process_access" in antibody_keys
    assert "judicial_post_auction_plan" not in antibody_keys


def test_course_antibodies_flag_fiduciary_chain_and_conditional_bid() -> None:
    html = """
    <html><body>
      <h1>Leilao extrajudicial AF - casa ocupada</h1>
      <p>Alienacao fiduciaria. Ocupada (AF). Lance condicionado sujeito a aceite do banco.</p>
      <p>2a praca sem minimo oficial publicado nesta pagina.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/casa-af",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "fiduciary_chain_unproven" in antibody_keys
    assert "conditional_bid_acceptance" in antibody_keys
    assert "official_minimum_bid" in antibody_keys


def test_course_antibodies_flag_caixa_debt_proof_without_blocking_known_direct_sale() -> None:
    html = """
    <html><body>
      <h1>Imovel Caixa - venda direta online</h1>
      <p>Casa em Jardim Aeroporto. Proposta pela internet.</p>
      <p>Consultar condicoes de pagamento e debitos antes da proposta.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnImovel=123",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "caixa_sale_modality_unproven" not in antibody_keys
    assert "caixa_debt_regularization_proof" in antibody_keys


def test_market_listing_that_mentions_caixa_financing_does_not_trigger_caixa_antibodies() -> None:
    html = """
    <html><body>
      <h1>Apartamento a venda em Campinas</h1>
      <p>Aceita financiamento bancario e simulacao de caixa do comprador.</p>
      <p>Condominio informado, IPTU informado e visita com corretor.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.chavesnamao.com.br/imovel/apartamento-a-venda-campinas",
        html,
    )

    assert evidence["course_antibodies"] == []


def test_navigation_filter_text_does_not_trigger_course_antibodies() -> None:
    html = """
    <html><body>
      <h1>Apartamento em Leilao em Sao Paulo / SP</h1>
      <nav>
        Filtros Localidade Selecione as localidades ImÃ³veis Caixa Compra Direta
        Leilao SFI Caixa Licitacao Aberta Caixa Modalidade Comprei PGFN
        Extrajudicial Judicial Venda Direta Arrematante paga ate 10% da avaliacao
        Apartamento Casa Comercial Galpao Garagem Terreno Bancos FGTS Financiamento
        Imoveis Caixa Debito Condominio Arrematante Paga Outros Particular
      </nav>
      <p>Rua Capote Valente, 134. Matricula 81.237 do 13o CRI.</p>
      <a href="https://www.webleiloes.com.br/leilao/imovel/16156">Ver anuncio no leiloeiro</a>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/apto-pinheiros-2803839",
        html,
    )

    assert evidence["course_antibodies"] == []


def test_course_antibodies_flag_unclear_execution_modality_for_auction() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - apartamento em Perdizes</h1>
      <p>2a praca judicial. Lance minimo R$ 420.000,00.</p>
      <p>O edital informa avaliacao e comissao, mas nao diz como participar do leilao.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-perdizes",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "auction_modality_unclear" in antibody_keys


def test_course_antibodies_flag_online_registration_and_missing_closing_rule() -> None:
    html = """
    <html><body>
      <h1>Leilao online - casa em Pinheiros</h1>
      <p>Lance minimo R$ 900.000,00.</p>
      <p>Para ofertar lance, faca cadastro previo, habilitacao e envio de documentos.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/casa-online",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "bidder_registration_unproven" in antibody_keys
    assert "online_closing_rule_unproven" in antibody_keys
    assert "auction_modality_unclear" not in antibody_keys


def test_course_antibodies_respect_online_closing_rule_when_stated() -> None:
    html = """
    <html><body>
      <h1>Leilao online - apartamento em Pinheiros</h1>
      <p>Usuario deve estar cadastrado e habilitado antes de ofertar lance.</p>
      <p>Encerramento com prorrogacao automatica de tres minutos a cada novo lance.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/apartamento-online",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "bidder_registration_unproven" in antibody_keys
    assert "online_closing_rule_unproven" not in antibody_keys


def test_course_antibodies_flag_hybrid_risk_and_presential_proxy_requirement() -> None:
    html = """
    <html><body>
      <h1>Leilao hibrido presencial e online - sobrado em Pinheiros</h1>
      <p>O leilao ocorrera no auditorio do leiloeiro e tambem pela plataforma online.</p>
      <p>Participacao por representante exige procuracao com poderes especificos.</p>
      <p>Encerramento com prorrogacao por novo lance.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/sobrado-pinheiros",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "hybrid_competition_risk" in antibody_keys
    assert "representative_proxy_unproven" in antibody_keys
    assert "auction_modality_unclear" not in antibody_keys


def test_course_antibodies_flag_labor_auction_specific_risks() -> None:
    html = """
    <html><body>
      <h1>Hasta publica unificada da Justica do Trabalho - TRT 2</h1>
      <p>Vara do Trabalho de Sao Paulo. Processo 1001234-56.2024.5.02.0001.</p>
      <p>Lote 12 com sala comercial e equipamentos da executada.</p>
      <p>Leilao online com cadastro previo no site do leiloeiro.</p>
      <p>Lance minimo R$ 250.000,00.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.trt2.jus.br/leiloes/hasta-publica-unificada/lote-12",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "labor_auction_core_terms_unproven" in antibody_keys
    assert "labor_auction_debt_responsibility_unproven" in antibody_keys
    assert "labor_auction_payment_terms_unproven" in antibody_keys
    assert "labor_lot_unit_sale_unproven" in antibody_keys


def test_course_antibodies_respect_complete_labor_auction_terms() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial trabalhista - TRT 2</h1>
      <p>Vara do Trabalho de Sao Paulo. Processo 1001234-56.2024.5.02.0001.</p>
      <p>Lote 12 - Matricula 81.237 do 13o CRI de Sao Paulo/SP.</p>
      <p>Avaliacao R$ 500.000,00. Lance minimo R$ 250.000,00.</p>
      <p>IPTU sub-roga no preco da arrematacao conforme artigo 130 do CTN.</p>
      <p>Condominio e demais debitos ficam a cargo do arrematante.</p>
      <p>Comissao do leiloeiro de 5%, sinal de 20% e deposito judicial do saldo em 24 horas.</p>
      <p>Leilao online com cadastro previo, habilitacao e encerramento com prorrogacao por novo lance.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.trt2.jus.br/leiloes/hasta-publica-unificada/lote-12",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "labor_auction_core_terms_unproven" not in antibody_keys
    assert "labor_auction_debt_responsibility_unproven" not in antibody_keys
    assert "labor_auction_payment_terms_unproven" not in antibody_keys
    assert "labor_lot_unit_sale_unproven" not in antibody_keys


def test_course_antibodies_flag_remote_valuation_and_streetview_gaps() -> None:
    html = """
    <html><body>
      <h1>Leilao online - apartamento em Pinheiros</h1>
      <p>Lance minimo R$ 520.000,00.</p>
      <p>Valor de mercado estimado em R$ 780.000,00 e saida projetada em R$ 720.000,00.</p>
      <p>A tese usa um anuncio avulso como referencia de preco.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-pinheiros",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "remote_valuation_triangulation_unproven" in antibody_keys
    assert "streetview_condition_unchecked" in antibody_keys


def test_course_antibodies_respect_triangulated_remote_valuation() -> None:
    html = """
    <html><body>
      <h1>Leilao online - apartamento em Pinheiros</h1>
      <p>Lance minimo R$ 520.000,00.</p>
      <p>Valor de mercado validado por Viva Real, DataZap e comparaveis do mesmo condominio.</p>
      <p>Google Street View confirma fachada, entorno, conservacao da rua e acesso.</p>
      <p>Matricula atualizada e certidao de onus foram abertas no cartorio.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-pinheiros",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "remote_valuation_triangulation_unproven" not in antibody_keys
    assert "streetview_condition_unchecked" not in antibody_keys


def test_course_antibodies_flag_sensitive_person_data_review() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - casa em Campinas</h1>
      <p>Lance minimo R$ 450.000,00. Valor de mercado validado por DataZap e Viva Real.</p>
      <p>Investigacao por Procob, Consulta Facil, CPF do executado, telefones, parentes e Facebook.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/casa-campinas",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "sensitive_person_data_minimization" in antibody_keys


def test_course_antibodies_respect_public_source_minimization() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - casa em Campinas</h1>
      <p>Lance minimo R$ 450.000,00. Valor de mercado validado por DataZap e Viva Real.</p>
      <p>Facebook e telefone foram citados apenas como fontes publicas permitidas.</p>
      <p>LGPD aplicada: nao armazenar CPF, telefone ou dado pessoal bruto; registrar apenas conclusao operacional.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/casa-campinas",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "sensitive_person_data_minimization" not in antibody_keys


def test_course_antibodies_flag_missing_market_selection_map() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - apartamento em Vila Mariana</h1>
      <p>Lance minimo R$ 510.000,00.</p>
      <p>A tese projeta revenda em 3 meses, lucro de 35% e diz que e uma das melhores ofertas.</p>
      <p>Valor de mercado validado por Viva Real, DataZap e comparaveis do mesmo condominio.</p>
      <p>Google Street View confirma fachada, entorno, conservacao da rua e acesso.</p>
      <p>Matricula atualizada e certidao de onus foram abertas no cartorio.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-vila-mariana",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "market_rotation_map_unproven" in antibody_keys


def test_course_antibodies_respect_market_selection_map() -> None:
    html = """
    <html><body>
      <h1>Leilao judicial - apartamento em Vila Mariana</h1>
      <p>Lance minimo R$ 510.000,00.</p>
      <p>Revenda em 3 meses validada no mapa do investimento.</p>
      <p>Bairro e microregiao conhecidos, condominio com rotatividade alta e ultimo imovel vendido em 45 dias.</p>
      <p>Corretor local e imobiliarias pequenas confirmaram demanda e preco de saida.</p>
      <p>Valor de mercado validado por Viva Real, DataZap e comparaveis do mesmo condominio.</p>
      <p>Google Street View confirma fachada, entorno, conservacao da rua e acesso.</p>
      <p>Matricula atualizada e certidao de onus foram abertas no cartorio.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-vila-mariana",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "market_rotation_map_unproven" not in antibody_keys


def test_course_antibodies_flag_caixa_financing_readiness_gap() -> None:
    html = """
    <html><body>
      <h1>Imovel Caixa em venda direta online</h1>
      <p>Casa retomada da Caixa com venda direta, FGTS e financiamento.</p>
      <p>E uma tese para arrematar sem dinheiro, com pouca entrada e credito bancario.</p>
      <p>Valor de mercado validado por DataZap, Viva Real e comparaveis do mesmo bairro.</p>
      <p>Google Maps confirma fachada, entorno e acesso. Matricula atualizada aberta no cartorio.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnImovel=123",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "caixa_financing_readiness_unproven" in antibody_keys


def test_course_antibodies_respect_caixa_financing_readiness() -> None:
    html = """
    <html><body>
      <h1>Imovel Caixa em venda direta online</h1>
      <p>Casa retomada da Caixa com venda direta, FGTS e financiamento permitidos pela regra oficial.</p>
      <p>Credito pre-aprovado, simulacao aprovada, FGTS confirmado e entrada reservada.</p>
      <p>Valor de mercado validado por DataZap, Viva Real e comparaveis do mesmo bairro.</p>
      <p>Google Maps confirma fachada, entorno e acesso. Matricula atualizada aberta no cartorio.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnImovel=123",
        html,
    )

    antibody_keys = {item["key"] for item in evidence["course_antibodies"]}
    assert "caixa_financing_readiness_unproven" not in antibody_keys


def test_market_registration_text_does_not_trigger_execution_antibodies() -> None:
    html = """
    <html><body>
      <h1>Casa a venda em Campinas</h1>
      <p>Cadastre-se para receber alertas, fazer visita online e falar com o corretor.</p>
      <p>Aceita financiamento bancario. Nao ha leilao.</p>
    </body></html>
    """

    evidence = diligence.extract_evidence(
        "https://www.chavesnamao.com.br/imovel/casa-a-venda-campinas",
        html,
    )

    assert evidence["course_antibodies"] == []


def test_active_diligence_removes_stale_course_antibodies_when_chain_is_proven(tmp_path: Path) -> None:
    seed_path = tmp_path / "dashboard_seed.json"
    report_json = tmp_path / "diligence.json"
    report_md = tmp_path / "diligence.md"
    source_url = "https://www.portalzuk.com.br/imovel/sp/sao-paulo/pinheiros/casa-af"
    seed_path.write_text(
        json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_number": 4043,
                        "thesis_id": "IM-AF-PROVEN",
                        "front": "imoveis",
                        "is_open": True,
                        "status": "Aberta - Atencao",
                        "outcome": "Pendencias abertas",
                        "source_url": source_url,
                        "source_validation_status": "valid",
                        "real_estate_analysis": {
                            "score": 82,
                            "confidence": 70,
                            "suggested_status": "Aberto com pendencias",
                            "next_action": "Desocupacao por conta do comprador",
                            "pending_items": [
                                {"key": "eviction_risk", "title": "Desocupacao por conta do comprador", "priority": "P0", "status": "aberta"},
                                {"key": "fiduciary_chain_unproven", "title": "Provar cadeia fiduciaria", "priority": "P0", "status": "aberta"},
                            ],
                            "clarified_items": [],
                            "candidate": {
                                "strategy": "2a praca extrajudicial Bradesco",
                                "source_url": source_url,
                                "listing_description": (
                                    "Edital Zuk/Bradesco Lei 9.514/97. Ocupado (AF). "
                                    "Matricula Av.11 consolidou a propriedade fiduciaria "
                                    "em nome do Banco Bradesco S/A."
                                ),
                            },
                            "source_validation": {"status": "valid", "reason": "Fonte oficial validada."},
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html_by_url = {
        source_url: """
        <html><body>
          <nav>Tipo de imovel Residenciais Leiloes Judiciais Leiloes Extrajudiciais</nav>
          <p>Casa ocupada. Lance minimo R$ 1.610.000,00. Matricula 22.175 do 10o CRI de Sao Paulo/SP.</p>
          <a href="https://documentacaoleilao.portalzuk.com.br/edital.pdf">Edital</a>
        </body></html>
        """,
    }

    diligence.run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        fetcher=lambda url: html_by_url[url],
    )

    updated = json.loads(seed_path.read_text(encoding="utf-8"))
    analysis = updated["thesis_open_operations"][0]["real_estate_analysis"]
    pending = {item["key"]: item for item in analysis["pending_items"]}

    assert "fiduciary_chain_unproven" not in pending
    assert "eviction_risk" in pending
    assert analysis["diligence_result"]["course_antibodies"] == []


def test_applies_course_antibodies_to_active_seed(tmp_path: Path) -> None:
    seed_path = tmp_path / "dashboard_seed.json"
    report_json = tmp_path / "diligence.json"
    report_md = tmp_path / "diligence.md"
    seed_path.write_text(
        json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_number": 4042,
                        "thesis_id": "IM-JUDICIAL-PERDIZES",
                        "front": "imoveis",
                        "is_open": True,
                        "status": "Aberta - Atencao",
                        "outcome": "Pendencias abertas",
                        "source_url": "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-perdizes",
                        "source_validation_status": "ambiguous",
                        "real_estate_analysis": {
                            "score": 78,
                            "confidence": 50,
                            "suggested_status": "Aberto com pendencias",
                            "next_action": "Validar fonte manualmente",
                            "pending_items": [
                                {"key": "source_validation", "title": "Validar fonte manualmente", "priority": "P0", "status": "aberta"},
                                {"key": "sale_comparables", "title": "Buscar 3 comparaveis de venda", "priority": "P1", "status": "aberta"},
                            ],
                            "clarified_items": [],
                            "candidate": {},
                            "source_validation": {"status": "ambiguous", "reason": "Fonte ainda nao validada."},
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    html_by_url = {
        "https://www.megaleiloes.com.br/leiloes/imoveis/apartamento-perdizes": """
        <h1>Leilao judicial - apartamento em Perdizes</h1>
        <p>Imovel desocupado. 2a praca judicial. Lance minimo R$ 420.000,00.</p>
        <p>Sem numero do processo ou link para autos nesta pagina.</p>
        """,
    }

    diligence.run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        fetcher=lambda url: html_by_url[url],
    )

    updated = json.loads(seed_path.read_text(encoding="utf-8"))
    analysis = updated["thesis_open_operations"][0]["real_estate_analysis"]
    pending = {item["key"]: item for item in analysis["pending_items"]}

    assert "source_validation" not in pending
    assert pending["judicial_process_access"]["priority"] == "P0"
    assert pending["judicial_post_auction_plan"]["priority"] == "P0"
    assert analysis["next_action"] == "Abrir processo judicial/autos"
    assert analysis["diligence_result"]["course_antibodies"] == [
        "judicial_process_access",
        "judicial_post_auction_plan",
        "auction_modality_unclear",
    ]


def test_run_active_diligence_accepts_utf8_bom_seed(tmp_path: Path) -> None:
    seed_path = tmp_path / "dashboard_seed.json"
    report_json = tmp_path / "diligence.json"
    report_md = tmp_path / "diligence.md"
    seed_path.write_text(
        json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_number": 4044,
                        "thesis_id": "IM-BOM",
                        "front": "imoveis",
                        "is_open": True,
                        "status": "Aberta - Atencao",
                        "source_url": "",
                        "real_estate_analysis": {
                            "pending_items": [
                                {"key": "occupancy", "title": "Confirmar ocupacao", "priority": "P0", "status": "aberta"}
                            ],
                            "clarified_items": [],
                            "candidate": {},
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8-sig",
    )

    summary = diligence.run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        fetcher=lambda url: "",
    )

    assert summary["investigated_count"] == 1
    assert json.loads(seed_path.read_text(encoding="utf-8"))


def test_closes_out_of_scope_city_rows_without_fetching(tmp_path: Path) -> None:
    seed_path = tmp_path / "dashboard_seed.json"
    report_json = tmp_path / "diligence.json"
    report_md = tmp_path / "diligence.md"
    seed_path.write_text(
        json.dumps(
            {
                "thesis_open_operations": [
                    {
                        "thesis_number": 4101,
                        "thesis_id": "IM-OUT",
                        "front": "imoveis",
                        "is_open": True,
                        "status": "Aberta - Atencao",
                        "outcome": "Pendencias abertas",
                        "source_url": "https://www.imovelweb.com.br/propriedades/oportunidade-unica-em-bauru-sp-3034244339.html",
                        "source_validation_status": "valid",
                        "real_estate_analysis": {
                            "pending_items": [
                                {"key": "occupancy", "title": "Confirmar ocupacao", "priority": "P0", "status": "aberta"},
                                {"key": "sale_comparables", "title": "Buscar 3 comparaveis de venda", "priority": "P1", "status": "aberta"},
                            ],
                            "clarified_items": [],
                            "candidate": {"city": "Bauru", "neighborhood": "Vila Aviacao"},
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8-sig",
    )

    def _raiser(_: str) -> str:
        raise AssertionError("fetcher nao deveria ser chamado em close_out_of_scope_only")

    summary = diligence.run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        fetcher=_raiser,
        close_out_of_scope_only=True,
    )

    updated = json.loads(seed_path.read_text(encoding="utf-8"))
    row = updated["thesis_open_operations"][0]
    analysis = row["real_estate_analysis"]

    assert summary["investigated_count"] == 1
    assert summary["closed_count"] == 1
    assert row["is_open"] is False
    assert row["status"] == "Fechada"
    assert row["outcome"] == "Fora do escopo"
    assert "fora do escopo" in str(row.get("exit_rule") or "").lower()
    assert analysis["suggested_status"] == "Descartado"
    assert analysis["next_action"] == "Fechar candidato: fora do escopo (SP capital + Campinas)"
    assert {item["key"] for item in analysis["pending_items"]} == {"sale_comparables"}
    assert report_json.exists()
    assert "IM-OUT" in report_md.read_text(encoding="utf-8")


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

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STRATEGY_BLUEPRINTS: list[dict[str, object]] = [
    {
        "strategy_id": "leilao_venda_online",
        "label": "Leilao/venda online",
        "asset_profile": "apartamento com desconto claro e diligencia documental forte",
        "renovation_profile": "maquiagem ou reforma leve",
        "target_discount_pct": 30,
        "target_roi_pct": 25,
    },
    {
        "strategy_id": "venda_direta_negociacao",
        "label": "Venda direta com negociacao",
        "asset_profile": (
            "unidade com vendedor flexivel, tempo de anuncio alto ou preco fora do padrao"
        ),
        "renovation_profile": "maquiagem inteligente",
        "target_discount_pct": 12,
        "target_roi_pct": 18,
    },
    {
        "strategy_id": "arbitragem_sem_reforma",
        "label": "Arbitragem sem reforma",
        "asset_profile": "compra abaixo do comprador ja mapeado ou de comparaveis liquidos",
        "renovation_profile": "sem reforma",
        "target_discount_pct": 18,
        "target_roi_pct": 15,
    },
    {
        "strategy_id": "house_flipping_leve",
        "label": "House flipping leve",
        "asset_profile": "planta pequena/media com liquidez e reforma controlada",
        "renovation_profile": "leve",
        "target_discount_pct": 15,
        "target_roi_pct": 20,
    },
    {
        "strategy_id": "house_flipping_pesada",
        "label": "House flipping reforma pesada",
        "asset_profile": "unidade muito descontada com margem para obra, prazo e reserva",
        "renovation_profile": "pesada",
        "target_discount_pct": 35,
        "target_roi_pct": 30,
    },
    {
        "strategy_id": "renda_plano_b",
        "label": "Renda / Plano B",
        "asset_profile": "unidade que pode carregar aluguel se a revenda atrasar",
        "renovation_profile": "maquiagem ou leve",
        "target_discount_pct": 10,
        "target_roi_pct": 14,
    },
    {
        "strategy_id": "condominio_antigo_requalificacao",
        "label": "Condominio antigo em requalificacao",
        "asset_profile": (
            "unidade em predio antigo com fachada, portaria ou areas comuns reformadas"
        ),
        "renovation_profile": "obra interna seletiva; condominio ja melhora percepcao externa",
        "target_discount_pct": 10,
        "target_roi_pct": 18,
    },
    {
        "strategy_id": "lancamentos_ciclo_entrega",
        "label": "Lancamentos / ciclo de entrega",
        "asset_profile": (
            "unidade em incorporadora ou estoque novo com prazo, entrega e distrato claros"
        ),
        "renovation_profile": "sem reforma; foco em preco, prazo e risco de entrega",
        "target_discount_pct": 8,
        "target_roi_pct": 12,
    },
]


TERRITORY_BLUEPRINTS: list[dict[str, object]] = [
    {
        "territory_id": "centro_republica_bela_vista",
        "label": "Centro / Republica / Bela Vista",
        "neighborhoods": ["Republica", "Centro", "Bela Vista", "Consolacao"],
        "price_band_brl": {"min": 180000, "max": 650000},
        "why": (
            "estoque antigo, transporte, retrofit e diferenca grande entre predios bons "
            "e cansados"
        ),
    },
    {
        "territory_id": "pinheiros_higienopolis_consolacao",
        "label": "Pinheiros / Higienopolis / Consolacao",
        "neighborhoods": ["Pinheiros", "Higienopolis", "Consolacao", "Perdizes"],
        "price_band_brl": {"min": 380000, "max": 1200000},
        "why": "liquidez alta e muitos predios antigos com valor destravado por modernizacao",
    },
    {
        "territory_id": "butanta_usp",
        "label": "Butanta / USP",
        "neighborhoods": ["Butanta", "Rio Pequeno", "Vila Indiana", "Jaguaré"],
        "price_band_brl": {"min": 240000, "max": 650000},
        "why": "demanda recorrente de estudantes, professores e renda de aluguel",
    },
    {
        "territory_id": "bras_belem_tatuape",
        "label": "Bras / Belem / Tatuape",
        "neighborhoods": ["Bras", "Belem", "Tatuape", "Mooca"],
        "price_band_brl": {"min": 180000, "max": 650000},
        "why": "mistura de renda, mobilidade e predios antigos perto de eixos de transporte",
    },
    {
        "territory_id": "agua_funda_jabaquara_saude",
        "label": "Agua Funda / Jabaquara / Saude",
        "neighborhoods": ["Agua Funda", "Jabaquara", "Saude", "Vila Mariana"],
        "price_band_brl": {"min": 180000, "max": 750000},
        "why": "casos reais ja mapeados e demanda por unidades compactas reformadas",
    },
    {
        "territory_id": "zona_leste_preco_baixo",
        "label": "Zona Leste preco baixo",
        "neighborhoods": ["Colonia", "Sao Miguel Paulista", "Artur Alvim", "Itaquera"],
        "price_band_brl": {"min": 110000, "max": 320000},
        "why": "ticket menor para aprendizado, mas exige disciplina de liquidez e documentos",
    },
    {
        "territory_id": "cantareira_recanto_verde",
        "label": "Cantareira / Jardim Recanto Verde",
        "neighborhoods": ["Jardim Recanto Verde", "Tremembe", "Cantareira"],
        "price_band_brl": {"min": 100000, "max": 280000},
        "why": "pipeline Caixa ja observado e forte dependencia de ocupacao, debitos e visita",
    },
    {
        "territory_id": "vila_mariana_aclimacao_ana_rosa",
        "label": "Vila Mariana / Aclimacao / Ana Rosa",
        "neighborhoods": ["Vila Mariana", "Aclimacao", "Ana Rosa", "Paraiso"],
        "price_band_brl": {"min": 420000, "max": 1350000},
        "why": "liquidez recorrente, metro, universidades e estoque antigo com reforma valorizavel",
    },
    {
        "territory_id": "moema_campo_belo_brooklin",
        "label": "Moema / Campo Belo / Brooklin",
        "neighborhoods": ["Moema", "Campo Belo", "Brooklin", "Vila Olimpia"],
        "price_band_brl": {"min": 480000, "max": 1800000},
        "why": (
            "demanda forte, aluguel comparavel abundante e oportunidade em planta "
            "antiga ou estoque novo"
        ),
    },
    {
        "territory_id": "santana_tucuruvi_zona_norte",
        "label": "Santana / Tucuruvi / Zona Norte",
        "neighborhoods": ["Santana", "Tucuruvi", "Parada Inglesa", "Mandaqui"],
        "price_band_brl": {"min": 230000, "max": 760000},
        "why": "eixo de metro, ticket intermediario e predios antigos com espaco para modernizacao",
    },
    {
        "territory_id": "santo_amaro_chacara_santo_antonio",
        "label": "Santo Amaro / Chacara Santo Antonio",
        "neighborhoods": ["Santo Amaro", "Chacara Santo Antonio", "Socorro", "Granja Julieta"],
        "price_band_brl": {"min": 250000, "max": 950000},
        "why": "mistura de renda, trabalho, metro/trem e estoque com precos muito dispersos",
    },
    {
        "territory_id": "osasco_barueri_eixo_oeste",
        "label": "Osasco / Barueri / Eixo Oeste",
        "neighborhoods": ["Osasco", "Presidente Altino", "Alphaville", "Barueri"],
        "price_band_brl": {"min": 220000, "max": 1100000},
        "why": "alternativa metropolitana com emprego, renda e comparaveis para plano B de aluguel",
    },
]


CONDOMINIUM_REQUALIFICATION_SOURCES: list[dict[str, object]] = [
    {
        "signal_id": "cond_edif_lotus_bela_vista",
        "title": "Cond Edif Lotus - Bela Vista",
        "territory_id": "centro_republica_bela_vista",
        "strategy_id": "condominio_antigo_requalificacao",
        "source_name": "Lello Imoveis",
        "source_url": "https://www.lelloimoveis.com.br/condominio/41891/cond_edif_lotus-bela_vista-sao_paulo/",
        "source_summary": "Pagina de condominio descreve predio com fachada reformada.",
    },
    {
        "signal_id": "condominio_sao_nicolau_republica",
        "title": "Condominio Sao Nicolau - Republica",
        "territory_id": "centro_republica_bela_vista",
        "strategy_id": "condominio_antigo_requalificacao",
        "source_name": "Direcional Condominios",
        "source_url": "https://www.direcionalcondominios.com.br/condominio-sao-nicolau-retrofit-valorizacao-imobiliaria/",
        "source_summary": "Materia descreve retrofit, modernizacao e recuperacao estrutural.",
    },
    {
        "signal_id": "edificio_acapulco_pinheiros",
        "title": "Edificio Acapulco - Pinheiros",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "strategy_id": "condominio_antigo_requalificacao",
        "source_name": "Sindico Certo",
        "source_url": "https://www.sindicocerto.com.br/materias_retrofit_condominio_de_cara_nova_para_um_uso_contemporaneo.htm",
        "source_summary": "Materia descreve retrofit, fachada e frente do edificio.",
    },
    {
        "signal_id": "requalifica_centro_pipeline",
        "title": "Pipeline Requalifica Centro",
        "territory_id": "centro_republica_bela_vista",
        "strategy_id": "condominio_antigo_requalificacao",
        "source_name": "Prefeitura de Sao Paulo / SMUL",
        "source_url": "https://prefeitura.sp.gov.br/web/licenciamento/w/programas-municipais-consolidam-2025-como-ano-decisivo-para-o-retrofit-no-centro-de-s%C3%A3o-paulo",
        "source_summary": "Programa publico indica volume crescente de retrofit no centro.",
    },
]


STRATEGY_CANDIDATE_SOURCES: list[dict[str, object]] = [
    {
        "source_id": "caixa_tamareiras_vila_carmosina",
        "title": "CAIXA - Tamareiras / Vila Carmosina",
        "strategy_id": "leilao_venda_online",
        "territory_id": "zona_leste_preco_baixo",
        "source_name": "CAIXA Imoveis",
        "source_url": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnOrigem=index&hdnimovel=8787711295569",
        "source_summary": (
            "Pagina de detalhe da Caixa usada como garimpo de venda online/leilao; "
            "confirmar disponibilidade, edital e ocupacao no dia."
        ),
        "candidate_angle": (
            "Testar desconto real contra avaliacao, debitos, ocupacao e liquidez "
            "na Zona Leste."
        ),
    },
    {
        "source_id": "caixa_residencial_nova_itaquera",
        "title": "CAIXA - Residencial Nova Itaquera",
        "strategy_id": "leilao_venda_online",
        "territory_id": "zona_leste_preco_baixo",
        "source_name": "CAIXA Imoveis",
        "source_url": "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnOrigem=index&hdnimovel=8555535748445",
        "source_summary": (
            "Fonte de leilao Caixa para triagem de apartamento compacto em Sao Paulo."
        ),
        "candidate_angle": (
            "Comparar lance minimo, avaliacao, visita, ocupacao e custo juridico "
            "antes de qualquer proposta."
        ),
    },
    {
        "source_id": "vivareal_venda_sao_paulo",
        "title": "VivaReal - apartamentos a venda em Sao Paulo",
        "strategy_id": "venda_direta_negociacao",
        "territory_id": "vila_mariana_aclimacao_ana_rosa",
        "source_name": "VivaReal",
        "source_url": "https://www.vivareal.com.br/venda/sp/sao-paulo/apartamento_residencial/",
        "source_summary": (
            "Pagina de busca ampla para venda direta; serve para garimpar tempo "
            "de anuncio e dispersao de preco."
        ),
        "candidate_angle": (
            "Filtrar unidades antigas com preco fora do padrao e margem para "
            "negociacao documentada."
        ),
    },
    {
        "source_id": "quintoandar_compra_sao_paulo",
        "title": "QuintoAndar - apartamentos a venda em Sao Paulo",
        "strategy_id": "venda_direta_negociacao",
        "territory_id": "moema_campo_belo_brooklin",
        "source_name": "QuintoAndar",
        "source_url": "https://www.quintoandar.com.br/comprar/imovel/sao-paulo-sao-paulo-sp-brasil/apartamento",
        "source_summary": (
            "Fonte de compra direta para comparar preco pedido, liquidez e padrao "
            "de acabamento."
        ),
        "candidate_angle": (
            "Buscar vendedor flexivel, preco acima do tempo de mercado e teto de "
            "compra bem definido."
        ),
    },
    {
        "source_id": "vivareal_mapa_arbitragem_sp",
        "title": "VivaReal - mapa de assimetria SP",
        "strategy_id": "arbitragem_sem_reforma",
        "territory_id": "santo_amaro_chacara_santo_antonio",
        "source_name": "VivaReal",
        "source_url": "https://www.vivareal.com.br/venda/sp/sao-paulo/apartamento_residencial/",
        "source_summary": (
            "Busca ampla para comparar preco por bairro, metragem e liquidez sem "
            "depender de obra."
        ),
        "candidate_angle": (
            "Separar outliers de preco que ja estejam vendaveis, com comparaveis "
            "vendidos no mesmo raio."
        ),
    },
    {
        "source_id": "imovelweb_venda_sao_paulo",
        "title": "Imovelweb - apartamentos a venda em Sao Paulo",
        "strategy_id": "arbitragem_sem_reforma",
        "territory_id": "osasco_barueri_eixo_oeste",
        "source_name": "Imovelweb",
        "source_url": "https://www.imovelweb.com.br/apartamentos-venda-sao-paulo-sp.html/",
        "source_summary": (
            "Fonte de anuncios para comparar oferta, preco pedido e diferenca entre "
            "bairros proximos."
        ),
        "candidate_angle": (
            "Procurar assimetria de preco sem obra e validar saida com comparaveis "
            "independentes."
        ),
    },
    {
        "source_id": "imovelweb_bela_vista_para_reformar",
        "title": "Imovelweb - Bela Vista para reformar",
        "strategy_id": "house_flipping_leve",
        "territory_id": "centro_republica_bela_vista",
        "source_name": "Imovelweb",
        "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-com-2-dormitorios-a-venda-88-m-por-r%24-3002615235.html",
        "source_summary": (
            "Anuncio observado com linguagem de oportunidade para reformar; validar "
            "estado real e preco vigente."
        ),
        "candidate_angle": (
            "Avaliar reforma estetica, custo controlado e revenda para comprador "
            "final no eixo central."
        ),
    },
    {
        "source_id": "imovelweb_saude_para_reformar",
        "title": "Imovelweb - Saude para reformar",
        "strategy_id": "house_flipping_leve",
        "territory_id": "agua_funda_jabaquara_saude",
        "source_name": "Imovelweb",
        "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-com-2-quartos-a-venda-em-saude-sp-3017055514.html",
        "source_summary": (
            "Anuncio de apartamento para reformar na Saude; deve ser tratado como "
            "triagem, nao tese pronta."
        ),
        "candidate_angle": (
            "Testar reforma leve proxima ao metro contra teto de compra e "
            "comparaveis reformados."
        ),
    },
    {
        "source_id": "imovelweb_jardim_america_reforma_pesada",
        "title": "Imovelweb - Jardim America para reforma",
        "strategy_id": "house_flipping_pesada",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "source_name": "Imovelweb",
        "source_url": "https://www.imovelweb.com.br/propriedades/apartamento-para-reformar-de-130m-3-suites-e-2-3005734646.html",
        "source_summary": (
            "Anuncio observado para reforma de unidade grande; exige orcamento, "
            "prazo e reserva maiores."
        ),
        "candidate_angle": (
            "So estudar se desconto pagar obra, tempo de carregamento e risco de "
            "execucao."
        ),
    },
    {
        "source_id": "imovelweb_higienopolis_reforma_pesada",
        "title": "Imovelweb - Higienopolis predio antigo",
        "strategy_id": "house_flipping_pesada",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "source_name": "Imovelweb",
        "source_url": "https://www.imovelweb.com.br/propriedades/sao-3-belos-dormitorios-tres-banheiros-sala-ampla-3019752321.html",
        "source_summary": (
            "Fonte listada para unidade ampla em predio antigo; validar se a reforma "
            "e estrutural ou estetica."
        ),
        "candidate_angle": (
            "Usar como caso de estudo de margem alta com risco alto e prazo de "
            "saida mais longo."
        ),
    },
    {
        "source_id": "quintoandar_aluguel_sao_paulo",
        "title": "QuintoAndar - aluguel de apartamentos em Sao Paulo",
        "strategy_id": "renda_plano_b",
        "territory_id": "santo_amaro_chacara_santo_antonio",
        "source_name": "QuintoAndar",
        "source_url": "https://www.quintoandar.com.br/alugar/imovel/sao-paulo-sp-brasil/apartamento",
        "source_summary": (
            "Busca de aluguel para estimar carregamento, liquidez e plano B por bairro."
        ),
        "candidate_angle": (
            "Cruzar aluguel pedido com custo total de carregamento antes de aceitar "
            "a tese de revenda."
        ),
    },
    {
        "source_id": "fipezap_locacao_mar_2026",
        "title": "FIPEZAP - locacao residencial mar/2026",
        "strategy_id": "renda_plano_b",
        "territory_id": "moema_campo_belo_brooklin",
        "source_name": "FIPEZAP",
        "source_url": "https://downloads.fipe.org.br/indices/fipezap/fipezap-202603-residencial-locacao.pdf",
        "source_summary": (
            "Relatorio de locacao residencial para calibrar aluguel esperado e "
            "tendencia de mercado."
        ),
        "candidate_angle": (
            "Usar como referencia macro; o aluguel da unidade ainda precisa de "
            "comparaveis reais."
        ),
    },
    {
        "source_id": "lello_cond_edif_lotus",
        "title": "Lello - Cond Edif Lotus / Bela Vista",
        "strategy_id": "condominio_antigo_requalificacao",
        "territory_id": "centro_republica_bela_vista",
        "source_name": "Lello Imoveis",
        "source_url": "https://www.lelloimoveis.com.br/condominio/41891/cond_edif_lotus-bela_vista-sao_paulo/",
        "source_summary": (
            "Pagina de condominio usada como fonte de sinal de predio em "
            "requalificacao."
        ),
        "candidate_angle": (
            "Buscar unidade disponivel no edificio e comparar contra predios sem "
            "melhoria no entorno."
        ),
    },
    {
        "source_id": "prefeitura_requalifica_centro",
        "title": "Prefeitura SP - pipeline Requalifica Centro",
        "strategy_id": "condominio_antigo_requalificacao",
        "territory_id": "centro_republica_bela_vista",
        "source_name": "Prefeitura de Sao Paulo / SMUL",
        "source_url": "https://prefeitura.sp.gov.br/web/licenciamento/w/programas-municipais-consolidam-2025-como-ano-decisivo-para-o-retrofit-no-centro-de-s%C3%A3o-paulo",
        "source_summary": (
            "Fonte institucional sobre retrofit no centro; sinal territorial, nao "
            "unidade compravel."
        ),
        "candidate_angle": (
            "Mapear predios do entorno e procurar assimetria de preco antes da "
            "melhora virar consenso."
        ),
    },
    {
        "source_id": "vivareal_wish_675_lancamento",
        "title": "VivaReal - WISH 675 / Vila Monte Alegre",
        "strategy_id": "lancamentos_ciclo_entrega",
        "territory_id": "agua_funda_jabaquara_saude",
        "source_name": "VivaReal Lancamentos",
        "source_url": "https://www.vivareal.com.br/imoveis-lancamentos/wish-675-id-2876400406/",
        "source_summary": (
            "Pagina de lancamento usada para acompanhar preco, entrega, estoque e "
            "risco de prazo."
        ),
        "candidate_angle": (
            "Validar se preco de entrada, prazo de entrega e estoque competem com "
            "usado reformado."
        ),
    },
    {
        "source_id": "vivareal_oriz_campo_belo_lancamento",
        "title": "VivaReal - Oriz / Campo Belo",
        "strategy_id": "lancamentos_ciclo_entrega",
        "territory_id": "moema_campo_belo_brooklin",
        "source_name": "VivaReal Lancamentos",
        "source_url": "https://www.vivareal.com.br/imoveis-lancamentos/oriz-by-plano-e-plano-apartamentos-id-2854210541/",
        "source_summary": (
            "Pagina de empreendimento para estudar ciclo de entrega, unidade compacta "
            "e concorrencia local."
        ),
        "candidate_angle": (
            "Comparar preco por metro, prazo e estoque novo contra alternativas "
            "prontas no bairro."
        ),
    },
]


BASE_DILIGENCE_CHECKLIST = [
    "confirmar unidade disponivel no edificio",
    "confirmar ocupacao",
    "buscar matricula atualizada",
    "confirmar divida de condominio e IPTU",
    "levantar 3 comparaveis vendidos no mesmo raio",
    "levantar 3 comparaveis de aluguel para plano B",
]


CONDOMINIUM_DILIGENCE_CHECKLIST = [
    "confirmar unidade disponivel no edificio",
    "confirmar ata/escopo da obra condominial",
    "confirmar se a obra ja foi paga ou se ha rateio extraordinario pendente",
    "comparar preco pedido contra unidades sem retrofit no mesmo raio",
    "validar impacto da fachada/areas comuns na liquidez e no aluguel",
]


LAUNCH_DILIGENCE_CHECKLIST = [
    "confirmar incorporadora, SPE e memorial de incorporacao",
    "validar prazo de entrega, atraso historico e clausulas de distrato",
    "comparar preco por metro com usado reformado no mesmo raio",
    "confirmar estoque, fluxo de pagamento e custo de carregamento",
    "testar plano B de aluguel ou revenda se a entrega atrasar",
]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _brief_id(territory_id: str, strategy_id: str) -> str:
    return f"IM-BUSCA-{territory_id}-{strategy_id}"


def _source_candidate_id(source_id: object) -> str:
    return f"IM-FONTE-{source_id}"


def _search_queries(territory: dict[str, object], strategy: dict[str, object]) -> list[str]:
    neighborhoods = " OR ".join(str(item) for item in territory["neighborhoods"])
    strategy_label = str(strategy["label"])
    return [
        f'"{neighborhoods}" apartamento venda "{strategy_label}" Sao Paulo',
        (
            f'"{neighborhoods}" "condominio antigo" '
            '"fachada reformada" apartamento Sao Paulo'
        ),
        f'"{neighborhoods}" apartamento "area comum reformada" Sao Paulo',
    ]


def _diligence_checklist_for_strategy(strategy_id: str) -> list[str]:
    checklist = list(BASE_DILIGENCE_CHECKLIST)
    if strategy_id == "condominio_antigo_requalificacao":
        checklist = list(dict.fromkeys(CONDOMINIUM_DILIGENCE_CHECKLIST + checklist))
    if strategy_id == "lancamentos_ciclo_entrega":
        checklist = list(dict.fromkeys(LAUNCH_DILIGENCE_CHECKLIST + checklist))
    return checklist


def generate_strategy_territory_candidate_briefs() -> list[dict[str, object]]:
    briefs: list[dict[str, object]] = []
    for territory in TERRITORY_BLUEPRINTS:
        for strategy in STRATEGY_BLUEPRINTS:
            territory_id = str(territory["territory_id"])
            strategy_id = str(strategy["strategy_id"])
            requires_condominium_signal = strategy_id == "condominio_antigo_requalificacao"
            checklist = _diligence_checklist_for_strategy(strategy_id)
            briefs.append(
                {
                    "brief_id": _brief_id(territory_id, strategy_id),
                    "brief_type": "strategy_territory_search",
                    "trust_level": "hypothesis",
                    "territory_id": territory_id,
                    "territory_label": territory["label"],
                    "neighborhoods": territory["neighborhoods"],
                    "strategy_id": strategy_id,
                    "strategy_label": strategy["label"],
                    "title": f"BUSCA - {strategy['label']} - {territory['label']}",
                    "asset_profile": strategy["asset_profile"],
                    "territory_thesis": territory["why"],
                    "price_band_brl": territory["price_band_brl"],
                    "target_discount_pct": strategy["target_discount_pct"],
                    "target_roi_pct": strategy["target_roi_pct"],
                    "renovation_profile": strategy["renovation_profile"],
                    "condominium_signal": {
                        "required": requires_condominium_signal,
                        "evidence_status": "to_verify",
                        "accepted_evidence": [
                            "fachada reformada",
                            "areas comuns reformadas",
                            "retrofit estrutural",
                            "portaria/elevadores modernizados",
                            "ata ou comunicacao formal da obra",
                        ],
                    },
                    "next_search_queries": _search_queries(territory, strategy),
                    "diligence_checklist": checklist,
                    "decision_rule": (
                        "Nao virar tese de compra ate existir unidade, preco pedido, "
                        "comparaveis e pendencias P0 fechadas."
                    ),
                }
            )
    return briefs


def generate_condominium_requalification_watchlist() -> list[dict[str, object]]:
    territories = {str(item["territory_id"]): item for item in TERRITORY_BLUEPRINTS}
    strategies = {str(item["strategy_id"]): item for item in STRATEGY_BLUEPRINTS}
    watchlist: list[dict[str, object]] = []
    for source in CONDOMINIUM_REQUALIFICATION_SOURCES:
        territory = territories[str(source["territory_id"])]
        strategy = strategies[str(source["strategy_id"])]
        watchlist.append(
            {
                "brief_id": f"IM-SINAL-{source['signal_id']}",
                "brief_type": "condominium_requalification_signal",
                "trust_level": "source_confirmed",
                "territory_id": source["territory_id"],
                "territory_label": territory["label"],
                "strategy_id": source["strategy_id"],
                "strategy_label": strategy["label"],
                "title": source["title"],
                "source_name": source["source_name"],
                "source_url": source["source_url"],
                "source_summary": source["source_summary"],
                "candidate_angle": (
                    "Buscar unidade disponivel com desconto dentro de predio cuja "
                    "percepcao externa esteja melhorando por obra condominial."
                ),
                "diligence_checklist": list(CONDOMINIUM_DILIGENCE_CHECKLIST),
                "decision_rule": (
                    "Fonte confirma o sinal do predio/territorio, nao uma compra. "
                    "A unidade ainda precisa ser encontrada e precificada."
                ),
            }
        )
    return watchlist


def generate_strategy_candidate_watchlist() -> list[dict[str, object]]:
    territories = {str(item["territory_id"]): item for item in TERRITORY_BLUEPRINTS}
    strategies = {str(item["strategy_id"]): item for item in STRATEGY_BLUEPRINTS}
    watchlist: list[dict[str, object]] = []
    for source in STRATEGY_CANDIDATE_SOURCES:
        strategy_id = str(source["strategy_id"])
        territory_id = str(source["territory_id"])
        strategy = strategies[strategy_id]
        territory = territories[territory_id]
        watchlist.append(
            {
                "brief_id": _source_candidate_id(source["source_id"]),
                "brief_type": "strategy_source_candidate",
                "trust_level": "source_listed",
                "source_status": "source_listed_pending_live_verification",
                "territory_id": territory_id,
                "territory_label": territory["label"],
                "neighborhoods": territory["neighborhoods"],
                "strategy_id": strategy_id,
                "strategy_label": strategy["label"],
                "title": source["title"],
                "source_name": source["source_name"],
                "source_url": source["source_url"],
                "source_summary": source["source_summary"],
                "candidate_angle": source["candidate_angle"],
                "asset_profile": strategy["asset_profile"],
                "territory_thesis": territory["why"],
                "price_band_brl": territory["price_band_brl"],
                "target_discount_pct": strategy["target_discount_pct"],
                "target_roi_pct": strategy["target_roi_pct"],
                "renovation_profile": strategy["renovation_profile"],
                "next_search_queries": _search_queries(territory, strategy),
                "diligence_checklist": _diligence_checklist_for_strategy(strategy_id),
                "decision_rule": (
                    "Nao vira tese de compra ate existir unidade, preco pedido, "
                    "comparaveis, disponibilidade vigente e pendencias P0 fechadas."
                ),
            }
        )
    return watchlist


def strategy_territory_report() -> dict[str, Any]:
    matrix = generate_strategy_territory_candidate_briefs()
    strategy_watchlist = generate_strategy_candidate_watchlist()
    watchlist = generate_condominium_requalification_watchlist()
    return {
        "generated_at": _utc_now(),
        "summary": {
            "strategy_count": len(STRATEGY_BLUEPRINTS),
            "territory_count": len(TERRITORY_BLUEPRINTS),
            "matrix_brief_count": len(matrix),
            "source_candidate_count": len(strategy_watchlist),
            "source_confirmed_requalification_count": len(watchlist),
            "actionability": (
                "Briefs sao hipoteses de busca. Fontes listadas e sinais confirmados "
                "ainda exigem unidade, preco, comparaveis, disponibilidade vigente e "
                "diligencia P0."
            ),
        },
        "strategies": STRATEGY_BLUEPRINTS,
        "territories": TERRITORY_BLUEPRINTS,
        "matrix_briefs": matrix,
        "strategy_candidate_watchlist": strategy_watchlist,
        "condominium_requalification_watchlist": watchlist,
    }


def report_to_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Radar imobiliario - estrategias por territorio",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- estrategias: `{summary['strategy_count']}`",
        f"- territorios: `{summary['territory_count']}`",
        f"- briefs de busca: `{summary['matrix_brief_count']}`",
        f"- fontes candidatas por estrategia: `{summary['source_candidate_count']}`",
        (
            "- sinais confirmados de condominio em requalificacao: "
            f"`{summary['source_confirmed_requalification_count']}`"
        ),
        "",
        "## Regra de confianca",
        "",
        str(summary["actionability"]),
        "",
        "## Fontes candidatas por estrategia",
    ]
    for item in report["strategy_candidate_watchlist"]:
        lines.extend(
            [
                "",
                f"### {item['title']}",
                f"- territorio: {item['territory_label']}",
                f"- estrategia: {item['strategy_label']}",
                f"- fonte: {item['source_name']}",
                f"- url: {item['source_url']}",
                f"- leitura: {item['source_summary']}",
                f"- angulo: {item['candidate_angle']}",
                f"- regra: {item['decision_rule']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Sinais confirmados de condominio",
        ]
    )
    for item in report["condominium_requalification_watchlist"]:
        lines.extend(
            [
                "",
                f"### {item['title']}",
                f"- territorio: {item['territory_label']}",
                f"- estrategia: {item['strategy_label']}",
                f"- fonte: {item['source_name']}",
                f"- url: {item['source_url']}",
                f"- leitura: {item['source_summary']}",
                f"- regra: {item['decision_rule']}",
            ]
        )
    lines.extend(["", "## Matriz de busca"])
    for item in report["matrix_briefs"]:
        lines.extend(
            [
                "",
                f"- `{item['brief_id']}` | {item['title']}",
                (
                    f"  - faixa alvo: R$ {item['price_band_brl']['min']:,} "
                    f"a R$ {item['price_band_brl']['max']:,}"
                ),
                f"  - tese territorial: {item['territory_thesis']}",
                f"  - regra: {item['decision_rule']}",
            ]
        )
    return "\n".join(lines)


def write_strategy_territory_report(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = strategy_territory_report()
    json_path = output_dir / "real_estate_strategy_territory_candidates_latest.json"
    md_path = output_dir / "real_estate_strategy_territory_candidates_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    return {"json_file": str(json_path), "markdown_file": str(md_path)}

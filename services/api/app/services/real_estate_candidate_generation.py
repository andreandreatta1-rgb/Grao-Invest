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


AUCTIONEER_SCOPE_CITIES = ["Sao Paulo", "Campinas"]
AUCTIONEER_JUCESP_SOURCE_URL = "https://www.institucional.jucesp.sp.gov.br/consultaLeilao.html"


AUCTIONEER_DIRECTORY_SOURCES: list[dict[str, object]] = [
    {
        "id": "auctioneer-jucesp-sp-campinas",
        "uf": "SP",
        "source_name": "JUCESP - Consulta de Leiloeiros e Tradutores",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "contact_path": (
            "Consulta oficial com filtro por municipio, situacao, matricula, telefone, "
            "e-mail e site publicado."
        ),
        "contact_strategy": (
            "Filtrar leiloeiros com situacao Atuante Regular em Sao Paulo capital e "
            "Campinas; registrar contato publico antes de promover lote para candidato."
        ),
        "visibility_tier": "cauda_longa",
        "relationship_stage": "coletar_contato",
        "scope_cities": AUCTIONEER_SCOPE_CITIES,
        "quality_filter": [
            "situacao Atuante Regular",
            "matricula informada pela JUCESP",
            "telefone/e-mail publicados pela Junta",
            "recorte inicial: Sao Paulo capital e Campinas",
        ],
    },
]


AUCTIONEER_OFFICIAL_CONTACTS: list[dict[str, object]] = [
    {
        "id": "auctioneer-sp-547",
        "name": "CARLOS CHUI",
        "registration": "547",
        "city": "Sao Paulo",
        "neighborhood": "Ipiranga",
        "phones": ["(11)2272-7170", "(11)97014-2280"],
        "email": "contato@arremataronline.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": (
            "Contato com dominio de leilao e multiplos telefones; bom canal, mas "
            "provavelmente mais disputado."
        ),
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Entrar no mailing e acompanhar pauta imobiliaria filtrada por SP.",
    },
    {
        "id": "auctioneer-sp-550",
        "name": "GILBERTO FORTES DO AMARAL FILHO",
        "registration": "550",
        "city": "Sao Paulo",
        "neighborhood": "",
        "phones": ["(11)3885-0387", "(11)99931-7508"],
        "email": "gilamaral@uol.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "E-mail pessoal e sem site publicado sugerem menor exposicao digital.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Contato direto para entender calendario e lotes imobiliarios.",
    },
    {
        "id": "auctioneer-sp-570",
        "name": "MIGUEL NIEMOJ",
        "registration": "570",
        "city": "Sao Paulo",
        "neighborhood": "Vila Prudente",
        "phones": ["(11)2341-2849", "(11)98114-8488"],
        "email": "miguelniemoj@gmail.com",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "E-mail gratuito e bairro definido favorecem abordagem regional.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Validar se possui agenda imobiliaria na zona leste/sudeste.",
    },
    {
        "id": "auctioneer-sp-581",
        "name": "FLAVIO CUNHA SODRE SANTORO",
        "registration": "581",
        "city": "Sao Paulo",
        "neighborhood": "Vila Romana",
        "phones": ["(11)2464-6465"],
        "email": "airton.silva@sodresantoro.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": "Dominio de marca reconhecivel indica operador mais visivel.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Acompanhar editais, mas tratar como canal de maior concorrencia.",
    },
    {
        "id": "auctioneer-sp-587",
        "name": "DOUGLAS JOSE FIDALGO",
        "registration": "587",
        "city": "Sao Paulo",
        "neighborhood": "Vila Euthalia",
        "phones": ["(11)2653-0553", "(11)99990-7776"],
        "email": "douglas@fidalgoleiloes.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": "Dominio proprio de leiloes e varios canais de contato.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Monitorar lotes imobiliarios e medir concorrencia por edital.",
    },
    {
        "id": "auctioneer-sp-593",
        "name": "REINALDO MARQUES DA SILVA",
        "registration": "593",
        "city": "Sao Paulo",
        "neighborhood": "Cidade Sao Francisco",
        "phones": ["(11)94762-4447"],
        "email": "artedosmarques@gmail.com",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "Canal simples, e-mail gratuito e apenas um telefone publicado.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Checar se recebe pauta de imoveis de menor ticket.",
    },
    {
        "id": "auctioneer-sp-599",
        "name": "VIVIAN CRISTINE DIANESE PEREZ",
        "registration": "599",
        "city": "Sao Paulo",
        "neighborhood": "Perdizes",
        "phones": ["(11)3862-1888", "(11)9998-3506"],
        "email": "vcdperez@gmail.com",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "Contato publico simples sem site publicado na fonte oficial.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Pedir mailing institucional e historico de lotes residenciais.",
    },
    {
        "id": "auctioneer-sp-602",
        "name": "CEZAR AUGUSTO BADOLATO SILVA",
        "registration": "602",
        "city": "Sao Paulo",
        "neighborhood": "Cerqueira Cesar",
        "phones": ["(11)94898-9425"],
        "email": "cezar.badolatooficial@gmail.com",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "E-mail gratuito e contato direto favorecem teste de relacionamento.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Validar se atua em imoveis compactos no eixo central/oeste.",
    },
    {
        "id": "auctioneer-campinas-715",
        "name": "ANGELA PECINI SILVEIRA",
        "registration": "715",
        "city": "Campinas",
        "neighborhood": "Vila Brandina",
        "phones": ["(19)3794-2044", "(11)97577-0485"],
        "email": "angela@pecinileiloes.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": "Dominio proprio de leiloes indica maior presenca comercial.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Monitorar Campinas e entorno; comparar taxa de concorrencia por lote.",
    },
    {
        "id": "auctioneer-campinas-716",
        "name": "ANA CLARA DE MELLO E SILVA",
        "registration": "716",
        "city": "Campinas",
        "neighborhood": "Centro",
        "phones": ["(19)3849-7675", "(19)99695-3050"],
        "email": "anaclarademello@bol.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "E-mail gratuito e recorte regional sugerem menor disputa inicial.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Contato direto para pauta de imoveis em Campinas.",
    },
    {
        "id": "auctioneer-campinas-838",
        "name": "CARLOS ALBERTO MADUREIRA DE OLIVEIRA",
        "registration": "838",
        "city": "Campinas",
        "neighborhood": "Jardim Proenca",
        "phones": ["(19)3323-2799", "(19)9127-2228"],
        "email": "",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "validar",
        "competition_reason": "Telefone publicado, mas sem e-mail/site na captura; exige validacao manual.",
        "relationship_stage": "validar_contato",
        "contact_strategy": "Telefonar apenas para confirmar canal oficial e pauta imobiliaria.",
    },
    {
        "id": "auctioneer-campinas-843",
        "name": "MARCELO EMIDIO FERREIRA PIEROBOM SILVEIRA",
        "registration": "843",
        "city": "Campinas",
        "neighborhood": "Centro",
        "phones": ["(19)3794-2030", "(19)98138-3065"],
        "email": "marcelo@jsilveira-advogados.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "Dominio juridico, nao marketplace de leiloes; pode ser canal menos obvio.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Validar se agenda inclui imoveis e se aceita mailing por e-mail.",
    },
    {
        "id": "auctioneer-campinas-849",
        "name": "DORCA PEREIRA DOS REIS",
        "registration": "849",
        "city": "Campinas",
        "neighborhood": "Jardim Guarani",
        "phones": ["(19)99605-0505"],
        "email": "atendimento@stiloleiloes.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": "E-mail de atendimento em dominio de leiloes indica estrutura comercial.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Entrar no mailing e marcar como canal com concorrencia moderada.",
    },
    {
        "id": "auctioneer-campinas-873",
        "name": "CARLOS DE JESUS RAMOS RIBEIRO",
        "registration": "873",
        "city": "Campinas",
        "neighborhood": "Taquaral",
        "phones": ["(19)3203-4409"],
        "email": "contato@rmcleiloes.com.br",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "estabelecido",
        "competition_reason": "Dominio proprio de leiloes sugere maior visibilidade no mercado.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Acompanhar Campinas e medir descontos efetivos antes de tese.",
    },
    {
        "id": "auctioneer-campinas-911",
        "name": "LEONETE MORAES AGUIAR",
        "registration": "911",
        "city": "Campinas",
        "neighborhood": "Taquaral",
        "phones": ["(17)99106-6422"],
        "email": "leoneteleiloeira@gmail.com",
        "website": "www.sumareleiloes.com.br",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "Site regional e contato pessoal indicam oportunidade de relacionamento.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Validar agenda Campinas/Sumare e lotes residenciais fora dos grandes portais.",
    },
    {
        "id": "auctioneer-campinas-986",
        "name": "MARCELO BRIDI",
        "registration": "986",
        "city": "Campinas",
        "neighborhood": "Jardim Flamboyant",
        "phones": ["(19)3367-2319", "(19)98354-9955"],
        "email": "meno26@hotmail.com",
        "website": "",
        "status": "Atuante Regular",
        "source_url": AUCTIONEER_JUCESP_SOURCE_URL,
        "competition_tier": "cauda_longa",
        "competition_reason": "E-mail pessoal e sem site publicado reduzem obviedade do canal.",
        "relationship_stage": "coletar_contato",
        "contact_strategy": "Contato exploratorio para entender pauta imobiliaria regional.",
    },
]


ACTIVE_AUCTION_PORTAL_SOURCES: list[dict[str, object]] = [
    {
        "id": "portal-leeilon-pinheiros",
        "portal": "Leeilon",
        "source_url": "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-a-venda-em-leilao/1066258",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "neighborhood": "Pinheiros",
        "example_asset": "Rua Joao Moura, 1362 - Apartamento 32",
        "source_role": "aggregator_clue",
        "observed_signal": "pagina indexada de apartamento em leilao no bairro-alvo",
        "next_search_queries": [
            'site:leeilon.com.br/imovel-em-leilao/SP/sao-paulo Pinheiros apartamento leilao',
            '"Pinheiros" "Leeilon" "Apartamento" "São Paulo"',
        ],
    },
    {
        "id": "portal-leeilon-hub-pinheiros",
        "portal": "Leeilon",
        "source_url": "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-n-2103-condominio-hub-pinheiros-r-dante-carraro-94-pinheiros-sao-paulo-sp/1176206",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "neighborhood": "Pinheiros",
        "example_asset": "Condominio Hub Pinheiros, Rua Dante Carraro, 94 - apto 2103",
        "source_role": "aggregator_clue",
        "observed_signal": "fonte lateral com identidade de condominio, unidade e endereco",
        "next_search_queries": [
            '"Condominio Hub Pinheiros" leilao',
            '"Rua Dante Carraro, 94" "apartamento 2103"',
        ],
    },
    {
        "id": "portal-leeilon-perdizes-turiassu",
        "portal": "Leeilon",
        "source_url": "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-r-turiassu-com-9080m-com-vaga-de-garagem-sao-paulosp/1207113",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "neighborhood": "Perdizes",
        "example_asset": "Rua Turiassu, 362 - apartamento 90,80m2",
        "source_role": "aggregator_clue",
        "observed_signal": "mesmo endereco de candidato ja conhecido reaparece como fonte lateral",
        "next_search_queries": [
            '"Rua Turiassu 362" leilao apartamento',
            'site:leeilon.com.br/imovel-em-leilao/SP/sao-paulo Perdizes Turiassu',
        ],
    },
    {
        "id": "portal-leeilon-perdizes-tucuna",
        "portal": "Leeilon",
        "source_url": "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apartamento-a-venda-em-leilao/952315",
        "territory_id": "pinheiros_higienopolis_consolacao",
        "neighborhood": "Perdizes",
        "example_asset": "Edificio Perdizes First Class, Rua Tucuna, 913 - apartamento 47",
        "source_role": "aggregator_clue",
        "observed_signal": "pagina lateral com edificio e unidade em bairro-alvo",
        "next_search_queries": [
            '"Rua Tucuna, 913" leilao apartamento',
            '"Perdizes First Class" leilao',
        ],
    },
    {
        "id": "portal-leilaoimovel-campo-belo-pascal",
        "portal": "Leilao Imovel",
        "source_url": "https://www.leilaoimovel.com.br/imovel/sp/sao-paulo/residencial-sao-paulo-sp-campo-belo-apartamento-com-34m-residenciais-cod-do-leilao-01492-lote-001-imovel-2607257",
        "territory_id": "moema_campo_belo_brooklin",
        "neighborhood": "Campo Belo",
        "example_asset": "Rua Pascal, 1777 - apto 125, Condominio Edificio Pascal",
        "source_role": "aggregator_clue",
        "observed_signal": "Leilao Imovel expõe endereco, area, vaga, ocupacao/desocupacao e debitos",
        "next_search_queries": [
            '"Rua Pascal, 1777" "Condominio Edificio Pascal"',
            'site:leilaoimovel.com.br/imovel/sp/sao-paulo Campo Belo apartamento leilao',
        ],
    },
    {
        "id": "portal-leeilon-jardins",
        "portal": "Leeilon",
        "source_url": "https://www.leeilon.com.br/imovel-em-leilao/SP/sao-paulo/apto-res-at-93m-jardinssp/1104836",
        "territory_id": "vila_mariana_aclimacao_ana_rosa",
        "neighborhood": "Jardim Paulista",
        "example_asset": "Apto residencial 93m2 - Jardins",
        "source_role": "aggregator_clue",
        "observed_signal": "bairro liquido adjacente aos alvos de alta renda",
        "next_search_queries": [
            'site:leeilon.com.br/imovel-em-leilao/SP/sao-paulo Jardins apartamento leilao',
            '"Jardim Paulista" "Leeilon" "apartamento"',
        ],
    },
    {
        "id": "portal-projud-campinas-savoy",
        "portal": "Projud Leiloes",
        "source_url": "https://www.projudleiloes.com.br/arquivos/Leiloes/Docs/50d8735c-bf55-4b44-bdfb-255ab7d0ab5d.pdf",
        "territory_id": "campinas-cambui-taquaral",
        "neighborhood": "Campinas",
        "example_asset": "Apartamento 32, Condominio Edificio Savoy, Campinas",
        "source_role": "primary_legal",
        "observed_signal": "PDF de edital judicial com leiloeiro e bem descrito",
        "next_search_queries": [
            'site:projudleiloes.com.br Campinas apartamento leilao edital',
            '"Condominio Edificio Savoy" "Campinas" leilao',
        ],
    },
    {
        "id": "portal-silveira-campinas",
        "portal": "Silveira Leiloes",
        "source_url": "https://www.silveiraleiloes.com.br/previewleilao/207/170abaa8-bac8-4783-9527-7133c124d14e.pdf",
        "territory_id": "campinas-cambui-taquaral",
        "neighborhood": "Campinas",
        "example_asset": "Apartamento em Campinas - edital extrajudicial",
        "source_role": "primary_legal",
        "observed_signal": "edital PDF de imovel em Campinas, util para monitoramento regional",
        "next_search_queries": [
            'site:silveiraleiloes.com.br Campinas apartamento leilao edital',
            '"Silveira Leiloes" "Campinas" "Apartamento"',
        ],
    },
]


AUCTIONEER_OUTREACH_SENT_AT = "2026-05-19"
AUCTIONEER_OUTREACH_NEXT_FOLLOW_UP_AT = "2026-05-22"
AUCTIONEER_OUTREACH_SENT_IDS = {
    "auctioneer-sp-599",
    "auctioneer-sp-602",
    "auctioneer-campinas-843",
    "auctioneer-campinas-911",
}
AUCTIONEER_OUTREACH_RESPONSES: dict[str, dict[str, str]] = {
    "auctioneer-sp-599": {
        "relationship_stage": "fora_do_radar_imobiliario",
        "outreach_status": "respondido_sem_imoveis",
        "response_received_at": "2026-05-19",
        "response_summary": "Vivian respondeu que infelizmente nao trabalha com imoveis.",
        "outreach_note": (
            "Resposta real recebida no Gmail: nao trabalha com imoveis. Remover do "
            "follow-up imobiliario e manter como aprendizado de qualidade da fonte."
        ),
    },
}


def _auctioneer_outreach_metadata(contact_id: object) -> dict[str, str]:
    if str(contact_id) not in AUCTIONEER_OUTREACH_SENT_IDS:
        return {}
    metadata = {
        "relationship_stage": "primeiro_contato_enviado",
        "outreach_status": "enviado",
        "outreach_channel": "Gmail",
        "outreach_sent_at": AUCTIONEER_OUTREACH_SENT_AT,
        "next_follow_up_at": AUCTIONEER_OUTREACH_NEXT_FOLLOW_UP_AT,
        "outreach_note": (
            "Envio confirmado pelo usuario no Gmail; aguardar resposta antes de "
            "promover lote de canal para candidato."
        ),
    }
    metadata.update(AUCTIONEER_OUTREACH_RESPONSES.get(str(contact_id), {}))
    if metadata.get("outreach_status") != "enviado":
        metadata.pop("next_follow_up_at", None)
    return metadata


AUCTIONEER_OUTREACH_PLAYBOOK: list[dict[str, str]] = [
    {
        "stage": "coleta_oficial",
        "action": "Extrair nome, matricula, situacao, site, e-mail e telefone publicados pela Junta Comercial.",
    },
    {
        "stage": "triagem_cauda_longa",
        "action": "Marcar baixa concorrencia quando o leiloeiro tem site simples, pouca presenca em portais e atuacao regional.",
    },
    {
        "stage": "primeiro_contato",
        "action": "Pedir mailing institucional de lotes imobiliarios no ticket alvo, sem pedir qualquer vantagem privada.",
    },
    {
        "stage": "relacionamento",
        "action": "Registrar tempo de resposta, clareza do edital, recorrencia de pauta e qualidade das informacoes.",
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


def generate_auctioneer_sourcing_report() -> dict[str, Any]:
    official_directories = [
        {
            **source,
            "brief_type": "auctioneer_official_directory",
            "trust_level": "official_directory",
            "next_action": (
                "Coletar contato publico, validar matricula e registrar resposta "
                "antes de promover qualquer lote para candidato."
            ),
        }
        for source in AUCTIONEER_DIRECTORY_SOURCES
    ]
    official_contacts = [
        {
            **contact,
            **_auctioneer_outreach_metadata(contact.get("id")),
            "brief_type": "auctioneer_official_contact",
            "trust_level": "official_contact_seed",
            "source_status": "official_captured_static_seed",
        }
        for contact in AUCTIONEER_OFFICIAL_CONTACTS
    ]
    long_tail_count = sum(
        1
        for source in official_directories
        if str(source.get("visibility_tier") or "") == "cauda_longa"
    )
    contact_source_count = sum(1 for source in official_directories if source.get("contact_path"))
    contact_tier_counts: dict[str, int] = {}
    for contact in official_contacts:
        tier = str(contact.get("competition_tier") or "validar")
        contact_tier_counts[tier] = contact_tier_counts.get(tier, 0) + 1
    outreach_sent_count = sum(1 for contact in official_contacts if contact.get("outreach_sent_at"))
    outreach_response_count = sum(1 for contact in official_contacts if contact.get("response_received_at"))
    outreach_no_real_estate_count = sum(
        1
        for contact in official_contacts
        if contact.get("outreach_status") == "respondido_sem_imoveis"
    )
    outreach_pending_response_count = outreach_sent_count - outreach_response_count

    return {
        "summary": {
            "official_directory_count": len(official_directories),
            "official_contact_count": len(official_contacts),
            "long_tail_directory_count": long_tail_count,
            "contact_source_count": contact_source_count,
            "outreach_sent_count": outreach_sent_count,
            "outreach_response_count": outreach_response_count,
            "outreach_no_real_estate_count": outreach_no_real_estate_count,
            "outreach_pending_response_count": outreach_pending_response_count,
            "next_follow_up_at": AUCTIONEER_OUTREACH_NEXT_FOLLOW_UP_AT,
            "scope_cities": AUCTIONEER_SCOPE_CITIES,
            "competition_tier_counts": contact_tier_counts,
            "actionability": (
                "Garimpo de cauda longa para sao paulo capital e campinas: usar a "
                "consulta oficial da JUCESP para encontrar leiloeiros Atuante Regular, "
                "separar canais estabelecidos de contatos menos obvios e so depois "
                "promover lotes para candidato."
            ),
        },
        "official_directories": official_directories,
        "official_contacts": official_contacts,
        "outreach_playbook": AUCTIONEER_OUTREACH_PLAYBOOK,
        "scoring_model": {
            "low_competition_signals": [
                "site simples ou pouco indexado",
                "baixa presenca em grandes portais",
                "atuacao regional",
                "agenda recorrente sem marketing agressivo",
            ],
            "quality_signals": [
                "matricula regular",
                "contato publico na Junta Comercial",
                "situacao Atuante Regular",
                "edital claro",
                "historico de lotes imobiliarios",
                "resposta direta e documentavel",
            ],
        },
    }


def generate_active_auction_portal_report() -> dict[str, Any]:
    sources = [
        {
            **source,
            "brief_type": "active_auction_portal_seed",
            "trust_level": "public_search_result",
            "next_action": (
                "Abrir a pagina, extrair identidade do ativo, seguir fonte oficial/editais "
                "e promover para candidato somente se preco, endereco e P0 forem utilizaveis."
            ),
        }
        for source in ACTIVE_AUCTION_PORTAL_SOURCES
    ]
    by_portal: dict[str, int] = {}
    by_role: dict[str, int] = {}
    for source in sources:
        portal = str(source.get("portal") or "desconhecido")
        role = str(source.get("source_role") or "source_clue")
        by_portal[portal] = by_portal.get(portal, 0) + 1
        by_role[role] = by_role.get(role, 0) + 1
    return {
        "summary": {
            "source_count": len(sources),
            "portal_counts": by_portal,
            "role_counts": by_role,
            "scope": "Sao Paulo capital, bairros-alvo e Campinas",
            "actionability": (
                "Leeilon e Leilao Imovel devem entrar como coletores ativos de entrada. "
                "Eles sao pistas publicas para descobrir candidatos; a aprovacao continua "
                "dependendo de edital/fonte oficial, fotos/condicao e comparaveis."
            ),
        },
        "sources": sources,
    }


def strategy_territory_report() -> dict[str, Any]:
    matrix = generate_strategy_territory_candidate_briefs()
    strategy_watchlist = generate_strategy_candidate_watchlist()
    watchlist = generate_condominium_requalification_watchlist()
    auctioneer_sourcing = generate_auctioneer_sourcing_report()
    active_portal_discovery = generate_active_auction_portal_report()
    return {
        "generated_at": _utc_now(),
        "summary": {
            "strategy_count": len(STRATEGY_BLUEPRINTS),
            "territory_count": len(TERRITORY_BLUEPRINTS),
            "matrix_brief_count": len(matrix),
            "source_candidate_count": len(strategy_watchlist),
            "source_confirmed_requalification_count": len(watchlist),
            "auctioneer_directory_count": auctioneer_sourcing["summary"]["official_directory_count"],
            "auctioneer_contact_count": auctioneer_sourcing["summary"]["official_contact_count"],
            "active_auction_portal_source_count": active_portal_discovery["summary"]["source_count"],
            "actionability": (
                "Briefs sao hipoteses de busca. Fontes listadas e sinais confirmados "
                "ainda exigem unidade, preco, comparaveis, disponibilidade vigente, "
                "diligencia P0 e validacao do canal de leiloeiro oficial."
            ),
        },
        "strategies": STRATEGY_BLUEPRINTS,
        "territories": TERRITORY_BLUEPRINTS,
        "matrix_briefs": matrix,
        "strategy_candidate_watchlist": strategy_watchlist,
        "condominium_requalification_watchlist": watchlist,
        "auctioneer_sourcing": auctioneer_sourcing,
        "active_auction_portal_discovery": active_portal_discovery,
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
        f"- fontes ativas de portais de leilao: `{summary['active_auction_portal_source_count']}`",
        (
            "- sinais confirmados de condominio em requalificacao: "
            f"`{summary['source_confirmed_requalification_count']}`"
        ),
        f"- diretorios oficiais de leiloeiros: `{summary['auctioneer_directory_count']}`",
        f"- contatos oficiais de leiloeiros: `{summary['auctioneer_contact_count']}`",
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

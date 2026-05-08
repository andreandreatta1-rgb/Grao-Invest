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


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _brief_id(territory_id: str, strategy_id: str) -> str:
    return f"IM-BUSCA-{territory_id}-{strategy_id}"


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


def generate_strategy_territory_candidate_briefs() -> list[dict[str, object]]:
    briefs: list[dict[str, object]] = []
    for territory in TERRITORY_BLUEPRINTS:
        for strategy in STRATEGY_BLUEPRINTS:
            territory_id = str(territory["territory_id"])
            strategy_id = str(strategy["strategy_id"])
            requires_condominium_signal = strategy_id == "condominio_antigo_requalificacao"
            checklist = list(BASE_DILIGENCE_CHECKLIST)
            if requires_condominium_signal:
                checklist = list(dict.fromkeys(CONDOMINIUM_DILIGENCE_CHECKLIST + checklist))
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


def strategy_territory_report() -> dict[str, Any]:
    matrix = generate_strategy_territory_candidate_briefs()
    watchlist = generate_condominium_requalification_watchlist()
    return {
        "generated_at": _utc_now(),
        "summary": {
            "strategy_count": len(STRATEGY_BLUEPRINTS),
            "territory_count": len(TERRITORY_BLUEPRINTS),
            "matrix_brief_count": len(matrix),
            "source_confirmed_requalification_count": len(watchlist),
            "actionability": (
                "Briefs sao hipoteses de busca. Sinais confirmados de condominio "
                "ainda exigem unidade, preco, comparaveis e diligencia."
            ),
        },
        "strategies": STRATEGY_BLUEPRINTS,
        "territories": TERRITORY_BLUEPRINTS,
        "matrix_briefs": matrix,
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
        (
            "- sinais confirmados de condominio em requalificacao: "
            f"`{summary['source_confirmed_requalification_count']}`"
        ),
        "",
        "## Regra de confianca",
        "",
        str(summary["actionability"]),
        "",
        "## Sinais confirmados de condominio",
    ]
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

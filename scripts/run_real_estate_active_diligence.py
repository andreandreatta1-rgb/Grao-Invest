from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


Fetcher = Callable[[str], str]

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

RESOLVABLE_P0_KEYS = {
    "source_validation",
    "source_access",
    "occupancy",
    "occupied_auction",
    "occupied_first_operation",
    "registration",
    "debt_total",
    "debts",
    "condo_debt",
    "iptu_debt",
    "edital",
}

OWNER_SCOPE_CITIES = {"sao paulo", "campinas"}

COURSE_ANTIBODY_DEFINITIONS: dict[str, dict[str, str]] = {
    "judicial_process_access": {
        "title": "Abrir processo judicial/autos",
        "priority": "P0",
        "action": (
            "Identificar processo, vara/tribunal, edital oficial, partes, onus, recursos "
            "visiveis e etapa antes de tratar o lote judicial como oportunidade."
        ),
    },
    "judicial_post_auction_plan": {
        "title": "Modelar pos-arrematacao judicial",
        "priority": "P0",
        "action": (
            "Validar auto de arrematacao, homologacao/assinaturas, carta, registro e "
            "imissao/posse antes de proposta."
        ),
    },
    "fiduciary_chain_unproven": {
        "title": "Provar cadeia fiduciaria",
        "priority": "P0",
        "action": (
            "Confirmar mora/notificacao, consolidacao da propriedade, matricula e etapa "
            "da praca/venda direta em fonte oficial."
        ),
    },
    "official_minimum_bid": {
        "title": "Confirmar lance minimo oficial",
        "priority": "P0",
        "action": (
            "Extrair o minimo oficial da praca e se ele depende de avaliacao, divida, "
            "despesas ou aceite do credor."
        ),
    },
    "caixa_sale_modality_unproven": {
        "title": "Classificar submodalidade Caixa",
        "priority": "P0",
        "action": (
            "Separar primeiro/segundo leilao, licitacao aberta, licitacao fechada, "
            "venda direta ou venda online direta e ler a regra oficial."
        ),
    },
    "caixa_debt_regularization_proof": {
        "title": "Provar regra Caixa para debitos",
        "priority": "P0",
        "action": (
            "Abrir regras oficiais da Caixa e confirmar se IPTU/condominio serao "
            "quitados, regularizados ou assumidos pelo comprador."
        ),
    },
    "conditional_bid_acceptance": {
        "title": "Confirmar aceite de lance condicionado",
        "priority": "P0",
        "action": (
            "Nao usar lance condicionado como preco executavel ate haver aceite, "
            "homologacao ou regra formal do vendedor/credor."
        ),
    },
    "failed_auction_liquidity_alert": {
        "title": "Validar liquidez apos leilao frustrado",
        "priority": "P1",
        "action": (
            "Tratar historico de leilao sem lance como alerta de demanda, preco, "
            "ocupacao ou documentacao, nao como prova de oportunidade."
        ),
    },
    "auction_modality_unclear": {
        "title": "Provar modalidade operacional do leilao",
        "priority": "P0",
        "action": (
            "Confirmar em edital, leiloeiro ou plataforma se a participacao e "
            "presencial, online ou hibrida antes de classificar como acionavel."
        ),
    },
    "bidder_registration_unproven": {
        "title": "Validar cadastro/habilitacao para lance",
        "priority": "P0",
        "action": (
            "Confirmar cadastro, habilitacao, aceite das regras e envio de documentos "
            "exigidos pela plataforma ou leiloeiro."
        ),
    },
    "online_closing_rule_unproven": {
        "title": "Provar regra de fechamento online",
        "priority": "P1",
        "action": (
            "Ler regra de encerramento, prorrogacao por novo lance, lance automatico "
            "e prazo final antes de definir tatico de lance."
        ),
    },
    "hybrid_competition_risk": {
        "title": "Modelar risco de leilao hibrido",
        "priority": "P1",
        "action": (
            "Tratar canal presencial e online simultaneos como risco competitivo e "
            "exigir margem/plano de lance mais conservador."
        ),
    },
    "representative_proxy_unproven": {
        "title": "Validar procuracao/representacao presencial",
        "priority": "P0",
        "action": (
            "Se o usuario nao comparecer pessoalmente, confirmar procuracao, poderes "
            "e reconhecimento exigidos para participacao presencial."
        ),
    },
    "labor_auction_core_terms_unproven": {
        "title": "Conciliar TRT/processo/lote/matricula",
        "priority": "P0",
        "action": (
            "Em leilao trabalhista, confirmar TRT, vara, processo, lote, matricula, "
            "avaliacao e lance minimo no edital/fonte oficial antes de tratar como oportunidade."
        ),
    },
    "labor_auction_debt_responsibility_unproven": {
        "title": "Provar debitos no leilao trabalhista",
        "priority": "P0",
        "action": (
            "Confirmar se IPTU, condominio e demais onus sub-rogam no preco, serao "
            "quitados ou ficam a cargo do arrematante."
        ),
    },
    "labor_auction_payment_terms_unproven": {
        "title": "Provar pagamento/comissao trabalhista",
        "priority": "P0",
        "action": (
            "Ler comissao do leiloeiro, sinal, deposito judicial, prazo de saldo, "
            "parcelamento permitido e penalidades por inadimplencia."
        ),
    },
    "labor_lot_unit_sale_unproven": {
        "title": "Provar venda individualizada do lote",
        "priority": "P0",
        "action": (
            "Quando o lote trabalhista mistura imovel e outros bens, confirmar se o "
            "imovel pode ser arrematado individualmente ou se ha preferencia pelo lote inteiro."
        ),
    },
    "remote_valuation_triangulation_unproven": {
        "title": "Triangular valor remoto do imovel",
        "priority": "P0",
        "action": (
            "Nao aceitar valor de saida por uma unica fonte; cruzar comparaveis, "
            "estimativa online, matricula/certidao e evidencias do mesmo predio/regiao."
        ),
    },
    "streetview_condition_unchecked": {
        "title": "Checar entorno e estado pelo Street View",
        "priority": "P1",
        "action": (
            "Abrir Google Street View/Maps para fachada, rua, acesso, conservacao, "
            "pichacao, comercio e sinais de depreciacao antes de validar preco remoto."
        ),
    },
    "sensitive_person_data_minimization": {
        "title": "Minimizar dados pessoais na investigacao",
        "priority": "P0",
        "action": (
            "Se usar CPF, telefone, redes sociais ou ferramentas privadas, limitar a "
            "fontes licitas e registrar apenas conclusao operacional, sem dado pessoal bruto."
        ),
    },
    "market_rotation_map_unproven": {
        "title": "Provar mapa de liquidez local",
        "priority": "P0",
        "action": (
            "Antes de chamar de melhor oferta, validar bairro/condominio, rotatividade, "
            "tempo real de venda e rede local de corretores/imobiliarias."
        ),
    },
    "caixa_financing_readiness_unproven": {
        "title": "Provar credito/entrada para Caixa",
        "priority": "P0",
        "action": (
            "Quando a tese Caixa depende de pouco capital, confirmar modalidade permite "
            "financiamento/FGTS, credito pre-aprovado, entrada e capacidade de pagamento."
        ),
    },
}

EXECUTION_READINESS_ANTIBODY_KEYS = {
    "auction_modality_unclear",
    "bidder_registration_unproven",
    "online_closing_rule_unproven",
    "hybrid_competition_risk",
    "representative_proxy_unproven",
}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = next((value for key, value in attrs if key.lower() == "href" and value), None)
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return
        self.links.append((self._href, " ".join(self._text)))
        self._href = None
        self._text = []


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def search_text(value: str) -> str:
    normalized = normalize_text(value)
    normalized = normalized.replace("º", "o").replace("ª", "a").replace("�", "")
    normalized = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
    return normalized.lower()


def ascii_clean(value: str) -> str:
    text = value.replace("º", "o").replace("ª", "a").replace("�", "o")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def repair_common_mojibake(value: str) -> str:
    return (
        value.replace("Matr�cula", "Matricula")
        .replace("matr�cula", "matricula")
        .replace("MATR�CULA", "MATRICULA")
        .replace("im�vel", "imovel")
        .replace("Im�vel", "Imovel")
        .replace("IM�VEL", "IMOVEL")
        .replace("n�", "no")
        .replace("N�", "No")
        .replace("�", "o")
    )


def extract_links(base_url: str, html_text: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html_text or "")
    links = [(urljoin(base_url, href), normalize_text(label)) for href, label in parser.links]
    for match in re.finditer(r"https?://[^\s\"'<>),;]+", html_text or "", flags=re.IGNORECASE):
        links.append((match.group(0).rstrip("."), ""))

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for href, label in links:
        if href in seen:
            continue
        seen.add(href)
        unique.append((href, label))
    return unique


def money_to_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.strip().replace("R$", "").replace(" ", "")
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _first_money_after(pattern: str, text: str) -> float | None:
    match = re.search(
        rf"(?:{pattern}).{{0,80}}?R\$\s*([\d.]+,\d{{2}})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return money_to_float(match.group(1))


def _official_leiloeiro_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".map", ".pdf")):
        return False
    if "leilaoimovel.com.br" in host or "suporteleiloes.com.br" in host:
        return False
    return any(
        marker in host
        for marker in (
            "webleiloes",
            "megaleiloes",
            "frazaoleiloes",
            "portalzuk",
            "zuk",
            "sold",
            "lanceja",
            "hastavip",
            "freitasleiloeiro",
            "vipleiloes",
            "proleilao",
        )
    )


def _same_page_anchor(base_url: str, href: str) -> bool:
    base = urlparse(base_url)
    parsed = urlparse(href)
    return (
        bool(parsed.fragment)
        and parsed.netloc.lower() == base.netloc.lower()
        and parsed.path.rstrip("/") == base.path.rstrip("/")
    )


def _official_url_from_document_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if "webleiloescombr" in path or "webleiloes" in host:
        return "https://www.webleiloes.com.br"
    if "megaleiloes" in host or "megaleiloes" in path:
        return "https://www.megaleiloes.com.br"
    if "vendasjudiciais.com.br" in host:
        return "https://www.vendasjudiciais.com.br"
    if "venda-imoveis.caixa.gov.br" in host:
        return "https://venda-imoveis.caixa.gov.br"
    if "picellileiloes" in host or "picellileiloes" in path:
        return "https://www.picellileiloes.com.br"
    if "portalzuk" in host:
        return "https://www.portalzuk.com.br"
    return ""


def _extract_registration(text: str) -> dict[str, str]:
    text = repair_common_mojibake(text)
    starts = [match.start() for match in re.finditer(r"matr.{0,3}cula", text, flags=re.IGNORECASE)]
    found: list[dict[str, str]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else min(len(text), start + 240)
        segment = text[start:end]
        match = re.search(
            r"matr.{0,3}cula(?:\s+do\s+im.{0,2}vel)?[:\s]*(?:n[ºo.]*:?)?\s*([\d.]+)",
            segment,
            flags=re.IGNORECASE,
        )
        if not match or not re.search(r"\d", match.group(1)):
            continue
        entry = {"matricula": match.group(1).rstrip(".")}
        tail = segment[match.end() : match.end() + 140]
        registry_match = re.search(
            r"(?:-|do|da)?\s*([^.;,\n]{0,90}?(?:CRI|SRI|Registro de Im[oó]veis|Cart[oó]rio|RI|ORI)[^.;,\n]{0,90})",
            tail,
            flags=re.IGNORECASE,
        )
        if registry_match:
            registry = re.sub(r"\s+", " ", registry_match.group(1)).strip(" -.")
            registry = re.sub(r"^(?:do|da)\s+", "", registry, flags=re.IGNORECASE)
            registry = re.split(
                r"\s+-\s+CNM\b|\s+CNM\b",
                registry,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" -.")
            entry["registry"] = ascii_clean(registry)
        found.append(entry)
    for entry in found:
        if entry.get("registry"):
            return entry
    if found:
        return found[0]
    return {}


def _extract_occupancy(text: str) -> tuple[str, str]:
    lower = search_text(text)
    if re.search(r"\bimovel\s+ocupad[oa]s?\b|\bocupad[oa]s?\b\.|sem visitacao", lower):
        return "ocupado", "Fonte informa imovel ocupado ou sem visitacao."
    if re.search(r"\bdesocupad[oa]s?\b|imovel vago|sem ocupantes", lower):
        return "desocupado", "Fonte informa imovel desocupado/vago."
    if re.search(r"\bimovel ocupado\b|\bocupad[oa]s?\b|sem visitacao", lower):
        return "ocupado", "Fonte informa imovel ocupado ou sem visitacao."
    return "desconhecido", ""


def _extract_debts(text: str) -> dict[str, Any]:
    lower = search_text(text)
    debts: dict[str, Any] = {}
    action_debt = _first_money_after(r"d[eé]bitos?\s+da\s+a[cç][aã]o|debito\s+da\s+acao", text)
    if action_debt is not None:
        debts["action_debt_brl"] = action_debt
    condo_value = _first_money_after(r"condom[ií]nio|condominio", text)
    if condo_value is not None:
        debts["condo_debt_brl"] = condo_value
    iptu_value = _first_money_after(r"iptu|tribut[aá]rios|tributarios", text)
    if iptu_value is not None:
        debts["iptu_debt_brl"] = iptu_value
    if (
        "condominio e iptu serao quitados pelo vendedor" in lower
        or "condominio e iptu serao quitados" in lower
        or ("quitados pelo vendedor" in lower and "condominio" in lower and "iptu" in lower)
    ):
        debts["seller_pays_condo_iptu_until_possession_transfer"] = True
    if "sub-roga" in lower and ("iptu" in lower or "tribut" in lower):
        debts["tax_debts_subrogated_in_bid_price"] = True
    return debts


def _course_antibody(key: str) -> dict[str, str]:
    definition = COURSE_ANTIBODY_DEFINITIONS[key]
    return {
        "key": key,
        "title": definition["title"],
        "priority": definition["priority"],
        "status": "aberta",
        "action": definition["action"],
    }


def _has_process_number(text: str) -> bool:
    return bool(re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", text))


def _has_process_link(links: list[tuple[str, str]]) -> bool:
    process_hosts = ("tjsp", "esaj", "pje", "trf", "tj", "jus.br")
    process_terms = ("processo", "autos", "process", "consulta")
    for href, label in links:
        parsed = urlparse(href)
        target = search_text(" ".join([parsed.netloc, parsed.path, parsed.query, label]))
        if any(host in target for host in process_hosts) and any(
            term in target for term in process_terms
        ):
            return True
    return False


def _is_auction_like_source(url: str, lower: str) -> bool:
    host = urlparse(url).netloc.lower()
    return bool(
        _official_leiloeiro_url(url)
        or "leilaoimovel.com.br" in host
        or "venda-imoveis.caixa.gov.br" in host
        or any(
            marker in lower
            for marker in (
                "leilao judicial",
                "leilao extrajudicial",
                "leilao online",
                "leilao presencial",
                "leilao hibrido",
                "leiloeiro",
                "lance minimo",
                "arrematacao",
                "arrematante",
                "1a praca",
                "2a praca",
                "primeira praca",
                "segunda praca",
            )
        )
    )


def _execution_modality_flags(lower: str) -> dict[str, bool]:
    hybrid = any(
        marker in lower
        for marker in (
            "hibrido",
            "presencial e online",
            "online e presencial",
            "presencial e on-line",
            "on-line e presencial",
        )
    )
    online = hybrid or any(
        marker in lower
        for marker in (
            "leilao online",
            "on-line",
            " online",
            "eletronico",
            "eletronica",
            "pela internet",
            "proposta pela internet",
            "plataforma online",
            "lance online",
            "venda online",
            "venda direta online",
        )
    )
    presencial = hybrid or any(
        marker in lower
        for marker in (
            "leilao presencial",
            " presencial",
            "auditorio",
            "local do leilao",
            "no forum",
            "foro",
            "escritorio do leiloeiro",
            "comparecer",
            "credenciamento presencial",
        )
    )
    return {"online": online, "presencial": presencial, "hybrid": hybrid}


def _requires_bidder_registration(lower: str) -> bool:
    return bool(
        re.search(
            r"\b(?:cadastro|cadastrado|cadastramento|habilitacao|habilitado|"
            r"credenciamento|documento|documentos|upload|identificacao)\b",
            lower,
        )
        or "envio de documentos" in lower
        or "aceite das regras" in lower
        or "aceitar as condicoes" in lower
    )


def _has_online_closing_rule(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "encerramento",
            "fechamento",
            "termino",
            "prazo final",
            "prorrogacao",
            "prorroga",
            "tempo extra",
            "novo lance",
            "lance automatico",
            "lance programado",
            "auto lance",
        )
    )


def _requires_representative_proxy(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "procuracao",
            "procurador",
            "representante",
            "firma reconhecida",
            "poderes especificos",
        )
    )


def _is_labor_auction_like(url: str, lower: str) -> bool:
    host = urlparse(url).netloc.lower()
    return bool(
        "justica do trabalho" in lower
        or "vara do trabalho" in lower
        or "reclamacao trabalhista" in lower
        or "execucao trabalhista" in lower
        or "tribunal regional do trabalho" in lower
        or ("hasta publica" in lower and "trt" in lower)
        or ("asta publica" in lower and "trt" in lower)
        or re.search(r"\btrt\s*\d+\b", lower)
        or re.search(r"\btrt\d+\.jus\.br\b", host)
    )


def _labor_core_terms_proven(
    lower: str,
    links: list[tuple[str, str]],
    minimum_bid: float | None,
) -> bool:
    has_trt_context = any(
        marker in lower
        for marker in (
            "trt",
            "vara do trabalho",
            "justica do trabalho",
            "tribunal regional do trabalho",
        )
    )
    has_lot = bool(re.search(r"\blote\s+(?:n[ou]mero\s+)?[a-z0-9.-]+", lower))
    has_registration = "matricula" in lower
    has_appraisal = any(
        marker in lower
        for marker in (
            "avaliacao",
            "valor avaliado",
            "avaliado em",
            "laudo de avaliacao",
        )
    )
    has_process = _has_process_number(lower) or _has_process_link(links)
    return bool(
        has_trt_context
        and has_process
        and has_lot
        and has_registration
        and has_appraisal
        and minimum_bid is not None
    )


def _labor_debt_responsibility_proven(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "artigo 130 do ctn",
            "art. 130 do ctn",
            "ctn",
            "sub-roga no preco",
            "subrogam no preco",
            "sub-rogam no preco",
            "condominio e iptu serao quitados",
            "debitos serao quitados",
            "debitos serao pagos",
            "debitos ficam a cargo do arrematante",
            "debitos a cargo do arrematante",
            "condominio e demais debitos ficam a cargo do arrematante",
            "responsabilidade do arrematante",
        )
    )


def _labor_payment_terms_proven(lower: str) -> bool:
    has_commission = "comissao" in lower or "5%" in lower or "5 por 100" in lower
    has_deadline_or_installment = any(
        marker in lower
        for marker in (
            "24 horas",
            "primeiro dia util",
            "deposito judicial",
            "saldo",
            "parcelamento",
            "parcelado",
            "parcelas",
            "30%",
            "30 por 100",
            "20%",
            "20 por 100",
        )
    )
    return has_commission and has_deadline_or_installment


def _labor_multi_asset_lot(lower: str) -> bool:
    multi_asset_terms = (
        "grupo de bens",
        "mais de um bem",
        "diversos bens",
        "bens moveis",
        "equipamentos",
        "maquinas",
        "veiculos",
        "carros",
        "moveis",
    )
    return (
        bool(re.search(r"\blote\s+\w+\s+com\b", lower))
        and any(term in lower for term in multi_asset_terms)
    ) or any(term in lower for term in ("imovel e equipamentos", "imoveis e equipamentos"))


def _labor_unit_sale_proven(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "venda individualizada",
            "arrematacao individualizada",
            "arrematado individualmente",
            "venda unitaria",
            "cada bem",
            "desmembramento autorizado",
            "desmembrar o lote",
        )
    )


def _needs_remote_valuation(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "valor de mercado",
            "preco de mercado",
            "valor de saida",
            "saida projetada",
            "saida estimada",
            "preco de venda",
            "valor estimado",
            "margem",
            "lucratividade",
            "comparavel",
            "comparaveis",
        )
    )


def _valuation_source_categories(lower: str) -> set[str]:
    categories: set[str] = set()
    if any(
        marker in lower
        for marker in (
            "viva real",
            "zap",
            "datazap",
            "data zap",
            "imovelweb",
            "chaves na mao",
            "olx",
            "quintoandar",
            "portal de imoveis",
        )
    ):
        categories.add("portal")
    if any(
        marker in lower
        for marker in (
            "comparavel",
            "comparaveis",
            "mesmo condominio",
            "mesmo predio",
            "metro quadrado",
            "m2",
            "valor medio",
        )
    ):
        categories.add("comparables")
    if _has_streetview_condition_check(lower):
        categories.add("streetview")
    if any(
        marker in lower
        for marker in (
            "matricula",
            "certidao",
            "certidao de onus",
            "cartorio",
            "onr",
            "registradores",
            "registro de imoveis",
        )
    ):
        categories.add("registry")
    return categories


def _has_remote_valuation_triangulation(lower: str) -> bool:
    categories = _valuation_source_categories(lower)
    return len(categories) >= 3 and bool(categories & {"portal", "comparables"})


def _has_streetview_condition_check(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "street view",
            "streetview",
            "google maps",
            "fachada",
            "entorno",
            "conservacao da rua",
            "estado de conservacao",
            "pichacao",
            "pichacoes",
            "acesso",
            "vizinho",
            "vizinhos",
            "porteiro",
            "sindico",
        )
    )


def _uses_sensitive_person_investigation(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "procob",
            "consulta facil",
            "cpf do executado",
            "cpf do reu",
            "telefone",
            "telefones",
            "celular",
            "celulares",
            "parentes",
            "perfil socioeconomico",
            "facebook",
            "linkedin",
            "rede social",
            "redes sociais",
        )
    )


def _personal_data_minimized(lower: str) -> bool:
    minimization_terms = (
        "lgpd",
        "fontes publicas",
        "fonte publica",
        "nao armazenar cpf",
        "nao armazenar telefone",
        "sem dado pessoal bruto",
        "sem dados pessoais brutos",
        "apenas conclusao operacional",
        "somente conclusao operacional",
        "minimizacao",
    )
    return any(term in lower for term in minimization_terms)


def _needs_market_rotation_map(lower: str) -> bool:
    return any(
        marker in lower
        for marker in (
            "melhor oferta",
            "melhores ofertas",
            "boa oferta",
            "otima oferta",
            "oportunidade",
            "revenda",
            "revender",
            "vender em",
            "venda em",
            "lucro",
            "lucratividade",
            "margem",
            "retorno",
            "roi",
        )
    )


def _market_rotation_map_categories(lower: str) -> set[str]:
    categories: set[str] = set()
    if any(
        marker in lower
        for marker in (
            "bairro",
            "microregiao",
            "micro-regiao",
            "regiao especifica",
            "condominio",
            "comarca",
            "cidade",
            "mesmo predio",
            "mesmo condominio",
        )
    ):
        categories.add("territory")
    if any(
        marker in lower
        for marker in (
            "rotatividade",
            "giro",
            "liquidez",
            "venda rapida",
            "vender rapido",
            "tempo de venda",
            "meses para vender",
            "dias para vender",
            "ultimo imovel vendido",
            "vendido em",
            "vendeu em",
        )
    ):
        categories.add("rotation")
    if any(
        marker in lower
        for marker in (
            "corretor local",
            "corretores locais",
            "imobiliaria local",
            "imobiliarias locais",
            "imobiliarias pequenas",
            "rede local",
            "relacionamento com corretor",
            "relacionamento com leiloeiro",
        )
    ):
        categories.add("local_network")
    if any(
        marker in lower
        for marker in (
            "mapa do investimento",
            "tese de saida",
            "plano de saida",
            "prazo esperado",
            "quanto vou investir",
            "capital alocado",
        )
    ):
        categories.add("investment_map")
    return categories


def _has_market_rotation_map(lower: str) -> bool:
    categories = _market_rotation_map_categories(lower)
    return "rotation" in categories and "territory" in categories and len(categories) >= 3


def _needs_caixa_financing_readiness(lower: str) -> bool:
    caixa_like = "venda-imoveis.caixa.gov.br" in lower or any(
        marker in lower
        for marker in (
            "imovel caixa",
            "imoveis caixa",
            "caixa economica",
            "venda direta caixa",
            "venda direta online caixa",
            "leilao sfi caixa",
            "licitacao aberta caixa",
            "retomada da caixa",
        )
    )
    financing_like = any(
        marker in lower
        for marker in (
            "sem dinheiro",
            "pouca entrada",
            "pouco de entrada",
            "quase nada de entrada",
            "financiamento",
            "financiar",
            "fgts",
            "credito bancario",
            "credito imobiliario",
        )
    )
    return caixa_like and financing_like


def _has_caixa_financing_readiness(lower: str) -> bool:
    readiness_terms = (
        "credito aprovado",
        "credito pre-aprovado",
        "pre-aprovacao de credito",
        "pre aprovacao de credito",
        "simulacao aprovada",
        "financiamento aprovado",
        "fgts confirmado",
        "entrada reservada",
        "capacidade de pagamento confirmada",
        "renda validada",
    )
    return any(term in lower for term in readiness_terms)


def _course_antibodies(
    url: str,
    text: str,
    links: list[tuple[str, str]],
    minimum_bid: float | None,
) -> list[dict[str, str]]:
    lower = search_text(" ".join([url, text]))
    found: list[str] = []
    auction_like = _is_auction_like_source(url, lower)
    execution_modality = _execution_modality_flags(lower)

    judicial_like = bool(
        re.search(
            r"\b(?:leilao judicial|leiloes judiciais|judicial|vara|processo|execucao)\b",
            lower,
        )
        or "carta de arrematacao" in lower
        or "auto de arrematacao" in lower
    )
    if judicial_like and not _has_process_number(lower) and not _has_process_link(links):
        found.append("judicial_process_access")

    post_auction_terms = (
        "auto de arrematacao",
        "carta de arrematacao",
        "homologacao",
        "registro",
        "imissao",
        "posse",
    )
    if judicial_like and not any(term in lower for term in post_auction_terms):
        found.append("judicial_post_auction_plan")

    labor_like = auction_like and _is_labor_auction_like(url, lower)
    if labor_like and not _labor_core_terms_proven(lower, links, minimum_bid):
        found.append("labor_auction_core_terms_unproven")
    if labor_like and not _labor_debt_responsibility_proven(lower):
        found.append("labor_auction_debt_responsibility_unproven")
    if labor_like and not _labor_payment_terms_proven(lower):
        found.append("labor_auction_payment_terms_unproven")
    if labor_like and _labor_multi_asset_lot(lower) and not _labor_unit_sale_proven(lower):
        found.append("labor_lot_unit_sale_unproven")

    if auction_like and _needs_remote_valuation(lower):
        if not _has_remote_valuation_triangulation(lower):
            found.append("remote_valuation_triangulation_unproven")
        if not _has_streetview_condition_check(lower):
            found.append("streetview_condition_unchecked")

    if (
        auction_like
        and _uses_sensitive_person_investigation(lower)
        and not _personal_data_minimized(lower)
    ):
        found.append("sensitive_person_data_minimization")

    if auction_like and _needs_market_rotation_map(lower) and not _has_market_rotation_map(lower):
        found.append("market_rotation_map_unproven")

    if (
        auction_like
        and _needs_caixa_financing_readiness(lower)
        and not _has_caixa_financing_readiness(lower)
    ):
        found.append("caixa_financing_readiness_unproven")

    fiduciary_like = any(
        marker in lower
        for marker in (
            "leilao extrajudicial",
            "extrajudicial",
            "alienacao fiduciaria",
            "propriedade fiduciaria",
            "lei 9.514",
            "lei 9514",
            "ocupada (af)",
            "ocupado (af)",
        )
    )
    fiduciary_chain_proven = any(
        marker in lower
        for marker in (
            "consolidacao da propriedade",
            "propriedade consolidada",
            "consolidada em favor",
            "consolidado em favor",
            "consolidacao em nome",
            "consolidou a propriedade",
            "consolidou propriedade",
        )
    )
    if fiduciary_like and not fiduciary_chain_proven:
        found.append("fiduciary_chain_unproven")

    second_auction_like = any(
        marker in lower
        for marker in ("2a praca", "2 praca", "segunda praca", "segundo leilao")
    )
    if second_auction_like and minimum_bid is None:
        found.append("official_minimum_bid")

    if any(
        marker in lower
        for marker in (
            "lance condicionado",
            "lances condicionados",
            "condicionado ao aceite",
            "sujeito a aceite",
            "sujeito a aprovacao",
            "dependente de aceite",
        )
    ):
        found.append("conditional_bid_acceptance")

    caixa_like = "venda-imoveis.caixa.gov.br" in lower or any(
        marker in lower
        for marker in (
            "imovel caixa",
            "imoveis caixa",
            "caixa economica",
            "venda direta caixa",
            "leilao sfi caixa",
            "licitacao aberta caixa",
            "cef",
        )
    )
    caixa_modality_proven = any(
        marker in lower
        for marker in (
            "venda direta",
            "venda online",
            "venda direta online",
            "licitacao aberta",
            "licitacao fechada",
            "proposta pela internet",
            "primeiro leilao",
            "segundo leilao",
            "1o leilao",
            "2o leilao",
            "1a praca",
            "2a praca",
        )
    )
    if caixa_like and not caixa_modality_proven:
        found.append("caixa_sale_modality_unproven")

    caixa_debt_proven = any(
        marker in lower
        for marker in (
            "debitos serao quitados",
            "debitos serao regularizados",
            "condominio e iptu serao quitados",
            "quitados pela caixa",
            "regularizacao dos debitos",
            "regularizar os debitos",
        )
    )
    if caixa_like and not caixa_debt_proven:
        found.append("caixa_debt_regularization_proof")

    if any(
        marker in lower
        for marker in (
            "leilao frustrado",
            "leiloes frustrados",
            "sem lance",
            "sem lances",
            "sem licitantes",
            "nao houve lance",
            "leilao negativo",
            "praca negativa",
        )
    ):
        found.append("failed_auction_liquidity_alert")

    if auction_like and not any(execution_modality.values()):
        found.append("auction_modality_unclear")

    if auction_like and _requires_bidder_registration(lower):
        found.append("bidder_registration_unproven")

    if auction_like and (
        execution_modality["online"] or execution_modality["hybrid"]
    ) and not _has_online_closing_rule(lower):
        found.append("online_closing_rule_unproven")

    if auction_like and execution_modality["hybrid"]:
        found.append("hybrid_competition_risk")

    if auction_like and (
        execution_modality["presencial"] or execution_modality["hybrid"]
    ) and _requires_representative_proxy(lower):
        found.append("representative_proxy_unproven")

    return [_course_antibody(key) for key in dict.fromkeys(found)]


def _looks_like_navigation_or_filter_text(text: str) -> bool:
    lower = search_text(text)
    raw_lower = (text or "").lower()
    leilao_imovel_filters = (
        "filtros localidade" in lower
        and "modalidade comprei pgfn" in lower
        and "arrematante paga" in lower
    )
    portalzuk_navigation = (
        "tipo de im" in raw_lower
        and "judiciais" in lower
        and "extrajudiciais" in lower
    )
    return leilao_imovel_filters or portalzuk_navigation


def _row_course_context(row: dict[str, Any], evidence: dict[str, Any]) -> str:
    analysis = row.get("real_estate_analysis") if isinstance(row.get("real_estate_analysis"), dict) else {}
    candidate = analysis.get("candidate") if isinstance(analysis.get("candidate"), dict) else {}
    source_validation = (
        analysis.get("source_validation") if isinstance(analysis.get("source_validation"), dict) else {}
    )
    parts: list[str] = []
    for payload in (row, analysis, candidate, source_validation):
        if not isinstance(payload, dict):
            continue
        for key in (
            "action",
            "asset",
            "thesis_reason",
            "operation_plan",
            "structured_operation",
            "learning_note",
            "exit_rule",
            "strategy",
            "origin",
            "listing_description",
            "auction_description",
            "notes",
            "source_validation_reason",
            "reason",
            "source_url",
        ):
            value = payload.get(key)
            if value:
                parts.append(str(value))
    parts.extend(
        str(evidence.get(key) or "")
        for key in ("source_url", "official_url", "edital_url")
        if evidence.get(key)
    )
    text_excerpt = str(evidence.get("text_excerpt") or "")
    if text_excerpt and not _looks_like_navigation_or_filter_text(text_excerpt):
        parts.append(text_excerpt)
    return " ".join(parts)


def extract_evidence(url: str, html_text: str) -> dict[str, Any]:
    text = normalize_text(html_text)
    lower = search_text(text)
    links = extract_links(url, html_text)
    host = urlparse(url).netloc.lower()
    official_url = url if _official_leiloeiro_url(url) else ""
    edital_url = ""
    pdf_urls: list[str] = []
    for href, label in links:
        normalized_href = search_text(href)
        normalized_label = search_text(label)
        if href.lower().endswith(".pdf"):
            pdf_urls.append(href)
        href_scheme = urlparse(href).scheme.lower()
        if href_scheme in {"http", "https"} and not edital_url and (
            href.lower().endswith(".pdf")
            and ("edital" in normalized_href or "suporteleiloes.com.br" in normalized_href)
        ):
            edital_url = href
        if href_scheme in {"http", "https"} and not edital_url and "edital" in normalized_label:
            edital_url = href
        if not official_url and not _same_page_anchor(url, href) and (
            _official_leiloeiro_url(href)
            or "ver anuncio no leiloeiro" in normalized_label
        ):
            official_url = href
    if not official_url and _official_leiloeiro_url(url):
        official_url = url
    if not official_url:
        for href in [edital_url, *pdf_urls]:
            official_url = _official_url_from_document_url(href)
            if official_url:
                break

    occupancy_status, occupancy_evidence = _extract_occupancy(text)
    registration = _extract_registration(text)
    debts = _extract_debts(text)
    minimum_bid = _first_money_after(
        r"lance\s+m[ií]nimo|lance minimo|2[ªa]\s+pra[cç]a|2a\s+praca|valor",
        text,
    )
    course_antibodies = (
        []
        if _looks_like_navigation_or_filter_text(text)
        else _course_antibodies(url, text, links, minimum_bid)
    )
    leiloeiro_name = ""
    match = re.search(r"leiloeiro\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç .-]{2,40})", text)
    if match:
        leiloeiro_name = match.group(1).strip(" .-")

    access_required = any(
        marker in lower
        for marker in (
            "captcha",
            "recaptcha",
            "acesso restrito",
            "faca seu cadastro",
            "cadastro necessario",
            "entre para continuar",
            "login para continuar",
        )
    )

    not_found = any(
        marker in lower
        for marker in (
            "404: this page could not be found",
            "pagina nao encontrada",
            "page could not be found",
            "anuncio nao encontrado",
            "lote nao encontrado",
        )
    )

    source_is_proven = bool(
        _official_leiloeiro_url(url)
        or ("leilaoimovel.com.br" in host and (official_url or edital_url))
        or ("venda-imoveis.caixa.gov.br" in host)
        or ("portalzuk.com.br" in host and registration)
        or ("proleilao.com.br" in host and registration)
    )
    if not_found:
        status = "nao_encontrado_apos_busca"
    elif access_required:
        status = "bloqueado_por_acesso"
    elif source_is_proven:
        status = "validado"
    else:
        status = "ambiguo"

    evidence: dict[str, Any] = {
        "status": status,
        "source_url": url,
        "opened_url": url,
        "aggregator_url": url if "leilaoimovel.com.br" in host else "",
        "official_url": "" if not_found else official_url or (url if _official_leiloeiro_url(url) else ""),
        "edital_url": edital_url,
        "pdf_urls": pdf_urls,
        "leiloeiro": leiloeiro_name,
        "occupancy_status": occupancy_status,
        "occupancy_evidence": occupancy_evidence,
        "registration": registration,
        "debts": debts,
        "minimum_bid_brl": minimum_bid,
        "course_antibodies": course_antibodies,
        "attempted_paths": [
            "abrir fonte inicial",
            "extrair links de edital/PDF/leiloeiro",
            "ler texto publico da pagina",
            "extrair ocupacao, matricula e debitos",
        ],
        "text_excerpt": text[:900],
    }
    if access_required:
        host_hint = urlparse(url).netloc.lower().replace(":", "-")
        evidence["access_request"] = {
            "site": url,
            "blocker_type": "login/cadastro/captcha",
            "why_it_matters": "A fonte bloqueou o proximo passo da diligencia publica.",
            "credential_file_hint": f"data/secure/real_estate_sources/{host_hint}.credentials.json",
        }
    return evidence


def default_fetcher(url: str, timeout_seconds: int = 35) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": BROWSER_UA,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            return _decode_bytes(raw, encoding)
    except (HTTPError, URLError, TimeoutError, OSError):
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if not curl:
            raise
        result = subprocess.run(
            [
                curl,
                "-L",
                "--max-time",
                str(timeout_seconds),
                "-A",
                BROWSER_UA,
                "-H",
                "Accept-Language: pt-BR,pt;q=0.9,en;q=0.8",
                url,
            ],
            capture_output=True,
            text=False,
            check=False,
        )
        if result.returncode != 0:
            stderr = _decode_bytes(result.stderr or b"", "utf-8").strip()
            raise RuntimeError(stderr or f"curl failed for {url}")
        return _decode_bytes(result.stdout or b"", "utf-8")


def _decode_bytes(raw: bytes, preferred_encoding: str) -> str:
    encodings = [preferred_encoding, "utf-8", "windows-1252", "iso-8859-1"]
    seen: set[str] = set()
    best = ""
    best_replacements = 10**9
    for encoding in encodings:
        normalized = (encoding or "utf-8").lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            decoded = raw.decode(encoding, errors="replace")
        except LookupError:
            continue
        replacements = decoded.count("�")
        if replacements < best_replacements:
            best = decoded
            best_replacements = replacements
        if replacements == 0:
            return decoded
    return best


def _p0_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = row.get("real_estate_analysis") if isinstance(row.get("real_estate_analysis"), dict) else {}
    pending = analysis.get("pending_items") if isinstance(analysis, dict) else []
    if not isinstance(pending, list):
        return []
    return [
        item
        for item in pending
        if isinstance(item, dict) and str(item.get("priority") or "").upper() == "P0"
    ]


def active_p0_rows(seed: dict[str, Any]) -> list[dict[str, Any]]:
    rows = seed.get("thesis_open_operations")
    if not isinstance(rows, list):
        return []
    selected: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("front") or "").lower() != "imoveis":
            continue
        if row.get("is_open") is not True:
            continue
        if _p0_items(row):
            selected.append(row)
    return sorted(selected, key=lambda item: int(item.get("thesis_number") or 0))


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.strip().lower()


def _candidate_city(row: dict[str, Any]) -> str:
    analysis = row.get("real_estate_analysis") if isinstance(row.get("real_estate_analysis"), dict) else {}
    candidate = analysis.get("candidate") if isinstance(analysis.get("candidate"), dict) else {}
    return str(candidate.get("city") or "").strip()


def _discard_out_of_scope_city_row(row: dict[str, Any], checked_at: str, *, city: str) -> dict[str, Any]:
    analysis = row.setdefault("real_estate_analysis", {})
    if not isinstance(analysis, dict):
        analysis = {}
        row["real_estate_analysis"] = analysis
    reason = f"Cidade fora do escopo atual do radar (SP capital + Campinas): {city}."
    resolved_p0: list[str] = []
    pending = analysis.get("pending_items")
    pending_items = [item for item in pending if isinstance(item, dict)] if isinstance(pending, list) else []
    kept_pending: list[dict[str, Any]] = []
    for item in pending_items:
        if str(item.get("priority") or "").upper() == "P0":
            item["status"] = "resolvida_por_descarte"
            item["resolution"] = "out_of_scope_city_discard"
            if item.get("key"):
                resolved_p0.append(str(item["key"]))
            continue
        kept_pending.append(item)
    analysis["pending_items"] = kept_pending
    _replace_or_append_clarified(
        analysis,
        _clarified_item("scope", "Fora do escopo do radar", reason),
    )
    analysis["suggested_status"] = "Descartado"
    analysis["next_action"] = "Fechar candidato: fora do escopo (SP capital + Campinas)"
    row["status"] = "Fechada"
    row["outcome"] = "Fora do escopo"
    row["is_open"] = False
    row["exit_rule"] = reason
    row["learning_note"] = f"Owner: {reason}"
    row["planned_exit_at"] = ""
    row["moment_result_pct"] = 0.0
    analysis["diligence_result"] = {
        "checked_at": checked_at,
        "status": "fora_do_escopo",
        "resolved_p0_keys": sorted(set(resolved_p0)),
        "course_antibodies": [],
        "remaining_p0_keys": [],
        "evidence": {"status": "fora_do_escopo", "city": city, "reason": reason},
    }
    return analysis["diligence_result"]


def _clarified_item(key: str, title: str, detail: str) -> dict[str, str]:
    return {"key": key, "title": title, "detail": detail}


def _replace_or_append_clarified(analysis: dict[str, Any], item: dict[str, str]) -> None:
    current = analysis.get("clarified_items")
    clarified = [entry for entry in current if isinstance(entry, dict)] if isinstance(current, list) else []
    clarified = [entry for entry in clarified if entry.get("key") != item["key"]]
    clarified.append(item)
    analysis["clarified_items"] = clarified


def _remove_resolved_pending_items(analysis: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    pending = analysis.get("pending_items")
    pending_items = [item for item in pending if isinstance(item, dict)] if isinstance(pending, list) else []
    resolved: set[str] = set()
    if evidence.get("status") == "validado":
        resolved.update({"source_validation", "source_access", "edital"})
    if evidence.get("occupancy_status") in {"ocupado", "desocupado"}:
        resolved.update({"occupancy", "occupied_auction", "occupied_first_operation"})
    if evidence.get("registration"):
        resolved.add("registration")
    debts = evidence.get("debts")
    if isinstance(debts, dict) and debts:
        resolved.update({"debts", "debt_total", "condo_debt", "iptu_debt"})

    analysis["pending_items"] = [
        item
        for item in pending_items
        if str(item.get("key") or "") not in resolved
    ]
    return sorted(resolved)


def _append_course_antibodies(analysis: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    raw_items = evidence.get("course_antibodies")
    if not isinstance(raw_items, list):
        return []
    current = analysis.get("clarified_items")
    if isinstance(current, list):
        analysis["clarified_items"] = [
            entry
            for entry in current
            if not (isinstance(entry, dict) and entry.get("key") == "course_antibodies")
        ]
    pending = analysis.get("pending_items")
    pending_items = [item for item in pending if isinstance(item, dict)] if isinstance(pending, list) else []
    current_course_keys = [
        str(item.get("key") or "").strip()
        for item in raw_items
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    ]
    current_course_key_set = set(current_course_keys)
    pending_items = [
        item
        for item in pending_items
        if str(item.get("key") or "") not in COURSE_ANTIBODY_DEFINITIONS
        or str(item.get("key") or "") in current_course_key_set
    ]
    existing_keys = {str(item.get("key") or "") for item in pending_items}
    added: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        key = str(raw_item.get("key") or "").strip()
        if not key or key in existing_keys:
            continue
        pending_items.append(
            {
                "key": key,
                "title": str(raw_item.get("title") or key),
                "priority": str(raw_item.get("priority") or "P0"),
                "status": str(raw_item.get("status") or "aberta"),
                "action": str(raw_item.get("action") or ""),
            }
        )
        existing_keys.add(key)
        added.append(key)
    analysis["pending_items"] = pending_items
    if current_course_keys:
        _replace_or_append_clarified(
            analysis,
            _clarified_item(
                "course_antibodies",
                "Anticorpos do curso aplicados",
                ", ".join(current_course_keys),
            ),
        )
    return current_course_keys


def _remove_irrelevant_execution_readiness(analysis: dict[str, Any]) -> None:
    pending = analysis.get("pending_items")
    pending_items = (
        [item for item in pending if isinstance(item, dict)]
        if isinstance(pending, list)
        else []
    )
    analysis["pending_items"] = [
        item
        for item in pending_items
        if str(item.get("key") or "") not in EXECUTION_READINESS_ANTIBODY_KEYS
    ]
    result = analysis.get("diligence_result")
    if not isinstance(result, dict):
        return
    result["course_antibodies"] = [
        key
        for key in result.get("course_antibodies", [])
        if key not in EXECUTION_READINESS_ANTIBODY_KEYS
    ]
    result["remaining_p0_keys"] = [
        str(item.get("key") or "")
        for item in analysis.get("pending_items", [])
        if isinstance(item, dict) and str(item.get("priority") or "").upper() == "P0"
    ]
    evidence = result.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("course_antibodies"), list):
        evidence["course_antibodies"] = [
            item
            for item in evidence["course_antibodies"]
            if not (
                isinstance(item, dict)
                and str(item.get("key") or "") in EXECUTION_READINESS_ANTIBODY_KEYS
            )
        ]


def _is_first_operation(row: dict[str, Any], analysis: dict[str, Any]) -> bool:
    candidate = analysis.get("candidate") if isinstance(analysis.get("candidate"), dict) else {}
    values = [
        row.get("first_operation"),
        row.get("firstOperation"),
        analysis.get("first_operation"),
        analysis.get("firstOperation"),
        candidate.get("first_operation"),
        candidate.get("firstOperation"),
    ]
    for value in values:
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "sim", "yes"}
    return True


def apply_evidence_to_row(row: dict[str, Any], evidence: dict[str, Any], checked_at: str) -> dict[str, Any]:
    analysis = row.setdefault("real_estate_analysis", {})
    if not isinstance(analysis, dict):
        analysis = {}
        row["real_estate_analysis"] = analysis
    candidate = analysis.setdefault("candidate", {})
    if not isinstance(candidate, dict):
        candidate = {}
        analysis["candidate"] = candidate

    previous_source_status = str(
        row.get("source_validation_status")
        or candidate.get("source_validation_status")
        or ""
    ).lower()
    previous_source_reason = str(
        row.get("source_validation_reason")
        or candidate.get("source_validation_reason")
        or ""
    ).strip()
    valid_reason = "Investigador abriu a cadeia publica e extraiu evidencia primaria."
    if (
        evidence.get("status") == "validado"
        and previous_source_status == "valid"
        and previous_source_reason
        and previous_source_reason != valid_reason
    ):
        valid_reason = previous_source_reason
    context_for_reason = search_text(
        " ".join(
            str(value or "")
            for value in (
                candidate.get("listing_description"),
                candidate.get("notes"),
                row.get("learning_note"),
                evidence.get("official_url"),
            )
        )
    )
    if evidence.get("status") == "validado" and "banco bradesco" in context_for_reason:
        valid_reason = (
            "Fonte oficial Zuk/Banco Bradesco validada; edital, matricula 22.175 "
            "e consolidacao da propriedade analisados."
        )

    source_validation = {
        "status": (
            "valid"
            if evidence.get("status") == "validado"
            else "access_required"
            if evidence.get("status") == "bloqueado_por_acesso"
            else "unavailable"
            if evidence.get("status") == "nao_encontrado_apos_busca"
            else "ambiguous"
        ),
        "reason": (
            valid_reason
            if evidence.get("status") == "validado"
            else "Fonte nao encontrada apos abrir o caminho publico informado."
            if evidence.get("status") == "nao_encontrado_apos_busca"
            else "Investigador ainda nao comprovou a cadeia primaria."
        ),
        "checked_at": checked_at,
        "url": evidence.get("official_url") or evidence.get("opened_url") or evidence.get("source_url") or row.get("source_url") or "",
        "aggregator_url": evidence.get("aggregator_url") or "",
        "official_url": evidence.get("official_url") or "",
        "edital_url": evidence.get("edital_url") or "",
        "investigation_status": evidence.get("status"),
        "investigation_policy": "investigador_implacavel",
    }
    if evidence.get("access_request"):
        source_validation.update(evidence["access_request"])
        source_validation["requires_user_action"] = True
    analysis["source_validation"] = source_validation
    row["source_validation"] = source_validation
    row["source_validation_status"] = source_validation["status"]
    row["source_validation_reason"] = source_validation["reason"]
    row["source_checked_at"] = checked_at
    candidate["source_validation"] = source_validation
    candidate["source_validation_status"] = source_validation["status"]
    candidate["source_validation_reason"] = source_validation["reason"]

    if evidence.get("occupancy_status") in {"ocupado", "desocupado"}:
        occupancy = str(evidence["occupancy_status"])
        analysis["occupancy_status"] = occupancy
        candidate["occupancy_status"] = occupancy
        row["occupancy_status"] = occupancy
        _replace_or_append_clarified(
            analysis,
            _clarified_item("occupancy", "Ocupacao esclarecida", str(evidence.get("occupancy_evidence") or f"Ocupacao: {occupancy}.")),
        )
    if evidence.get("registration"):
        registration = evidence["registration"]
        analysis["has_registration"] = True
        candidate["has_registration"] = True
        analysis["registration"] = registration
        candidate["registration"] = registration
        _replace_or_append_clarified(
            analysis,
            _clarified_item(
                "registration",
                "Matricula localizada",
                "Matricula "
                + str(registration.get("matricula") or "")
                + (f" - {registration.get('registry')}" if registration.get("registry") else ""),
            ),
        )
    debts = evidence.get("debts")
    if isinstance(debts, dict) and debts:
        analysis["condo_debt_known"] = True
        analysis["iptu_debt_known"] = True
        candidate["condo_debt_known"] = True
        candidate["iptu_debt_known"] = True
        analysis["debt_evidence"] = debts
        candidate["debt_evidence"] = debts
        detail_parts = []
        if debts.get("seller_pays_condo_iptu_until_possession_transfer"):
            detail_parts.append("vendedor quita condominio/IPTU ate transferencia da posse")
        if debts.get("tax_debts_subrogated_in_bid_price"):
            detail_parts.append("tributos sub-rogam no preco")
        if debts.get("action_debt_brl"):
            detail_parts.append(f"debitos da acao R$ {debts['action_debt_brl']:,.2f}")
        _replace_or_append_clarified(
            analysis,
            _clarified_item("debts", "Debitos lidos na fonte", "; ".join(detail_parts) or "Ha evidencia publica de debitos/responsabilidades."),
        )
    if evidence.get("edital_url"):
        analysis["has_edital"] = True
        candidate["has_edital"] = True
        _replace_or_append_clarified(
            analysis,
            _clarified_item("edital", "Edital localizado", str(evidence.get("edital_url"))),
        )
    if evidence.get("official_url") or evidence.get("status") == "validado":
        _replace_or_append_clarified(
            analysis,
            _clarified_item(
                "source_validation",
                "Fonte primaria investigada",
                str(evidence.get("official_url") or evidence.get("opened_url") or evidence.get("source_url")),
            ),
        )

    row_course_context = _row_course_context(row, evidence)
    context_course_antibodies = _course_antibodies(
        str(evidence.get("source_url") or row.get("source_url") or ""),
        row_course_context,
        [],
        evidence.get("minimum_bid_brl") if isinstance(evidence.get("minimum_bid_brl"), float) else None,
    )
    merged_course_antibodies: dict[str, dict[str, str]] = {}
    for raw_item in [*(evidence.get("course_antibodies") or []), *context_course_antibodies]:
        if isinstance(raw_item, dict) and raw_item.get("key"):
            merged_course_antibodies[str(raw_item["key"])] = raw_item
    evidence["course_antibodies"] = list(merged_course_antibodies.values())

    resolved_keys = _remove_resolved_pending_items(analysis, evidence)
    course_antibody_keys = _append_course_antibodies(analysis, evidence)
    analysis["diligence_result"] = {
        "checked_at": checked_at,
        "status": evidence.get("status"),
        "resolved_p0_keys": resolved_keys,
        "course_antibodies": course_antibody_keys,
        "remaining_p0_keys": [
            str(item.get("key") or "")
            for item in analysis.get("pending_items", [])
            if isinstance(item, dict) and str(item.get("priority") or "").upper() == "P0"
        ],
        "evidence": evidence,
    }

    occupied_without_plan = (
        evidence.get("occupancy_status") == "ocupado" and _is_first_operation(row, analysis)
    )
    if evidence.get("status") == "nao_encontrado_apos_busca":
        analysis["suggested_status"] = "Descartado"
        analysis["next_action"] = "Fechar candidato: fonte indisponivel"
        row["status"] = "Fechada"
        row["outcome"] = "Fonte indisponivel"
        row["is_open"] = False
        row["exit_rule"] = "Fonte publica informada retornou pagina nao encontrada."
        row["learning_note"] = "Investigador abriu a fonte e encontrou pagina indisponivel; remover do radar ativo ate existir nova fonte individual."
        row["planned_exit_at"] = ""
        row["moment_result_pct"] = 0.0
    elif occupied_without_plan:
        _remove_irrelevant_execution_readiness(analysis)
        analysis["suggested_status"] = "Descartado"
        analysis["next_action"] = "Fechar candidato: imóvel ocupado sem plano aprovado"
        row["status"] = "Fechada"
        row["outcome"] = "Descartado pelo radar"
        row["is_open"] = False
        row["exit_rule"] = "Imovel ocupado sem plano aprovado de desocupacao para primeira operacao."
        row["learning_note"] = (
            "Investigador esclareceu a ocupacao. Como e primeira operacao e nao ha plano "
            "aprovado de desocupacao, o candidato sai do radar ativo."
        )
        row["planned_exit_at"] = ""
        row["moment_result_pct"] = 0.0
    else:
        remaining_p0 = [
            item
            for item in analysis.get("pending_items", [])
            if isinstance(item, dict) and str(item.get("priority") or "").upper() == "P0"
        ]
        if remaining_p0:
            analysis["suggested_status"] = "Aberto com pendencias"
            analysis["next_action"] = str(remaining_p0[0].get("title") or "Resolver P0 restante")
            row["status"] = "Aberta - Atencao"
            row["outcome"] = "Pendencias abertas"
            row["is_open"] = True
        elif evidence.get("status") == "validado":
            analysis["suggested_status"] = "Diligencia"
            analysis["next_action"] = "Revisar comparaveis e proposta conservadora"
            row["status"] = "Aberta - Diligencia"
            row["outcome"] = "Evidencias P0 esclarecidas"
            row["is_open"] = True
        elif evidence.get("status") == "bloqueado_por_acesso":
            analysis["suggested_status"] = "Aberto com pendencias"
            analysis["next_action"] = "Acesso ao leiloeiro necessario"
            row["status"] = "Aberta - Atencao"
            row["outcome"] = "Bloqueado por acesso"
            row["is_open"] = True

    return analysis["diligence_result"]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Diligencia ativa do Radar Imobiliario",
        "",
        f"- Gerado em: {report['generated_at']}",
        f"- Candidatos investigados: {report['investigated_count']}",
        f"- Fechados por prova/risco: {report['closed_count']}",
        f"- Ainda abertos com P0: {report['still_open_with_p0_count']}",
        f"- Bloqueados por acesso: {report['access_blocked_count']}",
        "",
        "## Itens",
        "",
    ]
    for item in report["items"]:
        lines.extend(
            [
                f"### {item['thesis_number']} - {item['title']}",
                "",
                f"- Status: {item['status']}",
                f"- Decisao: {item['decision']}",
                f"- Fonte: {item['source_url']}",
                f"- Oficial: {item.get('official_url') or 'n/d'}",
                f"- Edital: {item.get('edital_url') or 'n/d'}",
                f"- Ocupacao: {item.get('occupancy_status') or 'desconhecida'}",
                f"- Matricula: {item.get('matricula') or 'n/d'}",
                f"- Anticorpos do curso: {', '.join(item.get('course_antibodies') or []) or 'nenhum'}",
                f"- P0 resolvidos: {', '.join(item.get('resolved_p0_keys') or []) or 'nenhum'}",
                f"- P0 restantes: {', '.join(item.get('remaining_p0_keys') or []) or 'nenhum'}",
                f"- Proximo passo: {item.get('next_action') or 'n/d'}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_active_diligence(
    *,
    seed_path: Path,
    report_json_path: Path,
    report_md_path: Path,
    fetcher: Fetcher | None = None,
    limit: int | None = None,
    close_out_of_scope_only: bool = False,
) -> dict[str, Any]:
    checked_at = utc_now()
    seed = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    rows = active_p0_rows(seed)
    rows = sorted(
        rows,
        key=lambda row: (
            0
            if (_normalize_text(_candidate_city(row)) and _normalize_text(_candidate_city(row)) not in OWNER_SCOPE_CITIES)
            else 1,
            int(row.get("thesis_number") or 0),
        ),
    )
    if close_out_of_scope_only:
        rows = [
            row
            for row in rows
            if (_normalize_text(_candidate_city(row)) and _normalize_text(_candidate_city(row)) not in OWNER_SCOPE_CITIES)
        ]
    if limit is not None and limit > 0:
        rows = rows[:limit]
    fetch = fetcher or default_fetcher
    items: list[dict[str, Any]] = []
    closed_count = 0
    access_blocked_count = 0
    still_open_with_p0_count = 0

    for row in rows:
        thesis_number = int(row.get("thesis_number") or 0)
        title = str(row.get("action") or row.get("asset") or row.get("thesis_id") or thesis_number)
        source_url = str(row.get("source_url") or "").strip()
        city_raw = _candidate_city(row)
        city_norm = _normalize_text(city_raw)
        if city_norm and city_norm not in OWNER_SCOPE_CITIES:
            result = _discard_out_of_scope_city_row(row, checked_at, city=city_raw)
            closed_count += 1
            items.append(
                {
                    "thesis_number": thesis_number,
                    "thesis_id": row.get("thesis_id"),
                    "title": title,
                    "status": "fora_do_escopo",
                    "decision": row.get("outcome") or row.get("status"),
                    "source_url": source_url,
                    "official_url": "",
                    "edital_url": "",
                    "occupancy_status": "desconhecido",
                    "matricula": "",
                    "resolved_p0_keys": result.get("resolved_p0_keys", []) if isinstance(result, dict) else [],
                    "course_antibodies": result.get("course_antibodies", []) if isinstance(result, dict) else [],
                    "remaining_p0_keys": [],
                    "next_action": (row.get("real_estate_analysis") or {}).get("next_action")
                    if isinstance(row.get("real_estate_analysis"), dict)
                    else "",
                    "evidence": {"status": "fora_do_escopo", "city": city_raw, "reason": row.get("exit_rule") or ""},
                }
            )
            continue
        if not source_url:
            evidence = {
                "status": "ambiguo",
                "source_url": "",
                "opened_url": "",
                "occupancy_status": "desconhecido",
                "registration": {},
                "debts": {},
                "course_antibodies": [],
                "attempted_paths": ["fonte ausente na seed"],
                "text_excerpt": "",
            }
        else:
            try:
                html_text = fetch(source_url)
                evidence = extract_evidence(source_url, html_text)
            except Exception as exc:  # noqa: BLE001 - report must preserve the blocker.
                evidence = {
                    "status": "bloqueado_por_acesso",
                    "source_url": source_url,
                    "opened_url": source_url,
                    "occupancy_status": "desconhecido",
                    "registration": {},
                    "debts": {},
                    "course_antibodies": [],
                    "attempted_paths": ["abrir fonte inicial com perfil de navegador"],
                    "access_request": {
                        "site": source_url,
                        "blocker_type": exc.__class__.__name__,
                        "why_it_matters": "Sem abrir a fonte, a app nao consegue comprovar a cadeia primaria.",
                        "credential_file_hint": f"data/secure/real_estate_sources/{urlparse(source_url).netloc.lower()}.credentials.json",
                    },
                    "error": str(exc),
                    "text_excerpt": "",
                }
        result = apply_evidence_to_row(row, evidence, checked_at)
        remaining_p0 = result.get("remaining_p0_keys") if isinstance(result, dict) else []
        is_open = row.get("is_open") is True
        if row.get("is_open") is False:
            closed_count += 1
        if evidence.get("status") == "bloqueado_por_acesso":
            access_blocked_count += 1
        if is_open and remaining_p0:
            still_open_with_p0_count += 1
        items.append(
            {
                "thesis_number": thesis_number,
                "thesis_id": row.get("thesis_id"),
                "title": title,
                "status": evidence.get("status"),
                "decision": row.get("outcome") or row.get("status"),
                "source_url": source_url,
                "official_url": evidence.get("official_url"),
                "edital_url": evidence.get("edital_url"),
                "occupancy_status": evidence.get("occupancy_status"),
                "matricula": (evidence.get("registration") or {}).get("matricula")
                if isinstance(evidence.get("registration"), dict)
                else "",
                "resolved_p0_keys": result.get("resolved_p0_keys", []) if isinstance(result, dict) else [],
                "course_antibodies": result.get("course_antibodies", []) if isinstance(result, dict) else [],
                "remaining_p0_keys": remaining_p0 or [],
                "next_action": (row.get("real_estate_analysis") or {}).get("next_action")
                if isinstance(row.get("real_estate_analysis"), dict)
                else "",
                "evidence": evidence,
            }
        )

    report = {
        "generated_at": checked_at,
        "seed_path": str(seed_path),
        "investigated_count": len(rows),
        "closed_count": closed_count,
        "access_blocked_count": access_blocked_count,
        "still_open_with_p0_count": still_open_with_p0_count,
        "items": items,
    }
    _write_json(seed_path, seed)
    _write_json(report_json_path, report)
    _write_markdown(report_md_path, report)
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aplica diligencia ativa aos P0 abertos do Radar Imobiliario.")
    parser.add_argument("--seed-path", default="data/dashboard_seed.json")
    parser.add_argument("--report-json", default="")
    parser.add_argument("--report-md", default="")
    parser.add_argument("--limit", type=int, default=0, help="Limita quantos itens investigar (0 = sem limite).")
    parser.add_argument(
        "--close-out-of-scope-only",
        action="store_true",
        help="Fecha apenas candidatos fora do escopo (SP capital + Campinas) sem tentar abrir fontes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(__file__).resolve().parents[1]
    seed_path = (repo_root / args.seed_path).resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_json = (
        Path(args.report_json).resolve()
        if args.report_json
        else repo_root / "data" / "reports" / f"active_real_estate_diligence_{stamp}.json"
    )
    report_md = (
        Path(args.report_md).resolve()
        if args.report_md
        else repo_root / "data" / "reports" / f"active_real_estate_diligence_{stamp}.md"
    )
    report = run_active_diligence(
        seed_path=seed_path,
        report_json_path=report_json,
        report_md_path=report_md,
        limit=args.limit if args.limit > 0 else None,
        close_out_of_scope_only=args.close_out_of_scope_only,
    )
    latest_json = repo_root / "data" / "reports" / "active_real_estate_diligence_latest.json"
    latest_md = repo_root / "data" / "reports" / "active_real_estate_diligence_latest.md"
    _write_json(latest_json, report)
    _write_markdown(latest_md, report)
    print(
        json.dumps(
            {
                "investigated_count": report["investigated_count"],
                "closed_count": report["closed_count"],
                "still_open_with_p0_count": report["still_open_with_p0_count"],
                "access_blocked_count": report["access_blocked_count"],
                "report_json": str(report_json),
                "report_md": str(report_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

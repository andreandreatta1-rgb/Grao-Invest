from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Any


PROCESS_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
MATRICULA_RE = re.compile(r"\bmatr[ií]cula(?:\s+imobili[aá]ria)?\s*(?:n[ºo.]*)?\s*([\d.]+)", re.IGNORECASE)
REGISTRY_RE = re.compile(r"\b(\d{1,2}\s*[ºo]?\s*CRI(?:/SP)?|cart[oó]rio\s+[^.;,]+)", re.IGNORECASE)
TAXPAYER_RE = re.compile(r"\b(?:contribuinte|cadastro|sql)\s*(?:n[ºo.]*)?\s*([\d.\-/]+)", re.IGNORECASE)
UNIT_RE = re.compile(r"\b(?:apto|apartamento|unidade|casa|lote|sala|conjunto)\s*(?:n[ºo.]*)?\s*([A-Z]?\d+[A-Z]?)\b", re.IGNORECASE)
CONDO_RE = re.compile(
    r"\b(?:condom[ií]nio|edif[ií]cio|ed\.)\s+([A-Za-zÀ-ÿ0-9 .'/-]+?)(?=,|\.|;|\s+Rua|\s+Avenida|\s+Av\.|\s+area|\s+área|$)",
    re.IGNORECASE,
)


def _text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _combined_text(payload: dict[str, Any]) -> str:
    values = [
        _text(payload, "title"),
        _text(payload, "street", "address", "endereco"),
        _text(payload, "building", "condominium"),
        _text(payload, "origin", "strategy"),
        _text(payload, "listing_description", "description", "auction_description", "notes"),
        _text(payload, "source_validation_reason"),
    ]
    return " ".join(value for value in values if value)


def _first_match(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return str(match.group(1) if match.groups() else match.group(0)).strip(" .;,-")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip(" .;,-")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _quoted(value: str) -> str:
    value = value.strip().strip('"')
    return f'"{value}"' if value else ""


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _source_role_from_url(url: str) -> str:
    host = _domain(url)
    if any(marker in host for marker in ("tjsp", "webleiloes", "portalzuk", "caixa", "bradesco", "santander", "frazaoleiloes", "proleilao")):
        return "primary_legal"
    if any(marker in host for marker in ("leeilon", "leilaoimovel", "spy", "zap", "vivareal", "chavesnamao", "quintoandar", "imovelweb")):
        return "aggregator_clue"
    return "source_clue" if host else ""


def build_asset_identity(payload: dict[str, Any]) -> dict[str, Any]:
    text = _combined_text(payload)
    street = _text(payload, "street", "address", "endereco")
    city = _text(payload, "city", "cidade", "municipality", "municipio")
    neighborhood = _text(payload, "neighborhood", "bairro", "district")
    condominium = _text(payload, "condominium", "building") or _first_match(CONDO_RE, text)
    unit = _text(payload, "unit", "apartment", "apartment_number") or _first_match(UNIT_RE, text)
    process_number = _text(payload, "process_number", "judicial_process_number") or _first_match(PROCESS_RE, text)
    matricula = _text(payload, "matricula", "registration_number") or _first_match(MATRICULA_RE, text)
    registry = _text(payload, "registry", "cartorio") or _first_match(REGISTRY_RE, text)
    taxpayer_id = _text(payload, "taxpayer_id", "contribuinte") or _first_match(TAXPAYER_RE, text)
    area = _text(payload, "private_area_m2", "privateAreaM2", "area_m2")
    source_url = _text(payload, "source_url", "sourceUrl")

    full_address = " / ".join(_dedupe([city, neighborhood, street]))
    address_variants = _dedupe([
        street,
        re.sub(r"\s+-\s+(?:Apto|Apartamento|Casa|Unidade|Sala).*$", "", street, flags=re.IGNORECASE),
        full_address,
        f"{street} {neighborhood}" if street and neighborhood else "",
        f"{street} {city}" if street and city else "",
    ])

    return {
        "full_address": full_address,
        "address_variants": address_variants,
        "city": city,
        "neighborhood": neighborhood,
        "street": street,
        "condominium": condominium,
        "unit": unit,
        "process_number": process_number,
        "matricula": matricula,
        "registry": registry,
        "taxpayer_id": taxpayer_id,
        "private_area_m2": area,
        "source_domain": _domain(source_url),
    }


def _query(role: str, query: str, reason: str, source_hint: str = "") -> dict[str, str]:
    return {
        "role": role,
        "query": query,
        "reason": reason,
        "source_hint": source_hint,
    }


def build_lateral_search_queries(identity: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
    street = str(identity.get("street") or "")
    address = str((identity.get("address_variants") or [street])[0] or street)
    condominium = str(identity.get("condominium") or "")
    unit = str(identity.get("unit") or "")
    process_number = str(identity.get("process_number") or "")
    matricula = str(identity.get("matricula") or "")
    registry = str(identity.get("registry") or "")
    area = str(identity.get("private_area_m2") or "")
    neighborhood = str(identity.get("neighborhood") or "")
    city = str(identity.get("city") or "")
    source_origin = _text(payload, "origin", "strategy")

    queries = [
        _query("condition_photos", f"{_quoted(address)} fotos internas", "procurar estado de conservacao e reforma", "Google/Bing/imagens"),
        _query("condition_photos", f"{_quoted(address)} Leeilon", "achar espelhos com fotos ou ficha visual", "Leeilon"),
        _query("aggregator_clue", f"{_quoted(address)} leilao", "achar espelhos do mesmo lote em agregadores", "agregadores"),
        _query("market_comparable", f"{_quoted(address)} venda", "buscar comparaveis do mesmo endereco ou rua", "portais de venda"),
    ]
    if unit and address:
        queries.insert(0, _query("primary_legal", f"{_quoted(address)} {_quoted(unit)}", "confirmar que a fonte lateral e a mesma unidade", "busca geral"))
    if condominium:
        queries.extend([
            _query("condition_photos", f"{_quoted(condominium)} {_quoted(neighborhood)} fotos", "validar fachada, padrao do predio e fotos internas", "imagens/portais"),
            _query("market_comparable", f"{_quoted(condominium)} {_quoted(city)} venda", "comparar com unidades do mesmo condominio", "portais de venda"),
            _query("aggregator_clue", f"{_quoted(condominium)} leilao", "achar leiloeiro oficial ou agregadores do ativo", "busca geral"),
        ])
    if process_number:
        queries.append(_query("primary_legal", _quoted(process_number), "seguir a cadeia judicial/processual", "TJSP/leiloeiro"))
    if matricula:
        registry_query = f" {_quoted(registry)}" if registry else ""
        queries.append(_query("primary_legal", f"matricula {_quoted(matricula)}{registry_query}", "confirmar registro, onus e identidade do ativo", "cartorio/leiloeiro"))
    if source_origin:
        queries.append(_query("primary_legal", f"{_quoted(source_origin)} {_quoted(address)}", "ligar origem/leiloeiro ao ativo", "fonte oficial"))
    if area and neighborhood:
        queries.append(_query("market_comparable", f"{_quoted(neighborhood)} {_quoted(area + 'm2')} venda apartamento", "buscar faixa de saida por metragem equivalente", "portais de venda"))

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in queries:
        query = re.sub(r"\s+", " ", item["query"]).strip()
        if len(query.replace('"', "").strip()) < 4:
            continue
        key = (item["role"], query.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append({**item, "query": query})
    return result[:10]


def _visual_evidence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("visual_evidence") or payload.get("visualEvidence")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _sale_comparables(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("sale_comparables") or payload.get("saleComparables")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def build_asset_first_diligence(payload: dict[str, Any]) -> dict[str, Any]:
    identity = build_asset_identity(payload)
    source_url = _text(payload, "source_url", "sourceUrl")
    source_validation = payload.get("source_validation") if isinstance(payload.get("source_validation"), dict) else {}
    source_status = (_text(payload, "source_validation_status") or str(source_validation.get("status") or "")).lower()
    visual_evidence = _visual_evidence(payload)
    sale_comparables = _sale_comparables(payload)

    existing_sources: list[dict[str, str]] = []
    if source_url:
        existing_sources.append({
            "role": _source_role_from_url(source_url) or "source_clue",
            "source": _domain(source_url) or "source_url",
            "source_url": source_url,
            "status": source_status or "unchecked",
        })
    for item in visual_evidence:
        url = str(item.get("source_url") or item.get("sourceUrl") or "")
        existing_sources.append({
            "role": str(item.get("role") or "condition_photos"),
            "source": str(item.get("source") or _domain(url) or "visual"),
            "source_url": url,
            "status": str(item.get("evidence_type") or item.get("status") or "pending_capture"),
        })
    for item in sale_comparables:
        url = str(item.get("source_url") or item.get("sourceUrl") or item.get("url") or "")
        existing_sources.append({
            "role": "market_comparable",
            "source": str(item.get("source") or item.get("origin") or _domain(url) or "comparavel"),
            "source_url": url,
            "status": str(item.get("evidence_type") or "listing"),
        })

    role_counts: dict[str, int] = {}
    for item in existing_sources:
        role = item.get("role") or "source_clue"
        role_counts[role] = role_counts.get(role, 0) + 1

    sale_comparables_count = int(payload.get("sale_comparables_count") or len(sale_comparables) or 0)
    missing_roles: list[str] = []
    if source_status != "valid" and not payload.get("has_edital"):
        missing_roles.append("primary_legal")
    if not visual_evidence and not payload.get("physical_condition_verified") and not payload.get("has_recent_photos"):
        missing_roles.append("condition_photos")
    if sale_comparables_count < 3:
        missing_roles.append("market_comparable")

    queries = build_lateral_search_queries(identity, payload)
    condition_status = _text(payload, "condition_evidence_status", "conditionEvidenceStatus")
    product_failure_signal = condition_status.startswith("user_found") or "usuario" in _text(payload, "notes").lower()
    status = "evidence_started" if existing_sources else "queries_ready"
    if product_failure_signal:
        status = "manual_source_found_app_missed"

    next_actions = []
    if "primary_legal" in missing_roles:
        next_actions.append("abrir fonte oficial por processo/matricula/leiloeiro")
    if "condition_photos" in missing_roles:
        next_actions.append("buscar fotos internas/externas pelo endereco e condominio")
    if "market_comparable" in missing_roles:
        next_actions.append("coletar 3 comparaveis do mesmo predio, rua ou raio curto")

    return {
        "status": status,
        "asset_identity": identity,
        "lateral_search_queries": queries,
        "existing_sources": existing_sources,
        "source_role_counts": role_counts,
        "missing_source_roles": missing_roles,
        "next_actions": next_actions,
        "product_failure_signal": product_failure_signal,
        "method": "asset_first",
    }

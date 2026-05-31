from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.services.real_estate_asset_first import build_asset_first_diligence


CONDO_DEBT_EXIT_THRESHOLD_BRL = 500_000.0
SALE_COMPARABLE_PREFIX = "[SALE_COMPARABLE] "


def _float(payload: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = payload.get(key, default)
    if value is None or value == "":
        return default
    return float(value)


def _int(payload: dict[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    if value is None or value == "":
        return default
    return int(value)


def _bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "yes", "on"}
    return bool(value)


def _text(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _normalize_text(value: str) -> str:
    if "Ã" in value or "Â" in value:
        try:
            repaired = value.encode("latin-1").decode("utf-8")
        except Exception:
            repaired = value
        if repaired and (repaired.count("Ã") + repaired.count("Â")) < (value.count("Ã") + value.count("Â")):
            value = repaired
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _number_from_text(value: str) -> float:
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _combined_text(payload: dict[str, Any], *keys: str) -> str:
    return " ".join(_text(payload, key) for key in keys if _text(payload, key))


def _auction_like_payload(payload: dict[str, Any]) -> bool:
    text = _normalize_text(
        _combined_text(
            payload,
            "origin",
            "source_origin",
            "strategy",
            "title",
            "property_type",
            "auction_modality",
            "auctionModality",
            "source_url",
            "listing_description",
            "auction_description",
        )
    )
    return any(
        marker in text
        for marker in (
            "arremat",
            "banco do brasil",
            "caixa",
            "extrajudicial",
            "judicial",
            "leilao",
            "leiloeiro",
            "leiloes",
            "licitacao",
            "praca",
        )
    )


def _has_approved_eviction_plan(payload: dict[str, Any]) -> bool:
    plan_text = _normalize_text(
        _combined_text(
            payload,
            "legal_plan",
            "legalPlan",
            "eviction_plan",
            "evictionPlan",
            "possession_plan",
            "possessionPlan",
        )
    )
    return any(
        marker in plan_text
        for marker in (
            "acordo de desocupacao",
            "desocupacao acordada",
            "imissao planejada",
            "plano juridico aprovado",
            "posse planejada",
        )
    )


def _first_float(payload: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        return float(value)
    return default


def _round_to_increment(value: float, increment: float = 5_000.0) -> float:
    if value <= 0 or increment <= 0:
        return 0.0
    return round(round(value / increment) * increment, 2)


def _median(values: list[float]) -> float:
    ordered = sorted(value for value in values if value > 0)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _raw_sale_comparables(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "sale_comparables",
        "saleComparables",
        "sale_comparable_evidence",
        "saleComparableEvidence",
        "valuation_comparables",
        "valuationComparables",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    note_comparables: list[dict[str, Any]] = []
    for line in _text(payload, "notes").splitlines():
        if not line.startswith(SALE_COMPARABLE_PREFIX):
            continue
        try:
            parsed = json.loads(line[len(SALE_COMPARABLE_PREFIX) :])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            note_comparables.append(parsed)
        elif isinstance(parsed, list):
            note_comparables.extend(item for item in parsed if isinstance(item, dict))
    if note_comparables:
        return note_comparables
    return []


def _comparable_valuation_scope(item: dict[str, Any]) -> str:
    evidence_text = _normalize_text(
        " ".join(
            str(item.get(key) or "")
            for key in ("evidence_type", "evidenceType", "note", "description")
        )
    )
    if any(
        token in evidence_text
        for token in (
            "same_address",
            "same address",
            "mesmo_endereco",
            "mesmo endereco",
            "mesma_matricula",
            "mesma matricula",
            "same_building",
            "same_condominium",
            "mesmo_condominio",
            "mesmo condominio",
        )
    ):
        return "same_address"
    if any(
        token in evidence_text
        for token in (
            "same_street",
            "same street",
            "mesma_rua",
            "mesma rua",
        )
    ):
        return "same_street"
    if any(
        token in evidence_text
        for token in (
            "neighborhood",
            "same_neighborhood",
            "same neighborhood",
            "mesmo_bairro",
            "mesmo bairro",
        )
    ):
        return "neighborhood"
    return "market_listing"


def _scope_priority(scope: str) -> int:
    return {
        "same_address": 3,
        "same_street": 2,
        "neighborhood": 1,
        "market_listing": 0,
    }.get(scope, 0)


def _preferred_sale_comparable_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    if not entries:
        return [], ""
    best_priority = max(
        _scope_priority(str(entry.get("valuation_scope") or ""))
        for entry in entries
    )
    selected = [
        entry
        for entry in entries
        if _scope_priority(str(entry.get("valuation_scope") or "")) == best_priority
    ]
    scope = str(selected[0].get("valuation_scope") or "market_listing") if selected else "market_listing"
    return selected, scope


def _sale_comparable_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in _raw_sale_comparables(payload):
        price = _first_float(
            item,
            "price",
            "asking_price",
            "askingPrice",
            "sale_price",
            "salePrice",
            "value",
        )
        if price <= 0:
            continue
        area = _first_float(
            item,
            "area_m2",
            "areaM2",
            "private_area_m2",
            "privateAreaM2",
            "area",
        )
        price_per_m2 = price / area if area > 0 else 0.0
        evidence_type = _text(item, "evidence_type") or _text(item, "evidenceType") or "asking_listing"
        note = _text(item, "note") or _text(item, "description")
        entries.append(
            {
                "source": _text(item, "source") or _text(item, "origin"),
                "source_url": _text(item, "source_url") or _text(item, "sourceUrl") or _text(item, "url"),
                "price": round(price, 2),
                "area_m2": round(area, 2),
                "price_per_m2": round(price_per_m2, 2),
                "evidence_type": evidence_type,
                "valuation_scope": _comparable_valuation_scope(
                    {
                        **item,
                        "evidence_type": evidence_type,
                        "note": note,
                    }
                ),
                "note": note,
            }
        )
    return entries


def _sale_valuation_from_comparables(
    payload: dict[str, Any],
    *,
    private_area_m2: float,
) -> dict[str, Any] | None:
    entries = _sale_comparable_entries(payload)
    if not entries:
        return None
    selected_entries, valuation_scope = _preferred_sale_comparable_entries(entries)
    if not selected_entries:
        return None
    price_per_m2_values = [
        entry["price_per_m2"]
        for entry in selected_entries
        if entry.get("price_per_m2", 0.0) > 0
    ]
    min_price_per_m2 = min(price_per_m2_values) if price_per_m2_values else 0.0
    max_price_per_m2 = max(price_per_m2_values) if price_per_m2_values else 0.0
    median_price_per_m2 = _median(price_per_m2_values) if price_per_m2_values else 0.0
    spread_ratio = (max_price_per_m2 / min_price_per_m2) if min_price_per_m2 > 0 else 0.0
    spread_pct = (
        (max_price_per_m2 - min_price_per_m2) / median_price_per_m2 * 100.0
        if median_price_per_m2 > 0
        else 0.0
    )
    quality_warning = bool(len(price_per_m2_values) >= 3 and spread_ratio >= 1.8)
    normalized_prices = [
        entry["price_per_m2"] * private_area_m2
        if private_area_m2 > 0 and entry["price_per_m2"] > 0
        else entry["price"]
        for entry in selected_entries
    ]
    base_sale_price = _round_to_increment(_median(normalized_prices))
    if base_sale_price <= 0:
        return None
    conservative_discount_pct = _first_float(
        payload,
        "sale_comparable_conservative_discount_pct",
        "saleComparableConservativeDiscountPct",
        default=8.0,
    )
    optimistic_premium_pct = _first_float(
        payload,
        "sale_comparable_optimistic_premium_pct",
        "saleComparableOptimisticPremiumPct",
        default=8.0,
    )
    return {
        "source": "sale_comparables",
        "sale_comparables_count": len(entries),
        "used_comparables_count": len(selected_entries),
        "excluded_lower_priority_comparables_count": len(entries) - len(selected_entries),
        "valuation_scope": valuation_scope,
        "base_sale_price": base_sale_price,
        "conservative_sale_price": _round_to_increment(
            base_sale_price * (1.0 - conservative_discount_pct / 100.0)
        ),
        "optimistic_sale_price": _round_to_increment(
            base_sale_price * (1.0 + optimistic_premium_pct / 100.0)
        ),
        "median_price_per_m2": round(median_price_per_m2, 2),
        "price_per_m2_min": round(min_price_per_m2, 2),
        "price_per_m2_max": round(max_price_per_m2, 2),
        "price_per_m2_spread_ratio": round(spread_ratio, 3),
        "price_per_m2_spread_pct": round(spread_pct, 2),
        "quality_warning": quality_warning,
        "caveat": (
            "Comparavel de anuncio, nao venda realizada; exige mais amostra antes de virar conviccao."
        ),
        "selected_comparables": selected_entries,
        "comparables": entries,
    }


def _auction_listing_reading(payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = _combined_text(
        payload,
        "title",
        "strategy",
        "property_type",
        "listing_description",
        "auction_description",
        "raw_description",
        "description",
        "notes",
        "local_demand_notes",
        "source_validation_reason",
    )
    normalized = _normalize_text(raw_text)
    source_text = _normalize_text(
        _combined_text(payload, "origin", "strategy", "source_url", "source_validation_reason")
    )
    if not normalized and not source_text:
        return {}

    reading: dict[str, Any] = {}
    private_area = re.search(
        r"area\s+(?:real\s+)?privativa\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m",
        normalized,
    )
    useful_area = re.search(
        r"area\s+util(?:\s+ou\s+privativa)?\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m",
        normalized,
    )
    useful_area_de = re.search(
        r"(?:areas?:\s*)?util\s+de\s+([0-9]+(?:[.,][0-9]+)?)\s*m",
        normalized,
    )
    total_area = re.search(r"area\s+total\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m", normalized)
    common_area = re.search(r"area\s+comum\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*m", normalized)
    if private_area:
        reading["private_area_m2"] = round(_number_from_text(private_area.group(1)), 2)
    elif useful_area:
        reading["private_area_m2"] = round(_number_from_text(useful_area.group(1)), 2)
    elif useful_area_de:
        reading["private_area_m2"] = round(_number_from_text(useful_area_de.group(1)), 2)
    if common_area:
        reading["common_area_m2"] = round(_number_from_text(common_area.group(1)), 2)
    if total_area:
        reading["total_area_m2"] = round(_number_from_text(total_area.group(1)), 2)

    if "desocupado" in normalized:
        reading["occupancy_status"] = "desocupado"
    elif "ocupado" in normalized:
        reading["occupancy_status"] = "ocupado"
    legal_ownership_blockers: list[str] = []
    ownership_text = re.sub(
        r"[-_/]+",
        " ",
        " ".join(text for text in (normalized, source_text) if text),
    )
    if (
        "direito sobre" in ownership_text
        or "direitos sobre" in ownership_text
        or "direito aquisitivo" in ownership_text
        or "direitos aquisitivos" in ownership_text
        or "cessao de direitos" in ownership_text
        or "cessao dos direitos" in ownership_text
        or re.search(r"\bdireitos?\s+(?:apto|apartamento|imovel|casa|unidade)\b", ownership_text)
    ):
        reading["rights_over_asset"] = True
        legal_ownership_blockers.append("direitos sobre")
    if re.search(r"\b(fracao|parte\s+ideal|quota|quotas|quinhao)\b", normalized):
        reading["fractional_interest"] = True
        legal_ownership_blockers.append("fracao ideal")
    if "nua propriedade" in normalized:
        reading["bare_ownership"] = True
        legal_ownership_blockers.append("nua propriedade")
    if legal_ownership_blockers:
        reading["legal_ownership_blockers"] = list(dict.fromkeys(legal_ownership_blockers))
    if "desocupacao" in normalized and (
        "por conta do adquirente" in normalized or "conta do adquirente" in normalized
    ):
        reading["buyer_responsible_for_eviction"] = True
    if "vendedor se exime" in normalized or "exime de qualquer responsabilidade" in normalized:
        reading["seller_disclaims_due_diligence"] = True
    if "cabe exclusivamente ao interessado" in normalized:
        reading["buyer_responsible_for_due_diligence"] = True
    if "art. 30" in normalized and "lei 9.514" in normalized:
        reading["fiduciary_sale_eviction_law"] = "art_30_lei_9514"
    if "extrajudicial" in normalized or "alienacao fiduciaria" in normalized:
        reading["auction_modality"] = "extrajudicial"
    elif "judicial" in normalized or "vara" in normalized or "processo" in normalized:
        reading["auction_modality"] = "judicial"
    elif "venda direta" in normalized:
        reading["auction_modality"] = "venda_direta"
    elif "caixa" in normalized or "banco do brasil" in normalized:
        reading["auction_modality"] = "banco"
    if _has_ambiguous_debt_responsibility(normalized):
        reading["debt_responsibility_ambiguous"] = True
    if _has_fiduciary_auction_nullity_action(normalized):
        reading["fiduciary_auction_nullity_action"] = True
        process_match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", normalized)
        if process_match:
            reading["judicial_process_number"] = process_match.group(0)
    has_payment_channel = "pix" in normalized or "boleto" in normalized
    if not has_payment_channel and "conta" in normalized:
        has_payment_channel = any(
            marker in normalized
            for marker in (
                "conta bancaria",
                "conta banc",
                "conta corrente",
                "agencia",
                "deposit",
                "transfer",
                "pagamento",
                "pagamentos",
            )
        )
    has_payment_risk_marker = any(
        marker in normalized
        for marker in (
            "terceiro",
            "fora do edital",
            "site falso",
            "nao oficial",
        )
    )
    anti_fraud_warning = bool(
        re.search(r"\b(?:nao|nunca|jamais)\s+(?:efetue|realize|faca|pague)\b", normalized)
        or re.search(r"\b(?:nao|nunca|jamais)\s+realize\s+nenhum\s+pagamento\b", normalized)
        or re.search(r"\bnao\s+efetue\s+pagamentos?\b", normalized)
    )
    if has_payment_channel and has_payment_risk_marker and not anti_fraud_warning:
        reading["suspicious_payment_instruction"] = True

    mentions_auction = "leilao" in source_text or "praca" in normalized
    mentions_market_reference = (
        "valor de referencia publicado" in normalized
        or "1a praca" in normalized
        or "primeira praca" in normalized
        or "valor do imovel" in normalized
    )
    if mentions_auction and mentions_market_reference:
        reading["auction_reference_not_resale"] = True
    return reading


def _auction_reference_value_evidence(
    payload: dict[str, Any],
    *,
    market_value: float,
    estimated_sale_base: float,
    sale_comparables_count: int,
    listing_reading: dict[str, Any],
) -> dict[str, Any]:
    if sale_comparables_count >= 3:
        return {}
    if _sale_comparable_entries(payload):
        return {}
    if not listing_reading.get("auction_reference_not_resale"):
        return {}
    reference_value = max(market_value, estimated_sale_base)
    if reference_value <= 0:
        return {}
    return {
        "source": "auction_reference_value",
        "status": "pendente",
        "risk_flag": "auction_reference_not_resale",
        "sale_comparables_count": sale_comparables_count,
        "base_sale_price": round(reference_value, 2),
        "caveat": (
            "Valor de leilao/1a praca ou avaliacao nao comprova revenda; precisa ser "
            "substituido por comparaveis reais do ativo."
        ),
        "required_action": (
            "Buscar anuncios ou vendas equivalentes por endereco, area privativa e vaga antes "
            "de manter a tese ativa."
        ),
    }


def _has_fiduciary_auction_nullity_action(normalized: str) -> bool:
    nullity_terms = (
        "acao declaratoria de nulidade",
        "acao anulatoria",
        "anulacao do leilao",
        "anulacao de leilao",
        "nulidade da consolidacao",
        "nulidade dos leiloes",
        "nulidade do leilao",
        "suspensao do leilao",
    )
    auction_terms = (
        "consolidacao da propriedade fiduciaria",
        "propriedade fiduciaria",
        "leilao extrajudicial",
        "leiloes extrajudiciais",
    )
    if any(term in normalized for term in nullity_terms) and any(
        term in normalized for term in auction_terms
    ):
        return True
    return "liminar" in normalized and "leilao" in normalized and "extrajudicial" in normalized


def _has_ambiguous_debt_responsibility(normalized: str) -> bool:
    debt_terms = (
        "debito",
        "debitos",
        "divida",
        "dividas",
        "obrigacao",
        "obrigacoes",
        "saldo devedor",
        "iptu",
        "condominio",
        "onus",
        "tributo",
        "tributos",
    )
    if not any(term in normalized for term in debt_terms):
        return False

    ambiguity_terms = (
        "nao fala explicitamente",
        "nao informa",
        "nao consta",
        "sem informacao",
        "responsabilidade nao definida",
        "responsabilidade a confirmar",
        "debitos a confirmar",
        "duvidas e esclarecimentos",
        "solicitar informacao",
        "solicitar esclarecimento",
    )
    if any(term in normalized for term in ambiguity_terms):
        return True

    explicit_resolution_terms = (
        "serao quitados com o produto da arrematacao",
        "serao pagos com o produto da arrematacao",
        "sub-rogam-se no preco",
        "subrogam-se no preco",
        "nao cabera ao arrematante",
        "arrematante nao responde",
        "comprador nao responde",
        "adquirente nao responde",
        "responde apenas pelas despesas vencidas apos",
        "responde apenas a partir",
    )
    if any(term in normalized for term in explicit_resolution_terms):
        return False

    explicit_assumption_terms = (
        "arrematante assumira",
        "arrematante responde",
        "cabera ao arrematante",
        "responsabilidade do arrematante",
        "por conta do arrematante",
        "comprador assumira",
        "adquirente assumira",
        "por conta do adquirente",
    )
    if any(term in normalized for term in explicit_assumption_terms):
        return False

    return False


def _weak_neighborhood_benchmark_evidence(
    payload: dict[str, Any],
    *,
    purchase_price: float,
    private_area_m2: float,
    market_value: float,
    estimated_sale_base: float,
    sale_comparables_count: int,
) -> dict[str, Any]:
    reference_value = max(market_value, estimated_sale_base)
    if purchase_price <= 0 or reference_value <= 0:
        return {}
    if sale_comparables_count >= 3:
        return {}
    if _sale_comparable_entries(payload):
        return {}

    discount_pct = (reference_value - purchase_price) / reference_value * 100.0
    if discount_pct < 30:
        return {}

    asking_price_per_m2 = purchase_price / private_area_m2 if private_area_m2 > 0 else 0.0
    reference_price_per_m2 = reference_value / private_area_m2 if private_area_m2 > 0 else 0.0
    notes = _text(payload, "notes").lower()
    benchmark_mentions = any(
        term in notes
        for term in (
            "bairro",
            "fipezap",
            "ranking",
            "preco medio",
            "preco/m2",
            "r$/m2",
            "m2",
        )
    )
    if private_area_m2 <= 0 and not benchmark_mentions:
        return {}

    return {
        "source": "market_value_estimate",
        "status": "pendente",
        "risk_flag": "weak_neighborhood_benchmark",
        "sale_comparables_count": sale_comparables_count,
        "base_sale_price": round(reference_value, 2),
        "asking_price_per_m2": round(asking_price_per_m2, 2),
        "reference_price_per_m2": round(reference_price_per_m2, 2),
        "discount_pct": round(discount_pct, 2),
        "caveat": (
            "Valor de saida parece vir de benchmark agregado de bairro; nao usar como "
            "desconto real sem comparaveis do mesmo predio ou equivalentes."
        ),
        "required_action": (
            "Validar valor de saida com 3 comparaveis equivalentes antes de calcular teto."
        ),
    }


def _risk_from_text(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"critico", "critica", "critical", "reprovado", "reprovada", "bloqueado"}:
        return "critico"
    if normalized in {"alto", "alta", "high"}:
        return "alto"
    if normalized in {"medio", "media", "medium"}:
        return "medio"
    if normalized in {"baixo", "baixa", "low", "ok"}:
        return "baixo"
    return ""


def _local_buyer_demand_evidence(
    payload: dict[str, Any],
    *,
    private_area_m2: float,
    purchase_price: float,
    estimated_sale_base: float,
    sale_comparables_count: int,
    rent_comparables_count: int,
) -> dict[str, Any]:
    explicit_risk = _risk_from_text(
        _text(payload, "local_demand_risk")
        or _text(payload, "localDemandRisk")
        or _text(payload, "buyer_demand_risk")
        or _text(payload, "buyerDemandRisk")
    )
    explicit_score = _first_float(
        payload,
        "local_demand_score",
        "localDemandScore",
        "buyer_demand_score",
        "buyerDemandScore",
        default=-1.0,
    )

    city = _text(payload, "city")
    neighborhood = _text(payload, "neighborhood")
    property_type = _text(payload, "property_type")
    title = _text(payload, "title")
    notes = _text(payload, "notes")
    local_notes = (
        _text(payload, "local_demand_notes")
        or _text(payload, "localDemandNotes")
        or _text(payload, "street_liquidity_evidence")
        or _text(payload, "streetLiquidityEvidence")
    )
    text = " ".join([city, neighborhood, property_type, title, notes, local_notes]).lower()

    is_apartment = "apart" in property_type.lower() or "apto" in text
    is_morumbi_area = any(term in text for term in ("morumbi", "vila andrade", "piazza morumbi"))
    large_unit = private_area_m2 >= 180
    high_ticket = purchase_price >= 700_000 or estimated_sale_base >= 900_000
    weak_sale_proof = sale_comparables_count < 3
    weak_rent_proof = rent_comparables_count < 3

    inferred_risk = ""
    signals: list[str] = []
    if is_morumbi_area and is_apartment and large_unit and high_ticket and weak_sale_proof:
        inferred_risk = "critico"
        signals.extend(
            [
                "Morumbi/Vila Andrade exige prova micro de comprador, nao apenas m2 barato.",
                "Apartamento grande e ticket alto reduzem o universo de compradores.",
                "Sem 3 comparaveis equivalentes, a saida fica especulativa.",
            ]
        )
    elif is_apartment and large_unit and high_ticket and weak_sale_proof:
        inferred_risk = "alto"
        signals.extend(
            [
                "Apartamento grande e ticket alto pedem comprador mapeado antes da diligencia pesada.",
                "Sem 3 comparaveis equivalentes, a liquidez local ainda nao esta provada.",
            ]
        )
    elif explicit_score >= 0 and explicit_score < 40:
        inferred_risk = "critico"
        signals.append("Score explicito de demanda local abaixo de 40/100.")
    elif explicit_score >= 0 and explicit_score < 60:
        inferred_risk = "alto"
        signals.append("Score explicito de demanda local abaixo de 60/100.")

    risk_level = explicit_risk or inferred_risk
    if not risk_level:
        return {}

    if not signals and local_notes:
        signals.append(local_notes)
    if weak_sale_proof:
        signals.append(f"{sale_comparables_count}/3 comparaveis de venda equivalentes.")
    if weak_rent_proof and risk_level in {"critico", "alto"}:
        signals.append(f"{rent_comparables_count}/3 comparaveis de aluguel para plano B.")

    status_label = {
        "critico": "Demanda local reprovada",
        "alto": "Demanda local pendente",
        "medio": "Demanda local a validar",
        "baixo": "Demanda local aceitavel",
    }.get(risk_level, "Demanda local a validar")
    buyer_profile = (
        _text(payload, "buyer_profile")
        or _text(payload, "buyerProfile")
        or (
            "Comprador de alto ticket para apartamento grande; publico menor e sensivel a "
            "seguranca, condominio, acesso e oferta concorrente."
            if risk_level in {"critico", "alto"}
            else "Publico comprador a validar por comparaveis de venda e aluguel."
        )
    )
    caveat = (
        _text(payload, "local_demand_caveat")
        or _text(payload, "localDemandCaveat")
        or (
            "Preco por m2 barato nao compensa se o comprador final evita a rua, o predio "
            "ou a micro-regiao."
            if risk_level == "critico"
            else "Antes de avancar, provar que existe comprador real nessa faixa e nesse raio."
        )
    )
    required_action = (
        _text(payload, "local_demand_required_action")
        or _text(payload, "localDemandRequiredAction")
        or (
            "Fechar o candidato e registrar aprendizado; so reabrir com 3 vendas equivalentes, "
            "oferta concorrente mapeada e corretor confirmando liquidez da rua/predio."
            if risk_level == "critico"
            else "Buscar 3 vendas equivalentes no mesmo predio ou raio curto e validar oferta concorrente."
        )
    )

    return {
        "status": "reprovado" if risk_level == "critico" else "pendente",
        "risk_level": risk_level,
        "status_label": status_label,
        "buyer_profile": buyer_profile,
        "signals": list(dict.fromkeys(signal for signal in signals if signal)),
        "sale_comparables_count": sale_comparables_count,
        "rent_comparables_count": rent_comparables_count,
        "caveat": caveat,
        "required_action": required_action,
        "should_discard": risk_level == "critico",
    }


def _scenario(
    *,
    sale_price: float,
    purchase_price: float,
    acquisition_costs: float,
    renovation_budget: float,
    carrying_cost: float,
    debt_costs: float = 0.0,
    selling_commission_pct: float,
    cash_needed: float,
) -> dict[str, float]:
    commission = sale_price * selling_commission_pct / 100.0
    net_profit = sale_price - commission - purchase_price - acquisition_costs
    net_profit -= renovation_budget + carrying_cost + max(0.0, debt_costs)
    roi_pct = (net_profit / cash_needed * 100.0) if cash_needed > 0 else 0.0
    return {
        "sale_price": round(sale_price, 2),
        "net_profit": round(net_profit, 2),
        "roi_pct": round(roi_pct, 2),
    }


def _payment_terms_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("payment_terms", "paymentTerms"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for key in ("commercial_terms", "commercialTerms"):
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        for terms_key in ("payment_terms", "paymentTerms", "terms", "scenarios"):
            terms = value.get(terms_key)
            if isinstance(terms, list):
                return [item for item in terms if isinstance(item, dict)]
    return []


def _price_table_payment(*, principal: float, monthly_rate: float, installments: int) -> float:
    if principal <= 0 or installments <= 0:
        return 0.0
    if monthly_rate <= 0:
        return principal / installments
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -installments)


def _present_value_of_installments(
    *,
    initial_cash: float,
    monthly_payment: float,
    installments: int,
    monthly_discount_rate: float,
) -> float:
    if monthly_payment <= 0 or installments <= 0:
        return initial_cash
    return initial_cash + sum(
        monthly_payment / ((1 + monthly_discount_rate) ** month)
        for month in range(1, installments + 1)
    )


def _commercial_terms_analysis(
    payload: dict[str, Any],
    *,
    purchase_price: float,
) -> dict[str, Any]:
    terms = _payment_terms_from_payload(payload)
    if purchase_price <= 0 or not terms:
        return {}

    discount_rate_pct = _first_float(
        payload,
        "payment_discount_rate_monthly_pct",
        "financial_discount_rate_monthly_pct",
        default=1.0,
    )
    monthly_discount_rate = max(discount_rate_pct, 0.0) / 100.0
    scenarios: list[dict[str, Any]] = []

    for index, term in enumerate(terms):
        kind = (
            _text(term, "kind")
            or _text(term, "type")
            or _text(term, "payment_type")
            or _text(term, "paymentType")
        ).lower()
        label = _text(term, "label") or _text(term, "description") or f"Condicao {index + 1}"
        key = _text(term, "key") or f"{kind or 'payment'}_{index + 1}"

        if kind == "cash_discount":
            discount_pct = _first_float(term, "discount_pct", "discountPct", default=0.0)
            effective_purchase_price = purchase_price * (1 - discount_pct / 100.0)
            discount_value = purchase_price - effective_purchase_price
            scenarios.append(
                {
                    "key": key,
                    "label": label,
                    "kind": kind,
                    "initial_cash": round(effective_purchase_price, 2),
                    "monthly_payment": 0.0,
                    "installments": 0,
                    "effective_purchase_price": round(effective_purchase_price, 2),
                    "present_value_cost": round(effective_purchase_price, 2),
                    "total_nominal_cost": round(effective_purchase_price, 2),
                    "discount_value": round(discount_value, 2),
                    "financing_cost": 0.0,
                    "risk_level": "baixo",
                    "decision": "melhora_margem" if discount_pct > 0 else "neutro",
                    "score_impact": 5 if discount_pct > 0 else 3,
                    "reading": "Desconto a vista reduz preco de entrada e melhora margem.",
                }
            )
            continue

        if kind == "installments_no_interest":
            down_payment_pct = _first_float(
                term,
                "down_payment_pct",
                "downPaymentPct",
                default=0.0,
            )
            installments = max(0, _int(term, "installments"))
            initial_cash = purchase_price * down_payment_pct / 100.0
            monthly_payment = (
                (purchase_price - initial_cash) / installments if installments > 0 else 0.0
            )
            present_value_cost = _present_value_of_installments(
                initial_cash=initial_cash,
                monthly_payment=monthly_payment,
                installments=installments,
                monthly_discount_rate=monthly_discount_rate,
            )
            scenarios.append(
                {
                    "key": key,
                    "label": label,
                    "kind": kind,
                    "initial_cash": round(initial_cash, 2),
                    "monthly_payment": round(monthly_payment, 2),
                    "installments": installments,
                    "effective_purchase_price": round(purchase_price, 2),
                    "present_value_cost": round(present_value_cost, 2),
                    "total_nominal_cost": round(purchase_price, 2),
                    "discount_value": 0.0,
                    "financing_cost": 0.0,
                    "risk_level": "medio",
                    "decision": "preserva_caixa_mas_reduz_margem",
                    "score_impact": 3,
                    "reading": "Melhora caixa inicial, mas perde o desconto a vista.",
                }
            )
            continue

        if kind == "price_table":
            down_payment_pct = _first_float(
                term,
                "down_payment_pct",
                "downPaymentPct",
                default=0.0,
            )
            installments = max(0, _int(term, "installments"))
            annual_interest_pct = _first_float(
                term,
                "annual_interest_pct",
                "annualInterestPct",
                default=0.0,
            )
            indexed_to = _text(term, "indexed_to") or _text(term, "indexedTo")
            initial_cash = purchase_price * down_payment_pct / 100.0
            financed_amount = max(0.0, purchase_price - initial_cash)
            monthly_rate = (1 + annual_interest_pct / 100.0) ** (1 / 12) - 1
            monthly_payment = _price_table_payment(
                principal=financed_amount,
                monthly_rate=monthly_rate,
                installments=installments,
            )
            total_nominal_cost = initial_cash + monthly_payment * installments
            financing_cost = total_nominal_cost - purchase_price
            present_value_cost = _present_value_of_installments(
                initial_cash=initial_cash,
                monthly_payment=monthly_payment,
                installments=installments,
                monthly_discount_rate=monthly_discount_rate,
            )
            is_indexed = bool(indexed_to)
            risk_level = (
                "alto"
                if is_indexed or installments >= 48 or total_nominal_cost >= purchase_price * 1.15
                else "medio"
            )
            scenarios.append(
                {
                    "key": key,
                    "label": label,
                    "kind": kind,
                    "initial_cash": round(initial_cash, 2),
                    "monthly_payment": round(monthly_payment, 2),
                    "installments": installments,
                    "annual_interest_pct": round(annual_interest_pct, 2),
                    "monthly_interest_pct": round(monthly_rate * 100.0, 4),
                    "indexed_to": indexed_to.upper() if indexed_to else "",
                    "inflation_indexed": is_indexed,
                    "effective_purchase_price": round(total_nominal_cost, 2),
                    "present_value_cost": round(present_value_cost, 2),
                    "total_nominal_cost": round(total_nominal_cost, 2),
                    "discount_value": 0.0,
                    "financing_cost": round(financing_cost, 2),
                    "risk_level": risk_level,
                    "decision": (
                        "alto_custo_financeiro"
                        if risk_level == "alto"
                        else "parcelamento_financeiro_a_simular"
                    ),
                    "score_impact": 1 if risk_level == "alto" else 2,
                    "reading": (
                        "Parcelamento longo indexado exige cenario de IPCA antes de defender a tese."
                        if is_indexed
                        else "Parcelamento com juros precisa competir com a margem esperada."
                    ),
                }
            )

    if not scenarios:
        return {}

    recommended = max(
        scenarios,
        key=lambda item: (
            int(item.get("score_impact", 0)),
            -float(item.get("present_value_cost", 0.0)),
        ),
    )
    has_cash_discount = any(item["kind"] == "cash_discount" for item in scenarios)
    has_ipca_risk = any(item.get("inflation_indexed") for item in scenarios)
    has_high_risk = any(item.get("risk_level") == "alto" for item in scenarios)
    score_points = max(int(item.get("score_impact", 0)) for item in scenarios)
    if has_high_risk and not has_cash_discount:
        score_points = min(score_points, 2)

    if has_cash_discount and has_ipca_risk:
        summary = (
            "A vista com desconto melhora a margem; parcelamento longo com IPCA vira risco financeiro."
        )
    elif recommended["kind"] == "cash_discount":
        summary = "A vista com desconto melhora a margem da tese."
    elif recommended["kind"] == "installments_no_interest":
        summary = "Parcelamento sem juros preserva caixa, mas precisa compensar a perda do desconto."
    else:
        summary = "Condicoes comerciais exigem simulacao financeira antes de avancar."

    return {
        "source": _text(payload, "origin") or _text(payload, "source_origin") or "fonte informada",
        "source_url": _text(payload, "source_url"),
        "discount_rate_monthly_pct": round(discount_rate_pct, 2),
        "recommended_scenario_key": recommended["key"],
        "recommended_decision": recommended["decision"],
        "score_points": score_points,
        "score_detail": summary,
        "requires_ipca_assumption": has_ipca_risk,
        "summary": summary,
        "scenarios": scenarios,
    }


def _purchase_ceiling(
    *,
    sale_price: float,
    acquisition_costs: float,
    renovation_budget: float,
    carrying_cost: float,
    debt_costs: float = 0.0,
    selling_commission_pct: float,
    cash_needed: float,
    target_roi_pct: float,
) -> float:
    if sale_price <= 0:
        return 0.0
    commission = sale_price * selling_commission_pct / 100.0
    target_profit = cash_needed * target_roi_pct / 100.0 if cash_needed > 0 else 0.0
    ceiling = sale_price - commission - acquisition_costs
    ceiling -= renovation_budget + carrying_cost + max(0.0, debt_costs) + target_profit
    return round(max(0.0, ceiling), 2)


def _discount_points(purchase_price: float, market_value: float) -> int:
    if purchase_price <= 0 or market_value <= 0:
        return 4
    discount_pct = (market_value - purchase_price) / market_value * 100.0
    if discount_pct >= 30:
        return 15
    if discount_pct >= 20:
        return 12
    if discount_pct >= 10:
        return 8
    if discount_pct > 0:
        return 4
    return 0


def _value_creation_points(base_profit_pct: float) -> int:
    if base_profit_pct >= 20:
        return 15
    if base_profit_pct >= 10:
        return 10
    if base_profit_pct >= 5:
        return 6
    if base_profit_pct > 0:
        return 3
    return 0


def _renovation_points(kind: str) -> int:
    normalized = kind.strip().lower()
    if normalized in {"maquiagem", "maquiagem inteligente"}:
        return 15
    if normalized == "leve":
        return 13
    if normalized in {"retrofit", "retrofit controlado"}:
        return 9
    if normalized == "pesada":
        return 3
    return 6


def _time_points(months: int) -> int:
    if months <= 0:
        return 4
    if months <= 6:
        return 10
    if months <= 9:
        return 8
    if months <= 12:
        return 5
    return 2


def _legal_points(payload: dict[str, Any]) -> int:
    occupancy = _text(payload, "occupancy_status", "desconhecido").lower()
    has_registration = _bool(payload, "has_registration")
    condo_known = _bool(payload, "condo_debt_known")
    iptu_known = _bool(payload, "iptu_debt_known")

    points = 0
    if occupancy == "desocupado":
        points += 4
    elif occupancy == "desconhecido":
        points += 2
    else:
        points += 0

    if has_registration:
        points += 3
    if condo_known:
        points += 2
    if iptu_known:
        points += 1
    return min(points, 10)


def _cash_points(cash_needed: float) -> int:
    if cash_needed <= 0:
        return 4
    if cash_needed <= 100_000:
        return 10
    if cash_needed <= 200_000:
        return 8
    if cash_needed <= 350_000:
        return 5
    return 3


def _breakdown_item(
    *,
    key: str,
    label: str,
    points: int,
    max_points: int,
    detail: str,
    status: str = "calculado",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "points": points,
        "max_points": max_points,
        "status": status,
        "detail": detail,
    }


def _clarified_item(*, key: str, title: str, detail: str) -> dict[str, str]:
    return {
        "key": key,
        "title": title,
        "status": "esclarecido",
        "detail": detail,
    }


def _add_pending(
    items: list[dict[str, Any]],
    *,
    key: str,
    title: str,
    priority: str,
    action: str,
) -> None:
    items.append(
        {
            "key": key,
            "title": title,
            "priority": priority,
            "status": "aberta",
            "action": action,
        }
    )


def _unique_steps(*groups: list[str]) -> list[str]:
    steps: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            step = str(raw or "").strip()
            if not step:
                continue
            marker = _normalize_text(step)
            if marker in seen:
                continue
            seen.add(marker)
            steps.append(step)
    return steps


def _pending_validation_route(item: dict[str, Any]) -> tuple[list[str], str]:
    key = str(item.get("key") or "").strip().lower()
    title = _normalize_text(str(item.get("title") or ""))
    action = str(item.get("action") or "").strip()

    source_chain = [
        "Abrir a pagina individual do lote/anuncio e confirmar que nao e apenas agregador.",
        "Baixar edital/anexos e localizar o leiloeiro ou fonte oficial dentro do documento.",
        "Conferir o lote no site do leiloeiro, tribunal, banco, diario/jornal ou fonte primaria equivalente.",
        "Se a fonte pedir cadastro/login, pedir credenciais ao usuario e continuar a diligencia.",
    ]
    documents_chain = [
        "Anexar edital, matricula e laudo quando existirem.",
        "Extrair texto dos PDFs; se falhar, rodar OCR ou pedir via cartorio/leiloeiro.",
        "Conferir objeto vendido, titularidade, onus, averbacoes, restricoes e prazos.",
    ]
    liquidity_chain = [
        "Buscar 3 comparaveis equivalentes no mesmo predio, rua curta ou microbairro.",
        "Validar liquidez com preco, metragem, vaga, estado interno e tempo de anuncio.",
        "Quando possivel, confirmar com corretor local se o ativo gira naquele preco.",
    ]

    if key in {"source_validation", "source_access", "source_payment_risk", "edital"}:
        return (
            _unique_steps(
                source_chain,
                [action],
            ),
            "Resolvida quando a fonte primaria, edital/anexos, leiloeiro oficial e dados de pagamento estiverem coerentes; se exigir login, fica bloqueada por acesso do usuario, nao por desistência da app.",
        )

    if key in {"registration", "registration_ocr"} or "matricula" in title:
        return (
            _unique_steps(
                [
                    "Localizar matricula anexada na pagina do lote, edital ou cartorio.",
                    "Validar texto legivel; se for scan/imagem, rodar OCR ou obter segunda via.",
                    "Checar propriedade, onus, penhoras, indisponibilidade, usufruto, area e vaga.",
                ],
                [action],
            ),
            "Resolvida quando a matricula legivel confirma objeto, titularidade e restricoes materiais para a tese.",
        )

    if key in {"occupancy", "occupied_first_operation", "eviction_risk"} or "ocup" in title:
        return (
            _unique_steps(
                [
                    "Ler edital, laudo e matricula procurando ocupado, desocupado, locatario, visitas e imissao.",
                    "Confirmar com leiloeiro/corretor/administradora se ha ocupante e se existe visita ou fotos atuais.",
                    "Se ocupado, estimar prazo, custo juridico e plano de posse antes de qualquer proposta.",
                ],
                [action],
            ),
            "Resolvida quando ocupacao, responsavel pela desocupacao, prazo e custo estiverem documentados ou o candidato for descartado.",
        )

    if key in {"rights_over_asset", "fractional_interest", "bare_ownership"}:
        return (
            _unique_steps(
                [
                    "Ler edital e matricula para identificar se o objeto e propriedade plena, direitos, fracao ideal ou nua propriedade.",
                    "Confirmar com leiloeiro/cartorio se ha cessao possivel, restricao de transferencia e efeito no registro.",
                    "Submeter a advogado apenas se houver margem extraordinaria; caso contrario fechar fora do radar padrao.",
                ],
                [action],
            ),
            "Resolvida quando o objeto vendido permite propriedade plena liquidavel; se for direito/fracao/nua propriedade sem tese juridica, fechar.",
        )

    if key in {"debt_total", "condo_debt", "iptu_debt", "debt_responsibility_ambiguous"} or any(
        token in title for token in ("debito", "condominio", "iptu", "divida")
    ):
        return (
            _unique_steps(
                [
                    "Extrair do edital quem paga condominio, IPTU, taxas, comissao, ITBI e cartorio.",
                    "Consultar prefeitura para IPTU/divida ativa e administradora/sindico para condominio.",
                    "Obter confirmacao escrita do leiloeiro/banco/cartorio quando a responsabilidade por debitos for ambigua.",
                ],
                [action],
            ),
            "Resolvida quando o custo total e a responsabilidade por debitos entram na conta de margem ou geram descarte.",
        )

    if key in {"exit_value_dispersion", "exit_value_validation", "exit_value_missing", "sale_comparables", "local_buyer_demand"} or any(
        token in title for token in ("saida", "comparave", "demanda", "liquidez")
    ):
        return (
            _unique_steps(liquidity_chain, [action]),
            "Resolvida quando 3 comparaveis equivalentes e sinal de liquidez local sustentam o preco de saida conservador.",
        )

    if key == "financing_dependency":
        return (
            _unique_steps(
                [
                    "Ler edital e regra do banco para pagamento a vista, parcelamento, FGTS e financiamento.",
                    "Separar cenario a vista do financiado e validar credito antes de tratar o lance como executavel.",
                ],
                [action],
            ),
            "Resolvida quando edital, banco e comprador permitem a estrutura financeira usada na tese.",
        )

    if key in {"physical_condition", "renovation_budget"}:
        return (
            _unique_steps(
                [
                    "Buscar fotos recentes, laudo, visita ou vistoria.",
                    "Orcar reforma por estado interno real e separar maquiagem, leve, retrofit ou obra pesada.",
                ],
                [action],
            ),
            "Resolvida quando reforma e estado fisico entram no custo com evidencia visual ou orcamento.",
        )

    if key in {"auction_modality", "purchase_price"}:
        return (
            _unique_steps(source_chain, documents_chain, [action]),
            "Resolvida quando modalidade, praca, lance minimo e condicoes oficiais estiverem extraidos da fonte primaria.",
        )

    return (
        _unique_steps(source_chain, documents_chain, liquidity_chain[:1], [action]),
        "Resolvida quando a pendencia virar evidencia anexada, custo/modelo atualizado ou descarte explicito.",
    )


def _enrich_pending_validation_routes(items: list[dict[str, Any]]) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        route, exit_criteria = _pending_validation_route(item)
        item.setdefault("validation_method", "investigador_implacavel_aula_3")
        item.setdefault("validation_route", route)
        item.setdefault("validation_exit_criteria", exit_criteria)
        key = str(item.get("key") or "").strip().lower()
        if key == "source_access":
            item.setdefault("requires_user_access", True)
            item.setdefault(
                "user_access_instruction",
                "Pedir ao usuario cadastro/login ou arquivo de credenciais e retomar a diligencia.",
            )


def _known_debt_costs(payload: dict[str, Any]) -> float:
    debt_total = 0.0
    for key in (
        "known_debt_costs_brl",
        "knownDebtCostsBrl",
        "condo_debt_amount_brl",
        "condoDebtAmountBrl",
        "iptu_debt_amount_brl",
        "iptuDebtAmountBrl",
        "tributary_debt_amount_brl",
        "tributaryDebtAmountBrl",
    ):
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            debt_total += float(value)
        except (TypeError, ValueError):
            continue
    return round(max(0.0, debt_total), 2)


def _sourcing_profile(
    payload: dict[str, Any],
    *,
    auction_modality: str,
    available_capital: float,
    cash_needed: float,
    estimated_sale_conservative: float,
    has_exit_plan: bool,
    is_auction_like: bool,
    minimum_reserve_after_bid: float,
    operational_text: str,
    pending_items: list[dict[str, Any]],
    purchase_price: float,
    renovation_budget: float,
    sale_comparables_count: int,
) -> dict[str, Any]:
    if not is_auction_like:
        return {"score": 0, "tier": "fora_do_garimpo", "signals": [], "gaps": []}

    score = 0
    signals: list[str] = []
    gaps: list[str] = []
    source_url = _text(payload, "source_url")
    source_validation_status = _text(payload, "source_validation_status").lower()

    def add_signal(label: str, points: int) -> None:
        nonlocal score
        if label not in signals:
            signals.append(label)
            score += points

    def add_gap(label: str) -> None:
        if label not in gaps:
            gaps.append(label)

    if source_url and source_validation_status == "valid":
        add_signal("fonte oficial individual", 15)
    else:
        add_gap("fonte oficial individual")

    if _bool(payload, "low_competition_source") or _bool(payload, "lowCompetitionSource") or any(
        marker in operational_text
        for marker in ("cauda longa", "leiloeiro regional", "regional oficial", "pouca concorrencia")
    ):
        add_signal("canal pouco concorrido", 10)

    if sale_comparables_count >= 3 and estimated_sale_conservative > purchase_price > 0:
        add_signal("desconto validado por comparaveis", 20)
    else:
        add_gap("comparaveis de saida")

    physical_text = any(
        marker in operational_text
        for marker in ("feio", "abandonado", "obra", "reforma", "foto interna", "fotos internas")
    )
    physical_evidence = _bool(payload, "has_recent_photos") or _bool(payload, "hasRecentPhotos") or _bool(
        payload, "physical_condition_verified"
    ) or _bool(payload, "physicalConditionVerified")
    if renovation_budget > 0 and physical_text and physical_evidence:
        add_signal("reforma precificavel", 15)
    elif physical_text:
        add_gap("vistoria/fotos/orcamento")

    if has_exit_plan:
        add_signal("saida clara", 15)
    else:
        add_gap("plano de saida")

    if auction_modality:
        add_signal("modalidade classificada", 10)
    else:
        add_gap("modalidade")

    if available_capital > 0:
        reserve_after_bid = available_capital - cash_needed
        if cash_needed <= available_capital and reserve_after_bid >= minimum_reserve_after_bid:
            add_signal("capital compativel", 15)
        else:
            add_gap("capital/reserva")
    elif cash_needed > 0 and cash_needed <= 250_000:
        add_signal("ticket inicial executavel", 10)

    p0_count = sum(1 for item in pending_items if str(item.get("priority") or "").upper() == "P0")
    if p0_count:
        return {
            "score": min(score, 45),
            "tier": "bloqueado_por_p0",
            "signals": signals,
            "gaps": gaps,
            "recommendation": "Resolver P0 antes de usar como padrao positivo de busca.",
        }

    score = max(0, min(score, 100))
    if score >= 80:
        tier = "garimpo_qualificado"
        recommendation = "Buscar mais candidatos com o mesmo padrao de canal, reforma precificavel e saida clara."
    elif score >= 60:
        tier = "garimpo_em_prova"
        recommendation = "Manter no radar e completar as provas positivas que faltam."
    else:
        tier = "baixo_prioridade"
        recommendation = "Nao usar como modelo de busca ate melhorar fonte, saida, capital ou reforma."
    return {
        "score": score,
        "tier": tier,
        "signals": signals,
        "gaps": gaps,
        "recommendation": recommendation,
    }


def build_candidate_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    asset_first_diligence = build_asset_first_diligence(payload)
    listing_reading = _auction_listing_reading(payload)
    if listing_reading:
        payload = {**payload}
        if listing_reading.get("private_area_m2"):
            current_area = _first_float(payload, "private_area_m2", "privateAreaM2")
            inferred_area = float(listing_reading["private_area_m2"])
            inferred_total = float(listing_reading.get("total_area_m2") or 0.0)
            current_matches_inferred_total = (
                inferred_total > 0
                and abs(current_area - inferred_total) <= max(0.5, inferred_total * 0.02)
            )
            if current_area <= 0 or inferred_area > current_area or current_matches_inferred_total:
                payload["private_area_m2"] = inferred_area
        if listing_reading.get("occupancy_status"):
            current_occupancy = _text(payload, "occupancy_status", "desconhecido").lower()
            inferred_occupancy = str(listing_reading["occupancy_status"] or "").strip().lower()
            if current_occupancy == "desconhecido":
                payload["occupancy_status"] = inferred_occupancy
            elif inferred_occupancy and inferred_occupancy != current_occupancy:
                payload["occupancy_status"] = "desconhecido"
                listing_reading["occupancy_conflict"] = True
    is_auction_like = _auction_like_payload(payload)
    has_approved_eviction_plan = _has_approved_eviction_plan(payload)
    operational_text = _normalize_text(
        _combined_text(
            payload,
            "origin",
            "source_origin",
            "strategy",
            "title",
            "property_type",
            "listing_description",
            "auction_description",
            "raw_description",
            "description",
            "notes",
            "source_validation_reason",
        )
    )
    auction_modality = (
        _text(payload, "auction_modality")
        or _text(payload, "auctionModality")
        or str(listing_reading.get("auction_modality") or "")
    )
    financing_dependency = is_auction_like and not _bool(payload, "financing_validated") and (
        _bool(payload, "financing_required")
        or _bool(payload, "financingRequired")
        or _bool(payload, "depends_on_financing")
        or _bool(payload, "dependsOnFinancing")
        or any(
            marker in operational_text
            for marker in (
                "fgts",
                "financiamento",
                "financiar",
                "entrada baixa",
                "minha casa minha vida",
                "mcmv",
            )
        )
    )
    needs_physical_condition_review = (
        is_auction_like
        and not _bool(payload, "physical_condition_verified")
        and not _bool(payload, "physicalConditionVerified")
        and not _bool(payload, "has_recent_photos")
        and not _bool(payload, "hasRecentPhotos")
        and any(
            marker in operational_text
            for marker in (
                "abandonado",
                "sem fotos",
                "foto interna",
                "fotos internas",
                "visita",
                "vistoria",
                "obra",
                "reforma pesada",
            )
        )
    )
    has_exit_plan = bool(
        _text(payload, "plan_b")
        or _text(payload, "planB")
        or _text(payload, "exit_plan")
        or _text(payload, "exitPlan")
        or _text(payload, "resale_plan")
        or _text(payload, "resalePlan")
    )
    available_capital = _first_float(
        payload,
        "available_capital_brl",
        "availableCapitalBrl",
        "capital_available_brl",
        "capitalAvailableBrl",
    )
    minimum_reserve_after_bid = _first_float(
        payload,
        "minimum_reserve_after_bid_brl",
        "minimumReserveAfterBidBrl",
        "reserve_after_bid_min_brl",
        "reserveAfterBidMinBrl",
    )

    purchase_price = _float(payload, "asking_price")
    private_area_m2 = _first_float(payload, "private_area_m2", "privateAreaM2")
    market_value = _float(payload, "market_value_estimate") or _float(payload, "appraisal_value")
    estimated_sale_conservative = _float(payload, "estimated_sale_conservative")
    estimated_sale_base = _float(payload, "estimated_sale_base") or market_value
    estimated_sale_optimistic = _float(payload, "estimated_sale_optimistic") or max(
        estimated_sale_base,
        market_value,
    )
    valuation_evidence = _sale_valuation_from_comparables(
        payload,
        private_area_m2=private_area_m2,
    )
    if valuation_evidence:
        evidence_base_sale = float(valuation_evidence["base_sale_price"])
        estimated_sale_base = evidence_base_sale
        market_value = evidence_base_sale
        estimated_sale_conservative = float(valuation_evidence["conservative_sale_price"])
        estimated_sale_optimistic = float(valuation_evidence["optimistic_sale_price"])
    renovation_budget = _float(payload, "renovation_budget")
    carrying_months = _int(payload, "carrying_months", 6)
    monthly_carrying_cost = _float(payload, "monthly_carrying_cost", 0.0)
    carrying_cost = carrying_months * monthly_carrying_cost
    acquisition_costs = _float(payload, "acquisition_costs") or purchase_price * 0.05
    debt_costs = _known_debt_costs(payload)
    selling_commission_pct = _float(payload, "selling_commission_pct", 6.0)
    cash_needed = _float(payload, "cash_needed")
    if cash_needed <= 0:
        if purchase_price <= 0:
            cash_needed = 0.0
        else:
            cash_needed = purchase_price + acquisition_costs + renovation_budget + carrying_cost
            if debt_costs > 0:
                cash_needed += debt_costs
    needs_capital_sizing_review = (
        is_auction_like
        and available_capital > 0
        and (
            cash_needed > available_capital
            or (
                minimum_reserve_after_bid > 0
                and available_capital - cash_needed < minimum_reserve_after_bid
            )
        )
    )
    commercial_terms = _commercial_terms_analysis(payload, purchase_price=purchase_price)

    scenarios = {
        "conservative": _scenario(
            sale_price=estimated_sale_conservative,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            debt_costs=debt_costs,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
        "base": _scenario(
            sale_price=estimated_sale_base,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            debt_costs=debt_costs,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
        "optimistic": _scenario(
            sale_price=estimated_sale_optimistic,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            debt_costs=debt_costs,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
    }

    base_profit_pct = (
        scenarios["base"]["net_profit"] / purchase_price * 100.0 if purchase_price > 0 else 0.0
    )
    occupancy = _text(payload, "occupancy_status", "desconhecido").lower()
    sale_comparables_count = max(
        _int(payload, "sale_comparables_count"),
        int(valuation_evidence["sale_comparables_count"]) if valuation_evidence else 0,
    )
    sale_comparables_quality_warning = bool(
        valuation_evidence
        and valuation_evidence.get("source") == "sale_comparables"
        and valuation_evidence.get("quality_warning")
    )
    rent_comparables_count = _int(payload, "rent_comparables_count")
    local_demand_evidence = _local_buyer_demand_evidence(
        payload,
        private_area_m2=private_area_m2,
        purchase_price=purchase_price,
        estimated_sale_base=estimated_sale_base,
        sale_comparables_count=sale_comparables_count,
        rent_comparables_count=rent_comparables_count,
    )
    local_demand_risk = str(local_demand_evidence.get("risk_level") or "")
    weak_valuation_evidence = _weak_neighborhood_benchmark_evidence(
        payload,
        purchase_price=purchase_price,
        private_area_m2=private_area_m2,
        market_value=market_value,
        estimated_sale_base=estimated_sale_base,
        sale_comparables_count=sale_comparables_count,
    )
    auction_reference_evidence = _auction_reference_value_evidence(
        payload,
        market_value=market_value,
        estimated_sale_base=estimated_sale_base,
        sale_comparables_count=sale_comparables_count,
        listing_reading=listing_reading,
    )
    if auction_reference_evidence:
        weak_valuation_evidence = auction_reference_evidence
    weak_valuation = bool(weak_valuation_evidence)
    if weak_valuation and not valuation_evidence:
        valuation_evidence = weak_valuation_evidence
    source_url = _text(payload, "source_url")
    existing_source_validation = payload.get("source_validation")
    source_validation_dict = (
        existing_source_validation if isinstance(existing_source_validation, dict) else {}
    )
    source_validation_status = (
        _text(payload, "source_validation_status")
        or str(source_validation_dict.get("status") or "")
    ).lower()
    source_validation_reason = _text(payload, "source_validation_reason") or str(
        source_validation_dict.get("reason") or ""
    )

    location_score = _float(payload, "location_liquidity_score", 60.0)
    if local_demand_risk == "critico":
        location_score = min(location_score, 25.0)
    elif local_demand_risk == "alto":
        location_score = min(location_score, 45.0)
    location_points = round(max(0.0, min(location_score, 100.0)) * 0.20)
    discount_points = _discount_points(purchase_price, market_value)
    value_creation_points = _value_creation_points(base_profit_pct)
    valuation_uncertain = weak_valuation or sale_comparables_quality_warning
    if valuation_uncertain:
        discount_points = min(discount_points, 6)
        value_creation_points = min(value_creation_points, 6)
    renovation_points = _renovation_points(_text(payload, "renovation_type", "desconhecida"))
    time_points = _time_points(carrying_months)
    legal_points = _legal_points(payload)
    cash_points = _cash_points(cash_needed)
    plan_b_points = 5 if _text(payload, "plan_b") else 0
    score_breakdown = [
        _breakdown_item(
            key="location_liquidity",
            label="Liquidez/localizacao",
            points=location_points,
            max_points=20,
            status="pendente" if local_demand_risk in {"critico", "alto"} else "calculado",
            detail=(
                f"Indice informado/estimado: {round(location_score, 2)}/100."
                + (
                    f" {local_demand_evidence.get('status_label')}: "
                    f"{local_demand_evidence.get('caveat')}"
                    if local_demand_evidence
                    else ""
                )
            ),
        ),
        _breakdown_item(
            key="discount",
            label="Desconto vs valor de mercado",
            points=discount_points,
            max_points=15,
            status="pendente" if valuation_uncertain else "calculado",
            detail=(
                f"Preco pedido R$ {purchase_price:,.2f}; valor referencia R$ {market_value:,.2f}."
                + (
                    " Benchmark de bairro sem comparaveis equivalentes; desconto capado."
                    if weak_valuation
                    else (
                        " Comparaveis com dispersao alta; validar saida antes de confiar no desconto."
                        if sale_comparables_quality_warning
                        else ""
                    )
                )
            ),
        ),
        _breakdown_item(
            key="value_creation",
            label="Criacao de valor",
            points=value_creation_points,
            max_points=15,
            status="pendente" if valuation_uncertain else "calculado",
            detail=(
                f"Lucro base sobre compra: {round(base_profit_pct, 2)}%."
                + (
                    " Lucro depende de validar a saida no ativo, nao so no bairro."
                    if weak_valuation
                    else (
                        " Lucro depende de validar a saida; comparaveis com dispersao alta."
                        if sale_comparables_quality_warning
                        else ""
                    )
                )
            ),
        ),
        _breakdown_item(
            key="renovation",
            label="Tipo de reforma",
            points=renovation_points,
            max_points=15,
            detail=f"Reforma: {_text(payload, 'renovation_type', 'desconhecida')}.",
        ),
        _breakdown_item(
            key="time",
            label="Prazo de carregamento",
            points=time_points,
            max_points=10,
            detail=f"Prazo estimado: {carrying_months} meses.",
        ),
        _breakdown_item(
            key="legal",
            label="Risco documental/legal",
            points=legal_points,
            max_points=10,
            detail=f"Ocupacao: {occupancy}; matricula/debitos conforme campos informados.",
        ),
        _breakdown_item(
            key="cash",
            label="Caixa necessario",
            points=cash_points,
            max_points=10,
            detail=f"Caixa estimado: R$ {cash_needed:,.2f}.",
        ),
        _breakdown_item(
            key="plan_b",
            label="Plano B",
            points=plan_b_points,
            max_points=5,
            detail="Plano alternativo informado." if plan_b_points else "Plano alternativo pendente.",
        ),
    ]
    if commercial_terms:
        score_breakdown.append(
            _breakdown_item(
                key="commercial_terms",
                label="Condicoes comerciais",
                points=int(commercial_terms["score_points"]),
                max_points=5,
                detail=commercial_terms["score_detail"],
            )
        )
    score = int(max(0, min(sum(item["points"] for item in score_breakdown), 100)))

    occupancy_confidence = 15 if occupancy in {"desocupado", "ocupado"} else 0
    registration_confidence = 15 if _bool(payload, "has_registration") else 0
    edital_confidence = 3 if _bool(payload, "has_edital") else 0
    debts_are_known = _bool(payload, "condo_debt_known") and _bool(payload, "iptu_debt_known")
    debt_confidence = 10 if debts_are_known else 0
    sale_comparables_confidence = min(sale_comparables_count, 3) * 5
    sale_comparables_status = "esclarecido" if sale_comparables_count >= 3 else "parcial"
    sale_comparables_detail = f"{sale_comparables_count}/3 comparaveis de venda."
    if sale_comparables_quality_warning:
        sale_comparables_confidence = min(sale_comparables_confidence, 5)
        sale_comparables_status = "parcial"
        spread_ratio = float(valuation_evidence.get("price_per_m2_spread_ratio") or 0.0) if valuation_evidence else 0.0
        if spread_ratio > 0:
            sale_comparables_detail += f" Dispersao alta (max/min={spread_ratio:.2f})."
        sale_comparables_detail += " Validar saida com amostra mais equivalente."
    rent_comparables_confidence = min(rent_comparables_count, 3) * 3 + (
        1 if rent_comparables_count >= 3 else 0
    )
    renovation_budget_confidence = 15 if renovation_budget > 0 else 0
    financing_confidence = 10 if _bool(payload, "financing_validated") else 0
    plan_b_confidence = 10 if _text(payload, "plan_b") else 0
    confidence_breakdown = [
        _breakdown_item(
            key="occupancy",
            label="Ocupacao confirmada",
            points=occupancy_confidence,
            max_points=15,
            status="esclarecido" if occupancy_confidence else "pendente",
            detail=f"Ocupacao: {occupancy}.",
        ),
        _breakdown_item(
            key="registration",
            label="Matricula atualizada",
            points=registration_confidence,
            max_points=15,
            status="esclarecido" if registration_confidence else "pendente",
            detail="Matricula informada." if registration_confidence else "Matricula pendente.",
        ),
        _breakdown_item(
            key="edital",
            label="Fonte/Edital localizado",
            points=edital_confidence,
            max_points=3,
            status="esclarecido" if edital_confidence else "pendente",
            detail=(
                "Edital ou pagina oficial informado."
                if edital_confidence
                else "Edital ou pagina oficial pendente."
            ),
        ),
        _breakdown_item(
            key="debts",
            label="Dividas conhecidas",
            points=debt_confidence,
            max_points=10,
            status="esclarecido" if debt_confidence else "pendente",
            detail="Condominio e IPTU conhecidos." if debt_confidence else "Debitos ainda parciais.",
        ),
        _breakdown_item(
            key="sale_comparables",
            label="Comparaveis de venda",
            points=sale_comparables_confidence,
            max_points=15,
            status=sale_comparables_status,
            detail=sale_comparables_detail,
        ),
        _breakdown_item(
            key="rent_comparables",
            label="Comparaveis de aluguel",
            points=rent_comparables_confidence,
            max_points=10,
            status="esclarecido" if rent_comparables_count >= 3 else "parcial",
            detail=f"{rent_comparables_count}/3 comparaveis de aluguel.",
        ),
        _breakdown_item(
            key="renovation_budget",
            label="Orcamento de reforma",
            points=renovation_budget_confidence,
            max_points=15,
            status="esclarecido" if renovation_budget_confidence else "pendente",
            detail=(
                f"Orcamento informado: R$ {renovation_budget:,.2f}."
                if renovation_budget_confidence
                else "Orcamento pendente."
            ),
        ),
        _breakdown_item(
            key="financing",
            label="Financiamento validado",
            points=financing_confidence,
            max_points=10,
            status="esclarecido" if financing_confidence else "pendente",
            detail="Financiamento validado." if financing_confidence else "Financiamento pendente.",
        ),
        _breakdown_item(
            key="plan_b",
            label="Plano B validado",
            points=plan_b_confidence,
            max_points=10,
            status="esclarecido" if plan_b_confidence else "pendente",
            detail="Plano B informado." if plan_b_confidence else "Plano B pendente.",
        ),
    ]
    if commercial_terms:
        confidence_breakdown.append(
            _breakdown_item(
                key="commercial_terms",
                label="Condicoes comerciais lidas",
                points=5,
                max_points=5,
                status="esclarecido",
                detail="A app leu as formas de pagamento e gerou cenarios financeiros.",
            )
        )
    confidence = int(max(0, min(sum(item["points"] for item in confidence_breakdown), 100)))
    if local_demand_risk == "critico":
        confidence = min(confidence, 30)
    elif local_demand_risk == "alto":
        confidence = min(confidence, 45)

    legal_ownership_blockers = [
        str(item)
        for item in listing_reading.get("legal_ownership_blockers", [])
        if str(item).strip()
    ]
    legal_ownership_blocker_text = ", ".join(legal_ownership_blockers)
    pending_items: list[dict[str, Any]] = []
    if purchase_price <= 0:
        _add_pending(
            pending_items,
            key="purchase_price",
            title="Confirmar valor de compra/lance",
            priority="P0",
            action="Extrair valor minimo, lance inicial ou tabela de pagamento oficial antes de simular ROI.",
        )
    if source_url and source_validation_status not in {"valid"}:
        source_key = "source_validation"
        if source_validation_status in {"expired", "unavailable"}:
            source_title = "Fonte indisponivel"
            source_action = source_validation_reason or "Remover do radar ativo ate existir nova fonte individual."
        elif source_validation_status == "access_required":
            credential_hint = str(source_validation_dict.get("credential_file_hint") or "")
            user_action = str(source_validation_dict.get("user_action") or "")
            source_key = "source_access"
            source_title = "Acesso ao leiloeiro necessario"
            source_action = (
                user_action
                or source_validation_reason
                or "Criar cadastro/login no leiloeiro e anexar credenciais para continuar."
            )
            if credential_hint:
                source_action = f"{source_action} Arquivo esperado: {credential_hint}."
        elif source_validation_status == "ambiguous":
            source_title = "Validar fonte manualmente"
            source_action = source_validation_reason or "Confirmar se o link e um lote/anuncio individual ainda publicado."
        else:
            source_title = "Validar fonte do candidato"
            source_action = "A app ainda nao confirmou se o link individual esta vivo."
        _add_pending(
            pending_items,
            key=source_key,
            title=source_title,
            priority="P0",
            action=source_action,
        )
    if listing_reading.get("suspicious_payment_instruction"):
        _add_pending(
            pending_items,
            key="source_payment_risk",
            title="Validar fonte e pagamento oficial",
            priority="P0",
            action="Conferir leiloeiro oficial, dominio, edital e dados de pagamento antes de qualquer lance.",
        )
    if listing_reading.get("fiduciary_auction_nullity_action"):
        process_number = str(listing_reading.get("judicial_process_number") or "").strip()
        process_suffix = f" Processo: {process_number}." if process_number else ""
        _add_pending(
            pending_items,
            key="fiduciary_auction_nullity_action",
            title="Acao judicial ataca consolidacao/leilao",
            priority="P0",
            action=(
                "Remover do radar padrao ate advogado validar processo, liminar, risco de anulacao "
                f"e efeito sobre posse/titulo.{process_suffix}"
            ),
        )
    if occupancy == "desconhecido":
        _add_pending(
            pending_items,
            key="occupancy",
            title="Confirmar ocupacao",
            priority="P0",
            action="Validar com fonte oficial, corretor ou responsavel pelo edital.",
        )
    if occupancy == "ocupado" and _bool(payload, "first_operation", True):
        _add_pending(
            pending_items,
            key="occupied_first_operation",
            title="Imovel ocupado na primeira operacao",
            priority="P0",
            action="Descartar ou travar decisao ate avaliar desocupacao com especialista.",
        )
    if listing_reading.get("buyer_responsible_for_eviction"):
        _add_pending(
            pending_items,
            key="eviction_risk",
            title="Desocupacao por conta do comprador",
            priority="P0",
            action="Nao tratar como lance simples; estimar prazo, custo juridico e risco de imissao.",
        )
    if listing_reading.get("rights_over_asset"):
        _add_pending(
            pending_items,
            key="rights_over_asset",
            title="Confirmar natureza dos direitos",
            priority="P0",
            action=(
                "Quando a oferta e de direitos e nao da propriedade plena, confirmar se ha "
                "cessao de direitos, financiamento/alienacao fiduciaria, restricoes de cessao "
                "e como isso afeta liquidez, preco e prazo de revenda."
            ),
        )
    if listing_reading.get("fractional_interest"):
        _add_pending(
            pending_items,
            key="fractional_interest",
            title="Bloquear fracao ideal",
            priority="P0",
            action=(
                "Nao manter fracao, parte ideal ou quota no radar de leilao; exige tese juridica "
                "separada e liquidez especifica antes de qualquer proposta."
            ),
        )
    if listing_reading.get("bare_ownership"):
        _add_pending(
            pending_items,
            key="bare_ownership",
            title="Bloquear nua propriedade",
            priority="P0",
            action=(
                "Nao tratar nua propriedade como compra de imovel pleno; descartar do radar de leilao "
                "ate existir tese juridica propria para usufruto e liquidez."
            ),
        )
    if listing_reading.get("seller_disclaims_due_diligence") or listing_reading.get(
        "buyer_responsible_for_due_diligence"
    ):
        _add_pending(
            pending_items,
            key="auction_due_diligence_disclaimer",
            title="Edital transfere diligencia ao comprador",
            priority="P0",
            action="Ler edital, matricula, acoes judiciais e restricoes HIS/HMP antes de manter a tese.",
        )
    if is_auction_like and not _bool(payload, "has_edital"):
        _add_pending(
            pending_items,
            key="edital",
            title="Buscar edital oficial",
            priority="P0",
            action="Anexar edital oficial e conferir objeto vendido, modalidade, prazos e condicoes de pagamento.",
        )
    if is_auction_like and not auction_modality:
        _add_pending(
            pending_items,
            key="auction_modality",
            title="Classificar modalidade do leilao",
            priority="P1",
            action="Separar judicial, extrajudicial, venda direta ou banco antes de aplicar prazos e checklist.",
        )
    if not _bool(payload, "has_registration"):
        _add_pending(
            pending_items,
            key="registration",
            title="Buscar matricula atualizada",
            priority="P0",
            action="Conferir propriedade, onus, restricoes e averbacoes relevantes.",
        )
    else:
        registration_text_status = _text(payload, "registration_text_status").strip().lower()
        if (
            registration_text_status in {"empty_text", "error", "dependency_missing"}
            or registration_text_status.startswith("error:")
        ):
            _add_pending(
                pending_items,
                key="registration_ocr",
                title="Validar matricula (OCR se necessario)",
                priority="P0",
                action=(
                    "Matrícula anexada sem texto legivel (scan/cripto). Rodar OCR ou obter via "
                    "cartorio/leiloeiro para checar onus, averbacoes e ocupacao antes de simular risco."
                ),
            )
    if listing_reading.get("debt_responsibility_ambiguous"):
        _add_pending(
            pending_items,
            key="debt_responsibility_ambiguous",
            title="Confirmar responsabilidade por debitos",
            priority="P0",
            action=(
                "Obter confirmacao escrita do leiloeiro, cartorio, banco ou contato oficial "
                "do edital sobre quais debitos ficam com o arrematante antes de qualquer lance."
            ),
        )
    if is_auction_like and (
        not _bool(payload, "condo_debt_known") or not _bool(payload, "iptu_debt_known")
    ):
        _add_pending(
            pending_items,
            key="debt_total",
            title="Confirmar custo total de debitos",
            priority="P0",
            action=(
                "Levantar IPTU, condominio, comissao, ITBI, cartorio e responsabilidade por "
                "debitos antes de calcular margem ou teto de lance."
            ),
        )
    if not _bool(payload, "condo_debt_known"):
        _add_pending(
            pending_items,
            key="condo_debt",
            title="Confirmar divida de condominio",
            priority="P0",
            action="Levantar valor vencido, limite de responsabilidade e acordo possivel.",
        )
    if not _bool(payload, "iptu_debt_known"):
        _add_pending(
            pending_items,
            key="iptu_debt",
            title="Confirmar divida de IPTU",
            priority="P0" if is_auction_like else "P1",
            action="Checar debitos municipais antes de calcular lucro.",
        )
    if financing_dependency:
        _add_pending(
            pending_items,
            key="financing_dependency",
            title="Validar financiamento/FGTS",
            priority="P0",
            action="Separar cenario a vista do financiado e confirmar se edital, banco e comprador permitem FGTS/financiamento.",
        )
    if sale_comparables_quality_warning:
        _add_pending(
            pending_items,
            key="exit_value_dispersion",
            title="Validar valor de saida",
            priority="P0",
            action=(
                "Comparaveis com grande dispersao de preco por m2; buscar 3 equivalentes (mesmo "
                "predio/raio curto) e confirmar faixa de saida antes de confiar no ROI."
            ),
        )
    if weak_valuation:
        _add_pending(
            pending_items,
            key="exit_value_validation",
            title="Validar valor de saida",
            priority="P0",
            action=(
                "Nao usar media de bairro como valor de revenda; buscar comparaveis do mesmo "
                "predio ou unidades equivalentes."
            ),
        )
    if estimated_sale_base <= 0 and market_value <= 0:
        _add_pending(
            pending_items,
            key="exit_value_missing",
            title="Validar valor de saida",
            priority="P0",
            action="Sem comparaveis ou avaliacao utilizavel; coletar 3 comparaveis antes de simular ROI.",
        )
    if local_demand_evidence and local_demand_risk in {"critico", "alto", "medio"}:
        _add_pending(
            pending_items,
            key="local_buyer_demand",
            title="Validar demanda local e comprador",
            priority="P0" if local_demand_risk in {"critico", "alto"} else "P1",
            action=str(local_demand_evidence.get("required_action") or ""),
        )
    if sale_comparables_count < 3:
        _add_pending(
            pending_items,
            key="sale_comparables",
            title="Buscar 3 comparaveis de venda",
            priority="P1",
            action="Usar comparaveis do mesmo condominio ou raio muito proximo.",
        )
    if (
        "condition_photos" in asset_first_diligence.get("missing_source_roles", [])
        and (is_auction_like or bool(source_url))
    ):
        first_condition_query = next(
            (
                item.get("query")
                for item in asset_first_diligence.get("lateral_search_queries", [])
                if item.get("role") == "condition_photos"
            ),
            "",
        )
        _add_pending(
            pending_items,
            key="asset_first_condition_photos",
            title="Buscar fonte lateral com fotos internas",
            priority="P1",
            action=(
                "Rodar busca asset-first por endereco/condominio para achar fotos internas, fachada "
                "e videos do mesmo ativo."
                + (f" Primeira consulta: {first_condition_query}." if first_condition_query else "")
            ),
        )
    if needs_physical_condition_review:
        _add_pending(
            pending_items,
            key="physical_condition",
            title="Validar vistoria, fotos e reforma",
            priority="P1",
            action="Exigir fotos recentes, visita/vistoria ou orcamento antes de confiar no desconto.",
        )
    if is_auction_like and not has_exit_plan:
        _add_pending(
            pending_items,
            key="exit_plan",
            title="Definir plano de saida",
            priority="P2",
            action="Informar se a tese e vender, alugar ou reformar, com preco alvo, prazo e custo de carregamento.",
        )
    if needs_capital_sizing_review:
        _add_pending(
            pending_items,
            key="capital_sizing",
            title="Validar capital e reserva pos-lance",
            priority="P2",
            action=(
                "Confirmar se o capital disponivel cobre entrada, custos, reforma e reserva de seguranca "
                "antes de tratar o primeiro lance como executavel."
            ),
        )
    if renovation_budget <= 0:
        _add_pending(
            pending_items,
            key="renovation_budget",
            title="Fazer orcamento de reforma",
            priority="P1",
            action="Separar maquiagem, reforma leve, retrofit e obra pesada.",
        )
    if commercial_terms.get("requires_ipca_assumption"):
        _add_pending(
            pending_items,
            key="commercial_terms_ipca",
            title="Simular IPCA nas parcelas",
            priority="P1",
            action="Projetar sensibilidade de IPCA e juros antes de usar parcelamento longo na tese.",
        )

    _enrich_pending_validation_routes(pending_items)

    sourcing = _sourcing_profile(
        payload,
        auction_modality=auction_modality,
        available_capital=available_capital,
        cash_needed=cash_needed,
        estimated_sale_conservative=estimated_sale_conservative,
        has_exit_plan=has_exit_plan,
        is_auction_like=is_auction_like,
        minimum_reserve_after_bid=minimum_reserve_after_bid,
        operational_text=operational_text,
        pending_items=pending_items,
        purchase_price=purchase_price,
        renovation_budget=renovation_budget,
        sale_comparables_count=sale_comparables_count,
    )

    clarified_items: list[dict[str, str]] = []
    if source_url and source_validation_status == "valid":
        clarified_items.append(
            _clarified_item(
                key="source_validation",
                title="Fonte individual validada",
                detail=source_validation_reason or "A app confirmou que o link aponta para anuncio/lote individual.",
            )
        )
    if occupancy in {"desocupado", "ocupado"}:
        clarified_items.append(
            _clarified_item(
                key="occupancy",
                title="Ocupacao informada",
                detail=f"Ocupacao registrada como {occupancy}.",
            )
        )
    if _bool(payload, "has_registration"):
        clarified_items.append(
            _clarified_item(
                key="registration",
                title="Matricula localizada",
                detail="Campo de matricula marcado como validado.",
            )
        )
    if _bool(payload, "has_edital"):
        clarified_items.append(
            _clarified_item(
                key="edital",
                title="Edital localizado",
                detail="Edital ou pagina oficial informado no radar.",
            )
        )
    if _bool(payload, "condo_debt_known"):
        clarified_items.append(
            _clarified_item(
                key="condo_debt",
                title="Divida de condominio esclarecida",
                detail="Campo de condominio marcado como conhecido.",
            )
        )
    if _bool(payload, "iptu_debt_known"):
        clarified_items.append(
            _clarified_item(
                key="iptu_debt",
                title="Divida de IPTU esclarecida",
                detail="Campo de IPTU marcado como conhecido.",
            )
        )
    if sale_comparables_count > 0:
        comparable_detail = f"{sale_comparables_count} comparaveis de venda informados."
        if valuation_evidence and valuation_evidence.get("source") == "sale_comparables":
            comparable_detail = (
                f"{sale_comparables_count} comparaveis de venda informados; "
                f"base recalibrada para R$ {valuation_evidence['base_sale_price']:,.2f}."
            )
        elif weak_valuation:
            comparable_detail = (
                f"{sale_comparables_count} comparaveis de venda informados, mas a saida ainda "
                "depende de 3 referencias equivalentes ao ativo."
            )
        clarified_items.append(
            _clarified_item(
                key="sale_comparables",
                title="Comparaveis de venda iniciados",
                detail=comparable_detail,
            )
        )
    if rent_comparables_count > 0:
        clarified_items.append(
            _clarified_item(
                key="rent_comparables",
                title="Comparaveis de aluguel iniciados",
                detail=f"{rent_comparables_count} comparaveis de aluguel informados.",
            )
        )
    if renovation_budget > 0:
        clarified_items.append(
            _clarified_item(
                key="renovation_budget",
                title="Orcamento de reforma informado",
                detail=f"Orcamento de R$ {renovation_budget:,.2f}.",
            )
        )
    if _bool(payload, "financing_validated"):
        clarified_items.append(
            _clarified_item(
                key="financing",
                title="Financiamento validado",
                detail="Campo de financiamento marcado como validado.",
            )
        )
    if _text(payload, "plan_b"):
        clarified_items.append(
            _clarified_item(
                key="plan_b",
                title="Plano B informado",
                detail=_text(payload, "plan_b"),
            )
        )
    if commercial_terms:
        clarified_items.append(
            _clarified_item(
                key="commercial_terms",
                title="Condicoes comerciais lidas",
                detail=commercial_terms["summary"],
            )
        )
    if local_demand_evidence and local_demand_risk == "critico":
        clarified_items.append(
            _clarified_item(
                key="local_buyer_demand_learning",
                title="Aprendizado de demanda local",
                detail=str(local_demand_evidence.get("caveat") or ""),
            )
        )

    has_p0 = any(item["priority"] == "P0" for item in pending_items)
    conservative_profit = scenarios["conservative"]["net_profit"]
    condo_debt_amount = _first_float(payload, "condo_debt_amount_brl", "condoDebtAmountBrl")
    if source_validation_status in {"expired", "unavailable"}:
        suggested_status = "Descartado"
        next_action = source_validation_reason or "Fonte indisponivel"
    elif source_validation_status == "access_required":
        suggested_status = "Aberto com pendencias"
        next_action = "Acesso ao leiloeiro necessario"
    elif listing_reading.get("suspicious_payment_instruction"):
        suggested_status = "Descartado"
        next_action = "Fechar candidato: fonte/pagamento nao oficial"
    elif listing_reading.get("fiduciary_auction_nullity_action"):
        suggested_status = "Descartado"
        next_action = "Fechar candidato: acao judicial ataca consolidacao/leilao"
    elif legal_ownership_blockers:
        suggested_status = "Descartado"
        next_action = (
            f"Fechar candidato: {legal_ownership_blocker_text} nao entra no radar de leilao"
        )
    elif local_demand_evidence.get("should_discard"):
        suggested_status = "Descartado"
        next_action = "Fechar candidato: demanda local reprovada"
    elif occupancy == "ocupado" and _bool(payload, "first_operation", True):
        suggested_status = "Descartado"
        next_action = "Descartar ou travar decisao"
    elif listing_reading.get("buyer_responsible_for_eviction") and not has_approved_eviction_plan:
        suggested_status = "Descartado"
        next_action = "Fechar candidato: posse/desocupacao sem plano aprovado"
    elif condo_debt_amount >= CONDO_DEBT_EXIT_THRESHOLD_BRL:
        suggested_status = "Descartado"
        next_action = "Fechar candidato: divida de condominio acima do limiar"
    elif conservative_profit < 0 and score < 70:
        if estimated_sale_base <= 0 and market_value <= 0:
            suggested_status = "Aberto com pendencias"
            next_action = "Validar valor de saida"
        else:
            suggested_status = "Descartado"
            next_action = "Rever preco maximo ou descartar"
    elif source_validation_status == "ambiguous":
        suggested_status = "Aberto com pendencias"
        next_action = "Validar fonte manualmente"
    elif score >= 80 and confidence >= 70 and not has_p0:
        suggested_status = "Candidato forte"
        next_action = "Avancar para diligencia"
    elif has_p0:
        suggested_status = "Aberto com pendencias"
        next_action = next(item["title"] for item in pending_items if item["priority"] == "P0")
    elif score >= 75:
        suggested_status = "Diligencia"
        next_action = "Validar documentos e visita"
    elif score >= 60:
        suggested_status = "Em estudo"
        next_action = (
            pending_items[0]["title"]
            if pending_items
            else "Comparar com outros candidatos"
        )
    else:
        suggested_status = "Descartado"
        next_action = "Descartar ou rever premissas"

    commission_factor = max(0.01, 1.0 - selling_commission_pct / 100.0)
    breakeven_sale_price = (
        purchase_price + acquisition_costs + renovation_budget + carrying_cost + debt_costs
    ) / commission_factor
    target_roi_pct = _float(payload, "target_roi_pct", 20.0)
    ceiling_sale_price = estimated_sale_conservative or estimated_sale_base
    max_purchase_price = _purchase_ceiling(
        sale_price=ceiling_sale_price,
        acquisition_costs=acquisition_costs,
        renovation_budget=renovation_budget,
        carrying_cost=carrying_cost,
        debt_costs=debt_costs,
        selling_commission_pct=selling_commission_pct,
        cash_needed=cash_needed,
        target_roi_pct=target_roi_pct,
    )
    price_gap_to_ceiling = round(purchase_price - max_purchase_price, 2)
    if max_purchase_price <= 0:
        price_ceiling_status = "Sem preco teto"
    elif weak_valuation:
        price_ceiling_status = "Teto a validar"
    elif price_gap_to_ceiling <= 0:
        price_ceiling_status = "Dentro do teto"
    else:
        price_ceiling_status = "Acima do teto"

    source_validation_payload: dict[str, Any] = {
        "status": source_validation_status or ("unchecked" if source_url else ""),
        "reason": source_validation_reason,
        "checked_at": _text(payload, "source_checked_at"),
        "url": source_url,
    }
    source_validation_payload.update(source_validation_dict)
    source_validation_payload["status"] = source_validation_status or str(
        source_validation_payload.get("status") or ("unchecked" if source_url else "")
    )
    source_validation_payload["reason"] = source_validation_reason or str(
        source_validation_payload.get("reason") or ""
    )
    source_validation_payload["checked_at"] = _text(payload, "source_checked_at") or str(
        source_validation_payload.get("checked_at") or ""
    )
    source_validation_payload["url"] = source_url or str(source_validation_payload.get("url") or "")

    return {
        "score": score,
        "confidence": confidence,
        "suggested_status": suggested_status,
        "next_action": next_action,
        "score_breakdown": score_breakdown,
        "confidence_breakdown": confidence_breakdown,
        "pending_items": pending_items,
        "clarified_items": clarified_items,
        "scenarios": scenarios,
        "breakeven_sale_price": round(breakeven_sale_price, 2),
        "max_purchase_price": max_purchase_price,
        "price_gap_to_ceiling": price_gap_to_ceiling,
        "price_ceiling_status": price_ceiling_status,
        "target_roi_pct": round(target_roi_pct, 2),
        "cash_needed": round(cash_needed, 2),
        "base_profit_pct": round(base_profit_pct, 2),
        "acquisition_costs": round(acquisition_costs, 2),
        "renovation_budget": round(renovation_budget, 2),
        "carrying_costs": round(carrying_cost, 2),
        "selling_commission_pct": round(selling_commission_pct, 2),
        "selling_costs": round(estimated_sale_base * selling_commission_pct / 100.0, 2),
        "debt_costs_assumed_brl": debt_costs,
        "commercial_terms": commercial_terms,
        "sourcing": sourcing,
        "asset_first_diligence": asset_first_diligence,
        "valuation_evidence": valuation_evidence or {},
        "local_demand_evidence": local_demand_evidence or {},
        "listing_reading": listing_reading or {},
        "source_validation": source_validation_payload,
    }


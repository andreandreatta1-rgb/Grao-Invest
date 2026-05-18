from __future__ import annotations

from typing import Any


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


def _scenario(
    *,
    sale_price: float,
    purchase_price: float,
    acquisition_costs: float,
    renovation_budget: float,
    carrying_cost: float,
    selling_commission_pct: float,
    cash_needed: float,
) -> dict[str, float]:
    commission = sale_price * selling_commission_pct / 100.0
    net_profit = sale_price - commission - purchase_price - acquisition_costs
    net_profit -= renovation_budget + carrying_cost
    roi_pct = (net_profit / cash_needed * 100.0) if cash_needed > 0 else 0.0
    return {
        "sale_price": round(sale_price, 2),
        "net_profit": round(net_profit, 2),
        "roi_pct": round(roi_pct, 2),
    }


def _purchase_ceiling(
    *,
    sale_price: float,
    acquisition_costs: float,
    renovation_budget: float,
    carrying_cost: float,
    selling_commission_pct: float,
    cash_needed: float,
    target_roi_pct: float,
) -> float:
    if sale_price <= 0:
        return 0.0
    commission = sale_price * selling_commission_pct / 100.0
    target_profit = cash_needed * target_roi_pct / 100.0 if cash_needed > 0 else 0.0
    ceiling = sale_price - commission - acquisition_costs
    ceiling -= renovation_budget + carrying_cost + target_profit
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
    items: list[dict[str, str]],
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


def build_candidate_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    purchase_price = _float(payload, "asking_price")
    market_value = _float(payload, "market_value_estimate") or _float(payload, "appraisal_value")
    estimated_sale_conservative = _float(payload, "estimated_sale_conservative")
    estimated_sale_base = _float(payload, "estimated_sale_base") or market_value
    estimated_sale_optimistic = _float(payload, "estimated_sale_optimistic") or max(
        estimated_sale_base,
        market_value,
    )
    renovation_budget = _float(payload, "renovation_budget")
    carrying_months = _int(payload, "carrying_months", 6)
    monthly_carrying_cost = _float(payload, "monthly_carrying_cost", 0.0)
    carrying_cost = carrying_months * monthly_carrying_cost
    acquisition_costs = _float(payload, "acquisition_costs") or purchase_price * 0.05
    selling_commission_pct = _float(payload, "selling_commission_pct", 6.0)
    cash_needed = _float(payload, "cash_needed")
    if cash_needed <= 0:
        cash_needed = purchase_price * 0.2 + acquisition_costs + renovation_budget + carrying_cost

    scenarios = {
        "conservative": _scenario(
            sale_price=estimated_sale_conservative,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
        "base": _scenario(
            sale_price=estimated_sale_base,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
        "optimistic": _scenario(
            sale_price=estimated_sale_optimistic,
            purchase_price=purchase_price,
            acquisition_costs=acquisition_costs,
            renovation_budget=renovation_budget,
            carrying_cost=carrying_cost,
            selling_commission_pct=selling_commission_pct,
            cash_needed=cash_needed,
        ),
    }

    base_profit_pct = (
        scenarios["base"]["net_profit"] / purchase_price * 100.0 if purchase_price > 0 else 0.0
    )
    occupancy = _text(payload, "occupancy_status", "desconhecido").lower()
    sale_comparables_count = _int(payload, "sale_comparables_count")
    rent_comparables_count = _int(payload, "rent_comparables_count")
    source_url = _text(payload, "source_url")
    source_validation_status = _text(payload, "source_validation_status").lower()
    source_validation_reason = _text(payload, "source_validation_reason")

    location_score = _float(payload, "location_liquidity_score", 60.0)
    location_points = round(max(0.0, min(location_score, 100.0)) * 0.20)
    discount_points = _discount_points(purchase_price, market_value)
    value_creation_points = _value_creation_points(base_profit_pct)
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
            detail=f"Indice informado/estimado: {round(location_score, 2)}/100.",
        ),
        _breakdown_item(
            key="discount",
            label="Desconto vs valor de mercado",
            points=discount_points,
            max_points=15,
            detail=f"Preco pedido R$ {purchase_price:,.2f}; valor referencia R$ {market_value:,.2f}.",
        ),
        _breakdown_item(
            key="value_creation",
            label="Criacao de valor",
            points=value_creation_points,
            max_points=15,
            detail=f"Lucro base sobre compra: {round(base_profit_pct, 2)}%.",
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
    score = int(max(0, min(sum(item["points"] for item in score_breakdown), 100)))

    occupancy_confidence = 15 if occupancy in {"desocupado", "ocupado"} else 0
    registration_confidence = 15 if _bool(payload, "has_registration") else 0
    edital_confidence = 3 if _bool(payload, "has_edital") else 0
    debts_are_known = _bool(payload, "condo_debt_known") and _bool(payload, "iptu_debt_known")
    debt_confidence = 10 if debts_are_known else 0
    sale_comparables_confidence = min(sale_comparables_count, 3) * 5
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
            status="esclarecido" if sale_comparables_count >= 3 else "parcial",
            detail=f"{sale_comparables_count}/3 comparaveis de venda.",
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
    confidence = int(max(0, min(sum(item["points"] for item in confidence_breakdown), 100)))

    pending_items: list[dict[str, str]] = []
    if source_url and source_validation_status not in {"valid"}:
        if source_validation_status in {"expired", "unavailable"}:
            source_title = "Fonte indisponivel"
            source_action = source_validation_reason or "Remover do radar ativo ate existir nova fonte individual."
        elif source_validation_status == "ambiguous":
            source_title = "Validar fonte manualmente"
            source_action = source_validation_reason or "Confirmar se o link e um lote/anuncio individual ainda publicado."
        else:
            source_title = "Validar fonte do candidato"
            source_action = "A app ainda nao confirmou se o link individual esta vivo."
        _add_pending(
            pending_items,
            key="source_validation",
            title=source_title,
            priority="P0",
            action=source_action,
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
    if not _bool(payload, "has_registration"):
        _add_pending(
            pending_items,
            key="registration",
            title="Buscar matricula atualizada",
            priority="P0",
            action="Conferir propriedade, onus, restricoes e averbacoes relevantes.",
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
            priority="P1",
            action="Checar debitos municipais antes de calcular lucro.",
        )
    if sale_comparables_count < 3:
        _add_pending(
            pending_items,
            key="sale_comparables",
            title="Buscar 3 comparaveis de venda",
            priority="P1",
            action="Usar comparaveis do mesmo condominio ou raio muito proximo.",
        )
    if renovation_budget <= 0:
        _add_pending(
            pending_items,
            key="renovation_budget",
            title="Fazer orcamento de reforma",
            priority="P1",
            action="Separar maquiagem, reforma leve, retrofit e obra pesada.",
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
        clarified_items.append(
            _clarified_item(
                key="sale_comparables",
                title="Comparaveis de venda iniciados",
                detail=f"{sale_comparables_count} comparaveis de venda informados.",
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

    has_p0 = any(item["priority"] == "P0" for item in pending_items)
    conservative_profit = scenarios["conservative"]["net_profit"]
    if source_validation_status in {"expired", "unavailable"}:
        suggested_status = "Descartado"
        next_action = source_validation_reason or "Fonte indisponivel"
    elif source_validation_status == "ambiguous":
        suggested_status = "Aberto com pendencias"
        next_action = "Validar fonte manualmente"
    elif occupancy == "ocupado" and _bool(payload, "first_operation", True):
        suggested_status = "Descartado"
        next_action = "Descartar ou travar decisao"
    elif conservative_profit < 0 and score < 70:
        suggested_status = "Descartado"
        next_action = "Rever preco maximo ou descartar"
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
        purchase_price + acquisition_costs + renovation_budget + carrying_cost
    ) / commission_factor
    target_roi_pct = _float(payload, "target_roi_pct", 20.0)
    ceiling_sale_price = estimated_sale_conservative or estimated_sale_base
    max_purchase_price = _purchase_ceiling(
        sale_price=ceiling_sale_price,
        acquisition_costs=acquisition_costs,
        renovation_budget=renovation_budget,
        carrying_cost=carrying_cost,
        selling_commission_pct=selling_commission_pct,
        cash_needed=cash_needed,
        target_roi_pct=target_roi_pct,
    )
    price_gap_to_ceiling = round(purchase_price - max_purchase_price, 2)
    if max_purchase_price <= 0:
        price_ceiling_status = "Sem preco teto"
    elif price_gap_to_ceiling <= 0:
        price_ceiling_status = "Dentro do teto"
    else:
        price_ceiling_status = "Acima do teto"

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
        "source_validation": {
            "status": source_validation_status or ("unchecked" if source_url else ""),
            "reason": source_validation_reason,
            "checked_at": _text(payload, "source_checked_at"),
            "url": source_url,
        },
    }


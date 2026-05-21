from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.services.real_estate_radar import build_candidate_analysis


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "data" / "dashboard_seed.json"
LEADS_PATH = ROOT / "data" / "real_estate_target_candidate_leads.json"
TARGET_PREFIX = "IM-RADAR-TARGET-"


def _money(value: float) -> str:
    return f"R$ {value:,.2f}"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candidate_snapshot(lead: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "strategy",
        "source_url",
        "origin",
        "city",
        "neighborhood",
        "street",
        "property_type",
        "asking_price",
        "market_value_estimate",
        "private_area_m2",
        "bedrooms",
        "parking_spaces",
        "occupancy_status",
        "renovation_type",
        "renovation_budget",
        "sale_comparables_count",
        "rent_comparables_count",
        "carrying_months",
        "monthly_carrying_cost",
        "acquisition_costs",
        "selling_commission_pct",
        "cash_needed",
        "estimated_sale_base",
        "estimated_sale_conservative",
        "estimated_sale_optimistic",
        "plan_b",
        "notes",
        "source_validation_status",
        "source_validation_reason",
        "source_checked_at",
    ]
    snapshot = {field: lead.get(field) for field in fields if field in lead}
    snapshot["source_validation"] = analysis.get("source_validation") or {}
    return snapshot


def _enriched_lead(lead: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(lead)
    market_value = _number(enriched.get("market_value_estimate"))
    sale_base = _number(enriched.get("estimated_sale_base"), market_value)
    if sale_base <= 0:
        sale_base = market_value
    enriched.setdefault("estimated_sale_base", sale_base)
    if sale_base > 0:
        enriched.setdefault("estimated_sale_conservative", round(sale_base * 0.92, 2))
        enriched.setdefault("estimated_sale_optimistic", round(sale_base * 1.05, 2))
    asking_price = _number(enriched.get("asking_price"))
    enriched.setdefault("acquisition_costs", round(asking_price * 0.08, 2))
    enriched.setdefault("selling_commission_pct", 6.0)
    enriched.setdefault("sale_comparables_count", 0)
    enriched.setdefault("rent_comparables_count", 0)
    enriched.setdefault("target_roi_pct", 20.0)
    enriched.setdefault("source_checked_at", enriched.get("observed_at", ""))
    note_parts = [
        f"Garimpo alvo: {enriched.get('neighborhood')} / {enriched.get('street')}.",
        "Valor de saida inicial vem do valor de referencia publicado; exige comparaveis equivalentes antes de proposta.",
    ]
    if enriched.get("notes"):
        note_parts.append(str(enriched["notes"]))
    enriched["notes"] = " ".join(part for part in note_parts if part)
    return enriched


def _operation_row(lead: dict[str, Any], thesis_number: int) -> dict[str, Any]:
    enriched = _enriched_lead(lead)
    analysis = build_candidate_analysis(enriched)
    analysis = {
        **analysis,
        "candidate": _candidate_snapshot(enriched, analysis),
        "summary": (
            "Candidato de bairro-alvo capturado em garimpo online; manter aberto "
            "somente enquanto fonte, demanda local e valor de saida forem provados."
        ),
    }
    candidate = analysis["candidate"]
    asking_price = round(_number(enriched.get("asking_price")), 2)
    sale_base = round(_number(enriched.get("estimated_sale_base"), _number(enriched.get("market_value_estimate"))), 2)
    max_purchase_price = round(_number(analysis.get("max_purchase_price")), 2)
    cash_needed = round(_number(analysis.get("cash_needed")), 2)
    base_scenario = analysis.get("scenarios", {}).get("base", {})
    roi_pct = round(_number(base_scenario.get("roi_pct")), 4)
    next_action = str(analysis.get("next_action") or "Validar candidato").strip()
    pending_titles = [
        str(item.get("title") or "").strip()
        for item in analysis.get("pending_items", [])[:3]
        if isinstance(item, dict) and str(item.get("title") or "").strip()
    ]
    pending_summary = ", ".join(pending_titles) if pending_titles else "sem P0 critico"
    price_ceiling_status = str(analysis.get("price_ceiling_status") or "Teto a validar")
    thesis_id = f"{TARGET_PREFIX}{enriched['id_suffix']}"
    observed_at = str(enriched.get("observed_at") or "2026-05-20T21:00:00-03:00")

    return {
        "phase": "pos_go_live",
        "thesis_number": thesis_number,
        "thesis_id": thesis_id,
        "thesis_raised_at": observed_at,
        "front": "imoveis",
        "source_url": enriched.get("source_url"),
        "source_validation": analysis.get("source_validation") or {},
        "source_validation_status": analysis.get("source_validation", {}).get("status", ""),
        "source_validation_reason": analysis.get("source_validation", {}).get("reason", ""),
        "source_checked_at": analysis.get("source_validation", {}).get("checked_at", ""),
        "asset": enriched.get("title"),
        "action": enriched.get("title"),
        "thesis_reason": (
            f"Radar de bairro-alvo: {candidate.get('city')} / {candidate.get('neighborhood')} / "
            f"{candidate.get('street')}. Score {analysis.get('score')}/100, "
            f"confianca {analysis.get('confidence')}/100."
        ),
        "expected_result_pct": roi_pct,
        "operation_plan": (
            f"Entrada {_money(asking_price)} | Saida base {_money(sale_base)} | "
            f"Teto Halley {_money(max_purchase_price)} | Caixa {_money(cash_needed)} | "
            f"Proximo passo: {next_action}"
        ),
        "structured_operation": (
            f"{enriched.get('strategy')} | {enriched.get('origin')} | "
            f"{enriched.get('property_type')} | {price_ceiling_status}"
        ),
        "entry_price_brl": asking_price,
        "current_price_brl": sale_base,
        "latest_price_at": observed_at,
        "planned_exit_at": (date(2026, 5, 20) + timedelta(days=14)).isoformat(),
        "exit_rule": next_action,
        "status": "Aberta - Atencao",
        "outcome": "Pendencias abertas",
        "moment_result_pct": 0.0,
        "duration_days": None,
        "open_days": 0,
        "learning_note": f"Antes de proposta: {next_action}. Pendencias principais: {pending_summary}.",
        "is_open": True,
        "real_estate_analysis": analysis,
    }


def seed_target_candidates() -> int:
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    leads = json.loads(LEADS_PATH.read_text(encoding="utf-8"))
    operations = payload.get("thesis_open_operations")
    if not isinstance(operations, list):
        raise ValueError("dashboard_seed.json nao contem thesis_open_operations.")

    retained = [
        row
        for row in operations
        if not str(row.get("thesis_id") or "").startswith(TARGET_PREFIX)
    ]
    max_thesis_number = max(
        [int(row.get("thesis_number") or 0) for row in retained if isinstance(row, dict)]
        or [0]
    )
    generated = [
        _operation_row(lead, max_thesis_number + index + 1)
        for index, lead in enumerate(leads)
    ]
    payload["thesis_open_operations"] = retained + generated
    SEED_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(generated)


if __name__ == "__main__":
    count = seed_target_candidates()
    print(f"Seeded {count} target real estate candidates into {SEED_PATH}")

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from app.models import MarketTick, SuitabilityProfile
from app.services.audit import record_audit_event
from app.services.thesis_case_study import (
    ThesisSummary,
    _available_instruments,
    _enriched_thesis_candidates,
    _monitoring_timeline,
    _raw_candidates_from_ticks,
    _realized_financial_pct,
    _strategy_for_thesis,
    _ticks_for_instrument,
)
from app.services.thesis_policy import apply_active_policy
from app.services.utils import DISCLAIMER
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


class CurrentThesisCard(TypedDict):
    thesis_id: str
    instrument: str
    direction: str
    why_thesis: list[str]
    reason_category: str
    thesis_raised_at: str
    suggested_entry_time: str
    suggested_exit_time: str
    entry_price: float
    target_price: float
    stop_price: float
    suggested_operation: dict[str, object]
    latest_price: float
    latest_event_time: str
    monitor_status: str
    suggested_action: str
    expected_financial_pct: float
    unrealized_financial_pct: float
    confidence_tese_pct: float
    progress_to_target_pct: float
    distance_to_stop_pct: float
    monitoring_events: list[dict[str, object]]


class CurrentThesisMonitorPayload(TypedDict):
    generated_at: str
    user_id: int
    horizon_bars: int
    recent_bars_window: int
    thesis_count: int
    scan_scope: dict[str, object]
    summary: dict[str, object]
    theses: list[CurrentThesisCard]
    disclaimer: str


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _reason_category(signals: list[str]) -> str:
    signal_str = " ".join(item.lower() for item in signals)
    categories: list[str] = []
    if "momento_" in signal_str or "suporte_tecnico_" in signal_str:
        categories.append("grafico/tecnico")
    if "fundamental_" in signal_str or "valuation_" in signal_str or "roe_" in signal_str:
        categories.append("fundamentalista")
    if "news_sentiment_" in signal_str:
        categories.append("noticias/contexto externo")
    if "geo_oil_context_" in signal_str:
        categories.append("geopolitico")
    if not categories:
        return "misto"
    return " + ".join(dict.fromkeys(categories))


def _is_current_candidate(
    thesis: ThesisSummary,
    ticks: list[MarketTick],
    recent_bars_window: int,
) -> bool:
    latest_index = len(ticks) - 1
    if latest_index <= 0:
        return False
    # "Tese atual": foi levantada recentemente e ainda esta dentro da janela de monitoramento.
    if thesis["entry_index"] < latest_index - recent_bars_window:
        return False
    if thesis["entry_index"] >= latest_index:
        return False
    return True


def _progress_metrics(thesis: ThesisSummary, latest_price: float) -> tuple[float, float]:
    entry_price = thesis["entry_price"]
    target_price = thesis["target_price"]
    stop_price = thesis["stop_price"]
    direction = thesis["direction"]
    if entry_price <= 0:
        return 0.0, 0.0

    if direction == "bullish":
        total_target_move = max(target_price - entry_price, 0.0001)
        progress = ((latest_price - entry_price) / total_target_move) * 100
        stop_distance = ((latest_price - stop_price) / entry_price) * 100
    elif direction == "bearish":
        total_target_move = max(entry_price - target_price, 0.0001)
        progress = ((entry_price - latest_price) / total_target_move) * 100
        stop_distance = ((stop_price - latest_price) / entry_price) * 100
    else:
        progress = 0.0
        stop_distance = ((latest_price - stop_price) / entry_price) * 100

    return round(_clamp(progress, -150.0, 150.0), 4), round(stop_distance, 4)


def _monitor_status_and_action(
    thesis: ThesisSummary,
    latest_price: float,
) -> tuple[str, str]:
    direction = thesis["direction"]
    target_price = thesis["target_price"]
    stop_price = thesis["stop_price"]

    if direction == "bullish":
        if latest_price >= target_price:
            return "target_hit", "realizar_saida_parcial_ou_total"
        if latest_price <= stop_price:
            return "stop_alert", "reduzir_risco_ou_encerrar"
        return "monitoring", "manter_monitoramento"
    if direction == "bearish":
        if latest_price <= target_price:
            return "target_hit", "realizar_saida_parcial_ou_total"
        if latest_price >= stop_price:
            return "stop_alert", "reduzir_risco_ou_encerrar"
        return "monitoring", "manter_monitoramento"
    return "monitoring", "manter_monitoramento"


def run_current_thesis_monitor(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 8,
    thesis_count: int = 8,
    recent_bars_window: int = 7,
) -> CurrentThesisMonitorPayload:
    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    if profile is None:
        raise ValueError("Suitability obrigatorio para monitoramento de teses atuais.")

    instrument_list = _available_instruments(db, instruments)
    if not instrument_list:
        raise ValueError("Nao ha historico de mercado para monitorar teses atuais.")

    raw_candidates = []
    ticks_by_instrument: dict[str, list[MarketTick]] = {}
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        ticks_by_instrument[instrument] = ticks
        raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))
    if not raw_candidates:
        raise ValueError("Historico insuficiente para gerar teses atuais.")

    enriched = _enriched_thesis_candidates(db, raw_candidates)
    policy_candidates, policy_metadata = apply_active_policy(enriched)

    current_candidates: list[ThesisSummary] = []
    for thesis in policy_candidates:
        ticks = ticks_by_instrument.get(thesis["instrument"], [])
        if _is_current_candidate(thesis, ticks, recent_bars_window):
            current_candidates.append(thesis)
    if not current_candidates:
        raise ValueError("Nenhuma tese atual encontrada no recorte configurado.")

    selected = sorted(
        current_candidates,
        key=lambda item: (item["confidence_tese_pct"], item["expected_financial_pct"]),
        reverse=True,
    )[:thesis_count]

    cards: list[CurrentThesisCard] = []
    for thesis in selected:
        ticks = ticks_by_instrument[thesis["instrument"]]
        latest_tick = ticks[-1]
        latest_price = round(float(latest_tick.price), 4)
        latest_index = len(ticks) - 1
        operation = _strategy_for_thesis(thesis, profile.investor_profile)
        unrealized_financial_pct = _realized_financial_pct(operation, thesis, latest_price)
        progress_to_target_pct, distance_to_stop_pct = _progress_metrics(thesis, latest_price)
        monitor_status, suggested_action = _monitor_status_and_action(thesis, latest_price)
        monitoring_events = _monitoring_timeline(
            ticks,
            thesis,
            operation,
            thesis["entry_index"],
            latest_index,
        )
        cards.append(
            {
                "thesis_id": thesis["thesis_id"],
                "instrument": thesis["instrument"],
                "direction": thesis["direction"],
                "why_thesis": thesis["supporting_signals"][:6],
                "reason_category": _reason_category(thesis["supporting_signals"]),
                "thesis_raised_at": thesis["entry_time"],
                "suggested_entry_time": thesis["entry_time"],
                "suggested_exit_time": latest_tick.event_time,
                "entry_price": thesis["entry_price"],
                "target_price": thesis["target_price"],
                "stop_price": thesis["stop_price"],
                "suggested_operation": operation,
                "latest_price": latest_price,
                "latest_event_time": latest_tick.event_time,
                "monitor_status": monitor_status,
                "suggested_action": suggested_action,
                "expected_financial_pct": thesis["expected_financial_pct"],
                "unrealized_financial_pct": unrealized_financial_pct,
                "confidence_tese_pct": thesis["confidence_tese_pct"],
                "progress_to_target_pct": progress_to_target_pct,
                "distance_to_stop_pct": distance_to_stop_pct,
                "monitoring_events": monitoring_events[-6:],
            }
        )

    target_hits = sum(1 for card in cards if card["monitor_status"] == "target_hit")
    stop_alerts = sum(1 for card in cards if card["monitor_status"] == "stop_alert")
    monitoring_count = sum(1 for card in cards if card["monitor_status"] == "monitoring")
    avg_unrealized = (
        round(sum(card["unrealized_financial_pct"] for card in cards) / len(cards), 4)
        if cards
        else 0.0
    )

    payload: CurrentThesisMonitorPayload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "user_id": user_id,
        "horizon_bars": horizon_bars,
        "recent_bars_window": recent_bars_window,
        "thesis_count": len(cards),
        "scan_scope": {
            "instruments": instrument_list,
            "tick_count": sum(len(items) for items in ticks_by_instrument.values()),
            "candidate_count": len(enriched),
            "policy_candidate_count": len(policy_candidates),
            "current_candidate_count": len(current_candidates),
            "policy": policy_metadata,
        },
        "summary": {
            "target_hits": target_hits,
            "stop_alerts": stop_alerts,
            "monitoring_count": monitoring_count,
            "avg_unrealized_financial_pct": avg_unrealized,
        },
        "theses": cards,
        "disclaimer": DISCLAIMER,
    }
    record_audit_event(
        db,
        "thesis.current_monitor.generated",
        {
            "user_id": user_id,
            "thesis_count": len(cards),
            "target_hits": target_hits,
            "stop_alerts": stop_alerts,
            "avg_unrealized_financial_pct": avg_unrealized,
        },
        user_id,
    )
    return payload


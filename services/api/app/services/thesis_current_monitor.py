from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypedDict

from app.db import BASE_DIR, DATA_DIR
from app.models import AuditEvent, MarketTick, SuitabilityProfile
from app.services.audit import record_audit_event
from app.services.notifications import notify_current_thesis_monitor
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
from app.services.thesis_operation_revaluation import (
    OperationRevaluation,
    build_operation_revaluation,
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
    confidence_now_pct: float
    confidence_delta_pct: float
    support_rate_pct: float
    technical_support_pct: float
    fundamental_support_pct: float
    news_support_pct: float
    geo_oil_support_pct: float
    fundamental_available: bool
    news_available: bool
    geo_oil_available: bool
    progress_to_target_pct: float
    distance_to_stop_pct: float
    executive_status: str
    executive_status_label: str
    executive_action: str
    thesis_validity: str
    revaluation_reason: str
    next_trigger: str
    learning_signal: str
    operation_revaluation: OperationRevaluation
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


def persist_current_thesis_monitor_snapshot(
    db: Session,
    payload: CurrentThesisMonitorPayload | dict[str, object],
    *,
    user_id: int,
) -> None:
    output_path = DATA_DIR / "current_thesis_monitor_latest.json"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    record_audit_event(
        db,
        "thesis.current_monitor.snapshot",
        {"payload": payload},
        user_id,
    )


def load_latest_current_thesis_monitor(
    db: Session,
    *,
    user_id: int | None = None,
) -> dict[str, object] | None:
    output_path = DATA_DIR / "current_thesis_monitor_latest.json"
    if output_path.exists():
        try:
            return json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    statement = (
        select(AuditEvent)
        .where(AuditEvent.event_type == "thesis.current_monitor.snapshot")
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    if user_id is not None:
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.event_type == "thesis.current_monitor.snapshot",
                AuditEvent.user_id == user_id,
            )
            .order_by(AuditEvent.id.desc())
            .limit(1)
        )
    event = db.scalar(statement)
    if event is not None:
        try:
            details = json.loads(event.details)
        except ValueError:
            details = None
        if isinstance(details, dict):
            payload = details.get("payload")
            if isinstance(payload, dict):
                return payload
            if "generated_at" in details and "theses" in details:
                return details
    bundled_bootstrap_path = BASE_DIR / "data" / "current_thesis_monitor_bootstrap.json"
    if bundled_bootstrap_path.exists():
        try:
            return json.loads(bundled_bootstrap_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    return None


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


def _parse_event_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_latest_tick_fresh(
    ticks: list[object],
    max_latest_age_days: int | None,
    reference_time: datetime,
) -> bool:
    if max_latest_age_days is None or max_latest_age_days <= 0:
        return True
    if not ticks:
        return False
    latest_time = _parse_event_datetime(getattr(ticks[-1], "event_time", ""))
    if latest_time is None:
        return False
    reference_utc = (
        reference_time.replace(tzinfo=UTC)
        if reference_time.tzinfo is None
        else reference_time.astimezone(UTC)
    )
    age_days = (reference_utc - latest_time).total_seconds() / 86400.0
    return age_days <= float(max_latest_age_days)


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
    if direction == "range":
        lower_bound = min(target_price, stop_price)
        upper_bound = max(target_price, stop_price)
        if latest_price < lower_bound or latest_price > upper_bound:
            return "stop_alert", "reduzir_risco_ou_encerrar"
    return "monitoring", "manter_monitoramento"


def _planned_exit_time(
    ticks: list[MarketTick],
    thesis: ThesisSummary,
) -> str:
    entry_index = int(thesis.get("entry_index", -1))
    horizon_bars = int(thesis.get("horizon_bars", 0))
    exit_index = entry_index + horizon_bars
    if entry_index < 0 or horizon_bars <= 0 or exit_index <= entry_index:
        return ""
    if exit_index >= len(ticks):
        return ""
    return str(ticks[exit_index].event_time)


def _select_current_candidates(
    current_candidates: list[ThesisSummary],
    *,
    thesis_count: int,
    distinct_instruments: bool = False,
    prefer_recent: bool = False,
) -> list[ThesisSummary]:
    if prefer_recent:
        sort_key = lambda item: (  # noqa: E731
            int(item.get("entry_index", 0)),
            item["confidence_tese_pct"],
            item["expected_financial_pct"],
        )
    else:
        sort_key = lambda item: (  # noqa: E731
            item["confidence_tese_pct"],
            item["expected_financial_pct"],
        )
    sorted_candidates = sorted(
        current_candidates,
        key=sort_key,
        reverse=True,
    )
    if not distinct_instruments:
        return sorted_candidates[:thesis_count]

    selected: list[ThesisSummary] = []
    seen_instruments: set[str] = set()
    for thesis in sorted_candidates:
        instrument = str(thesis["instrument"]).upper()
        if instrument in seen_instruments:
            continue
        selected.append(thesis)
        seen_instruments.add(instrument)
        if len(selected) >= thesis_count:
            break
    return selected


def run_current_thesis_monitor(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 8,
    thesis_count: int = 8,
    recent_bars_window: int = 7,
    distinct_instruments: bool = False,
    prefer_recent: bool = False,
    max_latest_age_days: int | None = None,
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
    reference_time = datetime.now(UTC)
    fresh_instruments: list[str] = []
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        if not _is_latest_tick_fresh(ticks, max_latest_age_days, reference_time):
            continue
        fresh_instruments.append(instrument)
        ticks_by_instrument[instrument] = ticks
        raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))
    if not raw_candidates:
        raise ValueError("Historico recente insuficiente para gerar teses atuais.")

    enriched = _enriched_thesis_candidates(db, raw_candidates)
    policy_candidates, policy_metadata = apply_active_policy(enriched)

    current_candidates: list[ThesisSummary] = []
    for thesis in policy_candidates:
        ticks = ticks_by_instrument.get(thesis["instrument"], [])
        if _is_current_candidate(thesis, ticks, recent_bars_window):
            current_candidates.append(thesis)
    if not current_candidates:
        raise ValueError("Nenhuma tese atual encontrada no recorte configurado.")

    selected = _select_current_candidates(
        current_candidates,
        thesis_count=thesis_count,
        distinct_instruments=distinct_instruments,
        prefer_recent=prefer_recent,
    )

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
        revaluation = build_operation_revaluation(
            thesis,
            latest_price=latest_price,
            monitor_status=monitor_status,
            unrealized_financial_pct=unrealized_financial_pct,
            progress_to_target_pct=progress_to_target_pct,
            distance_to_stop_pct=distance_to_stop_pct,
        )
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
                "suggested_exit_time": _planned_exit_time(ticks, thesis),
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
                "confidence_now_pct": revaluation["confidence_now_pct"],
                "confidence_delta_pct": revaluation["confidence_delta_pct"],
                "support_rate_pct": thesis["support_rate_pct"],
                "technical_support_pct": thesis["technical_support_pct"],
                "fundamental_support_pct": thesis["fundamental_support_pct"],
                "news_support_pct": thesis["news_support_pct"],
                "geo_oil_support_pct": thesis["geo_oil_support_pct"],
                "fundamental_available": thesis["fundamental_available"],
                "news_available": thesis["news_available"],
                "geo_oil_available": thesis["geo_oil_available"],
                "progress_to_target_pct": progress_to_target_pct,
                "distance_to_stop_pct": distance_to_stop_pct,
                "executive_status": revaluation["executive_status"],
                "executive_status_label": revaluation["executive_status_label"],
                "executive_action": revaluation["suggested_action"],
                "thesis_validity": revaluation["thesis_validity"],
                "revaluation_reason": revaluation["revaluation_reason"],
                "next_trigger": revaluation["next_trigger"],
                "learning_signal": revaluation["learning_signal"],
                "operation_revaluation": revaluation,
                "monitoring_events": monitoring_events[-6:],
            }
        )

    target_hits = sum(1 for card in cards if card["monitor_status"] == "target_hit")
    stop_alerts = sum(1 for card in cards if card["monitor_status"] == "stop_alert")
    monitoring_count = sum(1 for card in cards if card["monitor_status"] == "monitoring")
    executive_status_counts: dict[str, int] = {}
    for card in cards:
        status = card["executive_status"]
        executive_status_counts[status] = executive_status_counts.get(status, 0) + 1
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
            "fresh_instruments": fresh_instruments,
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
            "executive_status_counts": executive_status_counts,
            "needs_attention_count": executive_status_counts.get("atencao", 0)
            + executive_status_counts.get("invalidada", 0)
            + executive_status_counts.get("revisar_saida", 0),
        },
        "theses": cards,
        "disclaimer": DISCLAIMER,
    }
    persist_current_thesis_monitor_snapshot(db, payload, user_id=user_id)
    notify_current_thesis_monitor(db, payload)
    record_audit_event(
        db,
        "thesis.current_monitor.generated",
        {
            "user_id": user_id,
            "thesis_count": len(cards),
            "target_hits": target_hits,
            "stop_alerts": stop_alerts,
            "avg_unrealized_financial_pct": avg_unrealized,
            "executive_status_counts": executive_status_counts,
            "payload": payload,
        },
        user_id,
    )
    return payload

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from app.db import BASE_DIR, DATA_DIR
from app.models import AuditEvent, MarketTick, SuitabilityProfile
from app.services.audit import record_audit_event
from app.services.notifications import notify_current_thesis_monitor
from app.services.thesis_case_study import (
    RawCandidate,
    ThesisSummary,
    _available_instruments,
    _enriched_thesis_candidates,
    _live_candidates_from_ticks,
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

DEFAULT_CURRENT_MONITOR_INSTRUMENTS = (
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "ABEV3",
    "WEGE3",
    "B3SA3",
    "RENT3",
    "SUZB3",
    "JBSS3",
    "PRIO3",
    "RADL3",
    "GGBR4",
    "VBBR3",
    "LREN3",
    "HAPV3",
    "BPAC11",
    "RAIL3",
    "CMIG4",
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
)
DEFAULT_LATEST_TICK_FRESHNESS_MULTIPLIER = 3.0
DEFAULT_LATEST_TICK_MIN_AGE_SECONDS = 30 * 60


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
    range_lower_price: float | None
    range_upper_price: float | None
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


_NO_FRESH_MARKET_DATA_TOKEN = "nao ha dados de mercado frescos"


def _contract_issue(
    issues: list[dict[str, str]],
    code: str,
    message: str,
    *,
    severity: str = "error",
) -> None:
    issues.append({"severity": severity, "code": code, "message": message})


def _contract_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _contract_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _is_b3_instrument(instrument: str) -> bool:
    symbol = instrument.upper()
    return bool(symbol) and not symbol.endswith("USDT")


def _is_range_direction(direction: object) -> bool:
    normalized = str(direction or "").strip().lower()
    return normalized in {"range", "neutra", "neutral"}


def current_monitor_contract_issues(
    payload: dict[str, object],
    *,
    reference_time: datetime | None = None,
    enforce_fresh_b3: bool = False,
    b3_max_current_age_hours: int = 96,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    reference = reference_time or datetime.now(UTC)
    reference = (
        reference.replace(tzinfo=UTC)
        if reference.tzinfo is None
        else reference.astimezone(UTC)
    )

    theses_raw = payload.get("theses")
    theses = (
        [item for item in theses_raw if isinstance(item, dict)]
        if isinstance(theses_raw, list)
        else []
    )
    if _contract_float(payload.get("thesis_count")) != float(len(theses)):
        _contract_issue(
            issues,
            "payload.thesis_count.mismatch",
            "thesis_count nao bate com a quantidade de teses.",
        )

    summary = payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    expected_status_counts = {
        "target_hits": sum(1 for item in theses if str(item.get("monitor_status")) == "target_hit"),
        "stop_alerts": sum(1 for item in theses if str(item.get("monitor_status")) == "stop_alert"),
        "monitoring_count": sum(
            1 for item in theses if str(item.get("monitor_status")) == "monitoring"
        ),
    }
    for key, expected in expected_status_counts.items():
        if _contract_float(summary_dict.get(key)) != float(expected):
            _contract_issue(
                issues,
                f"summary.{key}.mismatch",
                f"{key} nao bate com os status das teses.",
            )

    for index, thesis in enumerate(theses):
        prefix = f"theses.{index}"
        instrument = str(thesis.get("instrument") or "").upper()
        direction = str(thesis.get("direction") or "").lower()
        if not instrument:
            _contract_issue(issues, f"{prefix}.instrument.missing", "Tese sem instrumento.")
        if direction not in {"bullish", "bearish", "range"}:
            _contract_issue(issues, f"{prefix}.direction.invalid", "Direcao da tese invalida.")

        for field in ("thesis_raised_at", "latest_event_time"):
            observed_at = _contract_datetime(thesis.get(field))
            if observed_at is None:
                _contract_issue(
                    issues,
                    f"{prefix}.{field}.missing",
                    f"{field} ausente ou invalido.",
                )
                continue
            if observed_at > reference + timedelta(seconds=60):
                _contract_issue(issues, f"{prefix}.{field}.future", f"{field} esta no futuro.")

        latest_event_time = _contract_datetime(thesis.get("latest_event_time"))
        if (
            enforce_fresh_b3
            and _is_b3_instrument(instrument)
            and latest_event_time is not None
            and reference - latest_event_time > timedelta(hours=b3_max_current_age_hours)
        ):
            _contract_issue(
                issues,
                f"{prefix}.b3.stale_current",
                "Tese B3 antiga nao pode ser publicada como monitor atual.",
            )

        entry_price = _contract_float(thesis.get("entry_price"))
        target_price = _contract_float(thesis.get("target_price"))
        stop_price = _contract_float(thesis.get("stop_price"))
        if entry_price is None or entry_price <= 0:
            _contract_issue(issues, f"{prefix}.entry_price.invalid", "Entrada invalida.")
            continue
        if target_price is None or target_price <= 0:
            _contract_issue(issues, f"{prefix}.target_price.invalid", "Alvo/centro invalido.")
            continue
        if stop_price is None or stop_price <= 0:
            _contract_issue(issues, f"{prefix}.stop_price.invalid", "Stop invalido.")
            continue

        if _is_range_direction(direction):
            range_lower = _contract_float(thesis.get("range_lower_price"))
            range_upper = _contract_float(thesis.get("range_upper_price"))
            if range_lower is None or range_upper is None:
                _contract_issue(
                    issues,
                    f"{prefix}.range.bounds",
                    "Tese range precisa de range_lower_price e range_upper_price.",
                )
                continue
            if range_lower >= range_upper:
                _contract_issue(issues, f"{prefix}.range.bounds_order", "Faixa range invalida.")
            if not range_lower <= entry_price <= range_upper:
                _contract_issue(
                    issues,
                    f"{prefix}.range.entry_outside",
                    "Entrada/centro fora da faixa range.",
                )
        elif direction == "bullish":
            if abs(target_price - entry_price) <= 0.0001:
                _contract_issue(
                    issues,
                    f"{prefix}.target.same_as_entry",
                    "Tese direcional com entrada igual ao alvo.",
                )
            if target_price <= entry_price:
                _contract_issue(
                    issues,
                    f"{prefix}.target.not_above_entry",
                    "Alvo bullish precisa ficar acima da entrada.",
                )
            if stop_price >= entry_price:
                _contract_issue(
                    issues,
                    f"{prefix}.stop.not_below_entry",
                    "Stop bullish precisa ficar abaixo da entrada.",
                )
        elif direction == "bearish":
            if abs(target_price - entry_price) <= 0.0001:
                _contract_issue(
                    issues,
                    f"{prefix}.target.same_as_entry",
                    "Tese direcional com entrada igual ao alvo.",
                )
            if target_price >= entry_price:
                _contract_issue(
                    issues,
                    f"{prefix}.target.not_below_entry",
                    "Alvo bearish precisa ficar abaixo da entrada.",
                )
            if stop_price <= entry_price:
                _contract_issue(
                    issues,
                    f"{prefix}.stop.not_above_entry",
                    "Stop bearish precisa ficar acima da entrada.",
                )

    return issues


def _raise_for_current_monitor_contract(payload: dict[str, object]) -> None:
    errors = [
        issue
        for issue in current_monitor_contract_issues(payload)
        if issue["severity"] == "error"
    ]
    if errors:
        codes = ", ".join(issue["code"] for issue in errors[:6])
        raise ValueError(f"Payload de monitor atual inconsistente: {codes}")


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_no_fresh_empty_monitor_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if _safe_int(payload.get("thesis_count"), 0) != 0:
        return False
    theses_raw = payload.get("theses")
    if isinstance(theses_raw, list) and theses_raw:
        return False
    summary = payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    notes_raw = summary_dict.get("notes")
    notes = notes_raw if isinstance(notes_raw, list) else []
    return any(_NO_FRESH_MARKET_DATA_TOKEN in str(note).strip().lower() for note in notes)


def _monitor_payload_from_audit_event(event: AuditEvent) -> dict[str, object] | None:
    try:
        details = json.loads(event.details)
    except ValueError:
        return None
    if not isinstance(details, dict):
        return None
    payload = details.get("payload")
    if isinstance(payload, dict):
        return payload
    if "generated_at" in details and "theses" in details:
        return details
    return None


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
    include_bundled_bootstrap: bool = True,
) -> dict[str, object] | None:
    output_path = DATA_DIR / "current_thesis_monitor_latest.json"
    if output_path.exists():
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        else:
            if not _is_no_fresh_empty_monitor_payload(payload):
                return payload

    statement = (
        select(AuditEvent)
        .where(AuditEvent.event_type == "thesis.current_monitor.snapshot")
        .order_by(AuditEvent.id.desc())
        .limit(50)
    )
    if user_id is not None:
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.event_type == "thesis.current_monitor.snapshot",
                AuditEvent.user_id == user_id,
            )
            .order_by(AuditEvent.id.desc())
            .limit(50)
        )
    for event in db.scalars(statement).all():
        payload = _monitor_payload_from_audit_event(event)
        if payload is not None and not _is_no_fresh_empty_monitor_payload(payload):
            return payload
    if include_bundled_bootstrap:
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
    if thesis["entry_index"] > latest_index:
        return False
    if int(thesis.get("entry_index", -1)) + int(thesis.get("horizon_bars", 0)) <= latest_index:
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


def _infer_tick_interval_seconds(ticks: list[object]) -> float | None:
    recent_ticks = ticks[-10:]
    intervals: list[float] = []
    for previous_tick, current_tick in zip(recent_ticks, recent_ticks[1:], strict=False):
        previous_time = _parse_event_datetime(getattr(previous_tick, "event_time", ""))
        current_time = _parse_event_datetime(getattr(current_tick, "event_time", ""))
        if previous_time is None or current_time is None or current_time <= previous_time:
            continue
        intervals.append((current_time - previous_time).total_seconds())
    if not intervals:
        return None
    return sum(intervals) / len(intervals)


def _is_latest_tick_fresh(
    ticks: list[object],
    max_latest_age_days: int | None,
    reference_time: datetime,
) -> bool:
    if not ticks:
        return False
    latest_time = _parse_event_datetime(getattr(ticks[-1], "event_time", ""))
    if latest_time is None:
        return False
    if max_latest_age_days is not None and max_latest_age_days > 0:
        max_age_seconds = float(max_latest_age_days) * 86400.0
    else:
        inferred_interval_seconds = _infer_tick_interval_seconds(ticks)
        if inferred_interval_seconds is None or inferred_interval_seconds <= 0:
            return False
        max_age_seconds = max(
            inferred_interval_seconds * DEFAULT_LATEST_TICK_FRESHNESS_MULTIPLIER,
            float(DEFAULT_LATEST_TICK_MIN_AGE_SECONDS),
        )
    reference_utc = (
        reference_time.replace(tzinfo=UTC)
        if reference_time.tzinfo is None
        else reference_time.astimezone(UTC)
    )
    age_seconds = (reference_utc - latest_time).total_seconds()
    if age_seconds <= 0:
        return True
    return age_seconds <= max_age_seconds


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
        range_lower = float(thesis.get("range_lower_price") or stop_price)
        range_upper = float(thesis.get("range_upper_price") or target_price or entry_price)
        if latest_price < range_lower:
            stop_distance = ((latest_price - range_lower) / entry_price) * 100
        elif latest_price > range_upper:
            stop_distance = ((range_upper - latest_price) / entry_price) * 100
        else:
            stop_distance = (
                min(latest_price - range_lower, range_upper - latest_price) / entry_price
            ) * 100

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
        lower_bound = float(thesis.get("range_lower_price") or min(target_price, stop_price))
        upper_bound = float(thesis.get("range_upper_price") or max(target_price, stop_price))
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
        latest_time = _parse_event_datetime(getattr(ticks[-1], "event_time", "")) if ticks else None
        if latest_time is None:
            return ""
        intervals: list[float] = []
        for previous_tick, current_tick in zip(ticks[-10:], ticks[-9:], strict=False):
            previous_time = _parse_event_datetime(getattr(previous_tick, "event_time", ""))
            current_time = _parse_event_datetime(getattr(current_tick, "event_time", ""))
            if previous_time is None or current_time is None or current_time <= previous_time:
                continue
            intervals.append((current_time - previous_time).total_seconds())
        if not intervals:
            return ""
        average_interval = sum(intervals) / len(intervals)
        if average_interval <= 0:
            return ""
        remaining_bars = exit_index - (len(ticks) - 1)
        estimated_exit = latest_time + timedelta(seconds=average_interval * remaining_bars)
        return estimated_exit.replace(microsecond=0).isoformat()
    return str(ticks[exit_index].event_time)


def _resolve_monitor_instruments(
    db: Session,
    instruments: list[str] | None,
) -> list[str]:
    requested_instruments = instruments or list(DEFAULT_CURRENT_MONITOR_INSTRUMENTS)
    return _available_instruments(db, requested_instruments)


def _current_window_raw_candidates(
    raw_candidates: list[RawCandidate],
    *,
    latest_index_by_instrument: dict[str, int],
    recent_bars_window: int,
) -> list[RawCandidate]:
    filtered: list[RawCandidate] = []
    for candidate in raw_candidates:
        instrument = str(candidate["instrument"]).upper()
        latest_index = latest_index_by_instrument.get(instrument, -1)
        entry_index = int(candidate["entry_index"])
        if latest_index <= 0:
            continue
        if entry_index < latest_index - recent_bars_window:
            continue
        if entry_index >= latest_index:
            continue
        filtered.append(candidate)
    return filtered


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

    instrument_list = _resolve_monitor_instruments(db, instruments)
    if not instrument_list:
        raise ValueError("Nao ha historico de mercado para monitorar teses atuais.")

    historical_candidates: list[RawCandidate] = []
    live_candidates: list[RawCandidate] = []
    ticks_by_instrument: dict[str, list[MarketTick]] = {}
    latest_index_by_instrument: dict[str, int] = {}
    reference_time = datetime.now(UTC)
    fresh_instruments: list[str] = []
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        if not _is_latest_tick_fresh(ticks, max_latest_age_days, reference_time):
            continue
        fresh_instruments.append(instrument)
        ticks_by_instrument[instrument] = ticks
        latest_index_by_instrument[instrument] = len(ticks) - 1
        historical_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))
        live_candidates.extend(
            _live_candidates_from_ticks(
                instrument,
                ticks,
                horizon_bars,
                recent_bars_window,
            )
        )
    if instrument_list and not fresh_instruments:
        raise ValueError("Nao ha dados de mercado frescos para monitorar teses atuais.")
    current_window_candidates = _current_window_raw_candidates(
        historical_candidates,
        latest_index_by_instrument=latest_index_by_instrument,
        recent_bars_window=recent_bars_window,
    )
    enriched: list[ThesisSummary] = []
    policy_candidates: list[ThesisSummary] = []
    policy_metadata: dict[str, object] = {}
    current_candidates: list[ThesisSummary] = []
    candidate_batches: list[tuple[list[RawCandidate], list[RawCandidate] | None]] = [
        (current_window_candidates, None),
        (live_candidates, historical_candidates),
    ]
    for candidate_inputs, support_candidates in candidate_batches:
        if not candidate_inputs:
            continue
        if support_candidates is None:
            batch_enriched = _enriched_thesis_candidates(db, candidate_inputs)
        else:
            batch_enriched = _enriched_thesis_candidates(
                db,
                candidate_inputs,
                support_candidates=support_candidates,
            )
        batch_policy_candidates, batch_policy_metadata = apply_active_policy(batch_enriched)
        batch_current_candidates: list[ThesisSummary] = []
        for thesis in batch_policy_candidates:
            ticks = ticks_by_instrument.get(thesis["instrument"], [])
            if _is_current_candidate(thesis, ticks, recent_bars_window):
                batch_current_candidates.append(thesis)
        if not batch_current_candidates:
            continue
        enriched = batch_enriched
        policy_candidates = batch_policy_candidates
        policy_metadata = batch_policy_metadata
        current_candidates = batch_current_candidates
        break
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
        open_monitoring_window = (
            int(thesis.get("entry_index", -1)) + int(thesis.get("horizon_bars", 0)) > latest_index
        )
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
        if open_monitoring_window:
            monitoring_events = [
                event
                for event in monitoring_events
                if str(event.get("event_type") or "") != "exit_snapshot"
            ]
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
                "range_lower_price": thesis.get("range_lower_price"),
                "range_upper_price": thesis.get("range_upper_price"),
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
    _raise_for_current_monitor_contract(payload)
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

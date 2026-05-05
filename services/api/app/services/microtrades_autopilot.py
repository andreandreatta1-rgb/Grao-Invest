from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from app.db import BASE_DIR, DATA_DIR
from app.models import AuditEvent, AssistantDecision as AssistantDecisionRecord, MarketTick
from app.schemas import MarketTickIngestRequest, SuitabilityRequest
from app.services.audit import record_audit_event
from app.services.assistant_decisions import create_decision
from app.services.crypto_history_provider import (
    CryptoHistoryProviderError,
    fetch_historical_crypto_candles,
)
from app.services.intraday_provider import IntradayProviderError, fetch_intraday_quotes
from app.services.market import ingest_tick, ingest_tick_live, recompute_indicators, resolve_active_provider
from app.services.signals import generate_signal
from app.services.suitability import save_suitability
from app.services.thesis_case_study import run_thesis_case_study
from app.services.thesis_current_monitor import (
    load_latest_current_thesis_monitor,
    persist_current_thesis_monitor_snapshot,
    run_current_thesis_monitor,
)
from app.services.utils import DISCLAIMER, isoformat, utc_now
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session


class MicrotradesAutopilotConfig(TypedDict):
    user_id: int
    instruments: list[str]
    provider_name: str
    history_provider_name: str
    interval: str
    lookback_hours: int
    max_candles_per_instrument: int
    horizon_bars: int
    thesis_count: int
    recent_bars_window: int
    auto_recompute_indicators: bool
    allow_external_fetches: bool
    publish_decisions: bool
    decision_cooldown_minutes: int


class MicrotradesAutopilotPayload(TypedDict):
    run_started_at: str
    run_finished_at: str
    user_id: int
    status: str
    config: dict[str, object]
    steps: list[dict[str, object]]
    backfill: dict[str, object]
    live_ingestion: dict[str, object]
    signal: dict[str, object]
    case_study: dict[str, object]
    monitor: dict[str, object]
    decision: dict[str, object]
    error: str | None


def persist_microtrades_autopilot_snapshot(
    db: Session,
    payload: MicrotradesAutopilotPayload | dict[str, object],
    *,
    user_id: int,
    persist_audit_event: bool = True,
) -> None:
    output_path = DATA_DIR / "microtrades_autopilot_latest.json"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    if persist_audit_event:
        record_audit_event(
            db,
            "microtrades.autopilot.snapshot",
            {"payload": payload},
            user_id,
        )


def load_latest_microtrades_autopilot_snapshot(
    db: Session,
    *,
    user_id: int | None = None,
    include_bundled_bootstrap: bool = True,
) -> dict[str, object] | None:
    output_path = DATA_DIR / "microtrades_autopilot_latest.json"
    if output_path.exists():
        try:
            return json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    statement = (
        select(AuditEvent)
        .where(AuditEvent.event_type == "microtrades.autopilot.snapshot")
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    if user_id is not None:
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.event_type == "microtrades.autopilot.snapshot",
                AuditEvent.user_id == user_id,
            )
            .order_by(AuditEvent.id.desc())
            .limit(1)
        )
    event = db.scalar(statement)
    if event is None:
        details = None
    else:
        try:
            details = json.loads(event.details)
        except ValueError:
            details = None
    if isinstance(details, dict):
        payload = details.get("payload")
        if isinstance(payload, dict):
            return payload
        if "run_started_at" in details and "steps" in details:
            return details

    if include_bundled_bootstrap:
        bundled_bootstrap_path = BASE_DIR / "data" / "microtrades_autopilot_latest.json"
        if bundled_bootstrap_path.exists():
            try:
                return json.loads(bundled_bootstrap_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
    return None


_INDICATORS_MISSING_TOKEN = "nao ha indicadores disponiveis"
_SUITABILITY_MISSING_TOKEN = "suitability obrigatorio"
_NO_CURRENT_THESES_TOKEN = "nenhuma tese atual encontrada"
_NO_FRESH_MARKET_DATA_TOKEN = "nao ha dados de mercado frescos"
_STALE_MONITOR_REUSED_NOTE = "Dados de mercado sem frescor; mantendo ultimo monitor valido."


def _autopilot_debug(config: MicrotradesAutopilotConfig, message: str) -> None:
    return None


def _normalize_instruments(instruments: list[str] | None) -> list[str]:
    normalized = []
    seen: set[str] = set()
    for item in instruments or []:
        key = str(item or "").strip().upper()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def build_microtrades_autopilot_config(
    *,
    user_id: int,
    instruments: list[str] | None = None,
    provider_name: str = "finnhub",
    history_provider_name: str = "binance",
    interval: str = "5m",
    lookback_hours: int = 168,
    max_candles_per_instrument: int = 1200,
    horizon_bars: int = 8,
    thesis_count: int = 8,
    recent_bars_window: int = 7,
    auto_recompute_indicators: bool = True,
    allow_external_fetches: bool = True,
    publish_decisions: bool = True,
    decision_cooldown_minutes: int = 45,
) -> MicrotradesAutopilotConfig:
    normalized_instruments = _normalize_instruments(instruments)
    if not normalized_instruments:
        normalized_instruments = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    return {
        "user_id": int(user_id),
        "instruments": normalized_instruments[:10],
        "provider_name": str(provider_name).strip() or "finnhub",
        "history_provider_name": str(history_provider_name).strip() or "binance",
        "interval": str(interval).strip() or "5m",
        "lookback_hours": max(1, min(int(lookback_hours), 24 * 365)),
        "max_candles_per_instrument": max(50, min(int(max_candles_per_instrument), 5000)),
        "horizon_bars": max(3, min(int(horizon_bars), 60)),
        "thesis_count": max(1, min(int(thesis_count), 30)),
        "recent_bars_window": max(2, min(int(recent_bars_window), 40)),
        "auto_recompute_indicators": bool(auto_recompute_indicators),
        "allow_external_fetches": bool(allow_external_fetches),
        "publish_decisions": bool(publish_decisions),
        "decision_cooldown_minutes": max(5, min(int(decision_cooldown_minutes), 24 * 12)),
    }


def _build_symbol_overrides(instruments: list[str]) -> dict[str, str] | None:
    overrides: dict[str, str] = {}
    for instrument in instruments:
        if (
            instrument.endswith(("USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH"))
            and ":" not in instrument
            and "-" not in instrument
        ):
            overrides[instrument] = f"BINANCE:{instrument}"
    return overrides or None


def _is_indicators_missing_error(message: str) -> bool:
    return _INDICATORS_MISSING_TOKEN in message.strip().lower()


def _is_suitability_missing_error(message: str) -> bool:
    return _SUITABILITY_MISSING_TOKEN in message.strip().lower()


def _is_no_current_theses_error(message: str) -> bool:
    normalized = message.strip().lower()
    return (
        _NO_CURRENT_THESES_TOKEN in normalized
        or _NO_FRESH_MARKET_DATA_TOKEN in normalized
    )


def _is_no_fresh_market_data_error(message: str) -> bool:
    return _NO_FRESH_MARKET_DATA_TOKEN in message.strip().lower()


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_iso_to_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _ensure_suitability_profile(db: Session, *, user_id: int) -> dict[str, object]:
    payload = SuitabilityRequest(
        user_id=user_id,
        time_horizon="medio",
        risk_tolerance="media",
        investment_experience="intermediaria",
        liquidity_need="media",
    )
    profile = save_suitability(db, payload)
    return {
        "profile_id": profile.id,
        "investor_profile": profile.investor_profile,
        "created_at": profile.created_at,
    }


def _interval_to_minutes(interval: str) -> int:
    raw = str(interval or "").strip().lower()
    if len(raw) < 2:
        return 5
    amount_str = raw[:-1]
    unit = raw[-1]
    if not amount_str.isdigit():
        return 5
    amount = max(1, int(amount_str))
    if unit == "m":
        return amount
    if unit == "h":
        return amount * 60
    if unit == "d":
        return amount * 24 * 60
    return 5


def _has_recent_history(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
    lookback_hours: int,
    max_candles_per_instrument: int,
) -> bool:
    interval_minutes = _interval_to_minutes(config["interval"])
    expected_candles = max(30, min(max_candles_per_instrument, int((lookback_hours * 60) / max(1, interval_minutes))))
    minimum_candles = max(config["horizon_bars"] + 26, int(expected_candles * 0.75))
    freshness_limit = timedelta(minutes=max(interval_minutes * 3, 30))
    for instrument in config["instruments"]:
        tick_count = int(
            db.scalar(
                select(func.count())
                .select_from(MarketTick)
                .where(MarketTick.instrument == instrument.upper())
            )
            or 0
        )
        latest_tick = db.scalar(
            select(MarketTick)
            .where(MarketTick.instrument == instrument.upper())
            .order_by(MarketTick.event_time.desc())
            .limit(1)
        )
        if latest_tick is None or tick_count < minimum_candles:
            return False
        latest_event_time = _safe_iso_to_utc(latest_tick.event_time)
        if latest_event_time is None:
            return False
        if utc_now() - latest_event_time > freshness_limit:
            return False
    return True


def _run_backfill(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
    lookback_hours: int | None = None,
    max_candles_per_instrument: int | None = None,
) -> dict[str, object]:
    if not config["allow_external_fetches"]:
        _autopilot_debug(config, "backfill: external fetches disabled")
        effective_lookback = (
            lookback_hours if lookback_hours is not None else config["lookback_hours"]
        )
        return {
            "provider_name": config["history_provider_name"],
            "interval": config["interval"],
            "lookback_hours": effective_lookback,
            "requested_candles": 0,
            "processed_count": 0,
            "failed_count": 0,
            "indicators_recomputed": [],
            "indicators_skipped": [],
            "skipped": True,
            "skip_reason": "external_fetches_disabled",
        }
    now = utc_now()
    effective_lookback = lookback_hours if lookback_hours is not None else config["lookback_hours"]
    effective_max_candles = (
        max_candles_per_instrument
        if max_candles_per_instrument is not None
        else config["max_candles_per_instrument"]
    )
    if _has_recent_history(
        db,
        config=config,
        lookback_hours=effective_lookback,
        max_candles_per_instrument=effective_max_candles,
    ):
        return {
            "provider_name": config["history_provider_name"],
            "interval": config["interval"],
            "lookback_hours": effective_lookback,
            "requested_candles": 0,
            "processed_count": 0,
            "failed_count": 0,
            "indicators_recomputed": [],
            "indicators_skipped": [],
            "skipped": True,
            "skip_reason": "historico_recente_ja_disponivel",
        }
    start_time = now - timedelta(hours=effective_lookback)
    symbol_overrides = _build_symbol_overrides(config["instruments"])
    candles = fetch_historical_crypto_candles(
        config["history_provider_name"],
        config["instruments"],
        config["interval"],
        start_time,
        now,
        symbol_overrides=symbol_overrides,
        max_candles_per_instrument=effective_max_candles,
    )
    provider_label = f"crypto-{config['history_provider_name'].lower()}-{config['interval']}"
    active_provider = resolve_active_provider(db, provider_label.lower())
    if active_provider is not None and active_provider.provider_name != provider_label.lower():
        raise ValueError(
            "Provedor inativo para ingestao no momento. Utilize o provedor ativo configurado."
        )
    source_payload_ids = [
        str(candle["source_payload_id"])
        for candle in candles
        if candle.get("source_payload_id") is not None
    ]
    existing_payload_ids = set(
        db.scalars(
            select(MarketTick.source_payload_id).where(
                MarketTick.provider == provider_label.lower(),
                MarketTick.instrument.in_([item.upper() for item in config["instruments"]]),
                MarketTick.source_payload_id.in_(source_payload_ids),
            )
        )
    )
    processed_count = len(candles)
    failed_count = 0
    ingested_instruments: set[str] = set()
    ingest_time = isoformat(utc_now())
    rows_to_insert: list[MarketTick] = []
    for candle in candles:
        try:
            instrument = str(candle["instrument"]).upper()
            source_payload_id = candle.get("source_payload_id")
            ingested_instruments.add(instrument)
            if source_payload_id is not None and str(source_payload_id) in existing_payload_ids:
                continue
            rows_to_insert.append(
                MarketTick(
                    instrument=instrument,
                    provider=provider_label.lower(),
                    event_time=isoformat(candle["event_time"]),
                    ingest_time=ingest_time,
                    price=float(candle["price"]),
                    volume=int(candle["volume"]),
                    currency=str(candle["currency"]),
                    source_payload_id=str(source_payload_id) if source_payload_id is not None else None,
                )
            )
        except (KeyError, TypeError, ValueError):
            failed_count += 1
    if rows_to_insert:
        db.add_all(rows_to_insert)
        db.commit()

    indicators_recomputed: list[str] = []
    indicators_skipped: list[str] = []
    if config["auto_recompute_indicators"]:
        for instrument in sorted(ingested_instruments):
            try:
                recompute_indicators(db, instrument)
                indicators_recomputed.append(instrument)
            except ValueError:
                indicators_skipped.append(instrument)

    return {
        "provider_name": config["history_provider_name"],
        "interval": config["interval"],
        "lookback_hours": effective_lookback,
        "requested_candles": len(candles),
        "processed_count": processed_count,
        "failed_count": failed_count,
        "indicators_recomputed": indicators_recomputed,
        "indicators_skipped": indicators_skipped,
    }


def _run_live_ingestion(db: Session, *, config: MicrotradesAutopilotConfig) -> dict[str, object]:
    if not config["allow_external_fetches"]:
        _autopilot_debug(config, "live_ingestion: external fetches disabled")
        return {
            "provider_name": config["provider_name"],
            "processed_count": 0,
            "failed_count": 0,
            "requested_instruments": config["instruments"],
            "skipped": True,
            "skip_reason": "external_fetches_disabled",
        }
    symbol_overrides = _build_symbol_overrides(config["instruments"])
    quotes = fetch_intraday_quotes(
        config["provider_name"],
        config["instruments"],
        symbol_overrides,
    )
    processed_count = 0
    failed_count = 0
    for quote in quotes:
        try:
            ingest_tick_live(
                db,
                MarketTickIngestRequest(
                    instrument=quote["instrument"],
                    provider=f"intraday-{quote['provider_name']}",
                    event_time=quote["event_time"],
                    price=quote["price"],
                    volume=quote["volume"],
                    currency=quote["currency"],
                    source_payload_id=quote["source_payload_id"],
                ),
                auto_recompute_indicators=config["auto_recompute_indicators"],
            )
            processed_count += 1
        except ValueError:
            failed_count += 1
    return {
        "provider_name": config["provider_name"],
        "processed_count": processed_count,
        "failed_count": failed_count,
        "requested_instruments": config["instruments"],
        "skipped": False,
    }


def _warmup_indicators(db: Session, *, config: MicrotradesAutopilotConfig) -> dict[str, object]:
    warmup_backfill = _run_backfill(
        db,
        config=config,
        lookback_hours=max(config["lookback_hours"], 240),
        max_candles_per_instrument=max(config["max_candles_per_instrument"], 2000),
    )
    recomputed: list[str] = []
    for instrument in config["instruments"]:
        try:
            recompute_indicators(db, instrument)
            recomputed.append(instrument)
        except ValueError:
            continue
    return {
        "backfill": warmup_backfill,
        "recomputed_instruments": recomputed,
    }


def _run_signal_generation(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
) -> dict[str, object]:
    warmup_done = False
    warmup_payload: dict[str, object] | None = None
    last_error = ""
    _autopilot_debug(config, f"signal_generation: start instruments={config['instruments']}")
    for instrument in config["instruments"]:
        try:
            signal = generate_signal(db, config["user_id"], instrument)
            _autopilot_debug(config, f"signal_generation: signal ready instrument={instrument}")
            return {
                "skipped": False,
                "signal_id": signal.id,
                "instrument": signal.instrument,
                "signal_type": signal.signal_type,
                "confidence": signal.confidence,
                "warmup": warmup_payload,
                "skip_reason": None,
            }
        except ValueError as exc:
            message = str(exc)
            if not _is_indicators_missing_error(message):
                raise
            last_error = message
            if not warmup_done:
                warmup_payload = _warmup_indicators(db, config=config)
                warmup_done = True
                try:
                    signal = generate_signal(db, config["user_id"], instrument)
                    _autopilot_debug(
                        config,
                        f"signal_generation: signal ready after warmup instrument={instrument}",
                    )
                    return {
                        "skipped": False,
                        "signal_id": signal.id,
                        "instrument": signal.instrument,
                        "signal_type": signal.signal_type,
                        "confidence": signal.confidence,
                        "warmup": warmup_payload,
                        "skip_reason": None,
                    }
                except ValueError as retry_exc:
                    retry_message = str(retry_exc)
                    if not _is_indicators_missing_error(retry_message):
                        raise
                    last_error = retry_message
                    _autopilot_debug(
                        config,
                        f"signal_generation: retry still missing indicators instrument={instrument}",
                    )
                    continue
            continue
    _autopilot_debug(config, f"signal_generation: skipped reason={last_error}")
    return {
        "skipped": True,
        "signal_id": None,
        "instrument": None,
        "signal_type": None,
        "confidence": 0.0,
        "warmup": warmup_payload,
        "skip_reason": last_error or "Nao foi possivel gerar sinal para os ativos informados.",
    }


def _run_case_study_with_auto_suitability(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
) -> tuple[dict[str, object], bool]:
    try:
        payload = run_thesis_case_study(
            db,
            config["user_id"],
            config["instruments"],
            config["horizon_bars"],
        )
        return payload, False
    except ValueError as exc:
        message = str(exc)
        if not _is_suitability_missing_error(message):
            raise
        _ensure_suitability_profile(db, user_id=config["user_id"])
        payload = run_thesis_case_study(
            db,
            config["user_id"],
            config["instruments"],
            config["horizon_bars"],
        )
        return payload, True


def _empty_monitor_payload(
    *,
    config: MicrotradesAutopilotConfig,
    reason: str,
) -> dict[str, object]:
    return {
        "generated_at": isoformat(utc_now()),
        "user_id": config["user_id"],
        "horizon_bars": config["horizon_bars"],
        "recent_bars_window": config["recent_bars_window"],
        "thesis_count": 0,
        "scan_scope": {"instruments": config["instruments"], "candidate_count": 0},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 0,
            "avg_unrealized_financial_pct": 0.0,
            "executive_status_counts": {},
            "needs_attention_count": 0,
            "notes": [reason],
        },
        "theses": [],
        "disclaimer": DISCLAIMER,
    }


def has_valid_current_monitor_snapshot(
    payload: object,
    *,
    user_id: int | None = None,
) -> bool:
    if not isinstance(payload, dict):
        return False
    if user_id is not None:
        payload_user_id = _safe_int(payload.get("user_id"), -1)
        if payload_user_id != int(user_id):
            return False
    theses_raw = payload.get("theses")
    theses = (
        [item for item in theses_raw if isinstance(item, dict)]
        if isinstance(theses_raw, list)
        else []
    )
    return _safe_int(payload.get("thesis_count"), 0) > 0 and bool(theses)


def is_no_fresh_market_data_monitor_payload(payload: object) -> bool:
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
    return any(_is_no_fresh_market_data_error(str(note)) for note in notes)


def build_stale_reused_current_monitor_payload(payload: dict[str, object]) -> dict[str, object]:
    reused = deepcopy(payload)
    summary = reused.get("summary")
    summary_dict = deepcopy(summary) if isinstance(summary, dict) else {}
    summary_dict["notes"] = [_STALE_MONITOR_REUSED_NOTE]
    reused["summary"] = summary_dict

    data_quality = reused.get("data_quality")
    data_quality_dict = deepcopy(data_quality) if isinstance(data_quality, dict) else {}
    data_quality_dict.update(
        {
            "status": "stale_reused",
            "reason": "no_fresh_market_data",
            "message": _STALE_MONITOR_REUSED_NOTE,
            "reused_at": isoformat(utc_now()),
            "previous_generated_at": reused.get("generated_at"),
        }
    )
    reused["data_quality"] = data_quality_dict
    return reused


def _run_monitor_with_auto_suitability(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
) -> tuple[dict[str, object], bool, bool]:
    try:
        payload = run_current_thesis_monitor(
            db,
            user_id=config["user_id"],
            instruments=config["instruments"],
            horizon_bars=config["horizon_bars"],
            thesis_count=config["thesis_count"],
            recent_bars_window=config["recent_bars_window"],
        )
        return payload, False, False
    except ValueError as exc:
        message = str(exc)
        if _is_suitability_missing_error(message):
            _ensure_suitability_profile(db, user_id=config["user_id"])
            payload = run_current_thesis_monitor(
                db,
                user_id=config["user_id"],
                instruments=config["instruments"],
                horizon_bars=config["horizon_bars"],
                thesis_count=config["thesis_count"],
                recent_bars_window=config["recent_bars_window"],
            )
            return payload, True, False
        if _is_no_fresh_market_data_error(message):
            previous_payload = load_latest_current_thesis_monitor(
                db,
                user_id=config["user_id"],
                include_bundled_bootstrap=False,
            )
            if has_valid_current_monitor_snapshot(previous_payload, user_id=config["user_id"]):
                return build_stale_reused_current_monitor_payload(previous_payload), False, False
        if _is_no_current_theses_error(message):
            payload = _empty_monitor_payload(config=config, reason=message)
            persist_current_thesis_monitor_snapshot(db, payload, user_id=config["user_id"])
            return payload, False, True
        raise


def summarize_top_theses(monitor_payload: dict[str, object]) -> str:
    theses_raw = monitor_payload.get("theses")
    theses = [item for item in theses_raw if isinstance(item, dict)] if isinstance(theses_raw, list) else []
    if not theses:
        return "Sem teses elegiveis no recorte atual."

    def _rank_key(item: dict[str, object]) -> tuple[float, float]:
        confidence = float(item.get("confidence_now_pct") or item.get("confidence_tese_pct") or 0.0)
        expected = float(item.get("expected_financial_pct") or 0.0)
        return (confidence, expected)

    ranked = sorted(theses, key=_rank_key, reverse=True)[:3]
    lines: list[str] = []
    for item in ranked:
        instrument = str(item.get("instrument") or "-").upper()
        confidence = float(item.get("confidence_now_pct") or item.get("confidence_tese_pct") or 0.0)
        expected = float(item.get("expected_financial_pct") or 0.0)
        status = str(item.get("executive_status_label") or item.get("monitor_status") or "monitorar")
        expected_sign = "+" if expected >= 0 else ""
        lines.append(
            f"{instrument} {expected_sign}{expected:.2f}% | conf {confidence:.1f}% | {status}"
        )
    return " | ".join(lines)


def create_decision_with_cooldown(
    db: Session,
    *,
    user_id: int,
    title: str,
    context: str,
    question: str,
    options: list[dict[str, object]],
    priority: str,
    cooldown_minutes: int,
    force: bool = False,
) -> dict[str, object]:
    existing = db.scalar(
        select(AssistantDecisionRecord)
        .where(
            AssistantDecisionRecord.user_id == user_id,
            AssistantDecisionRecord.status == "pending",
            AssistantDecisionRecord.title == title[:160],
        )
        .order_by(desc(AssistantDecisionRecord.id))
        .limit(1)
    )
    if existing is not None and not force:
        created_at = _safe_iso_to_utc(existing.created_at)
        now = utc_now()
        if created_at is not None:
            elapsed = now - created_at
            if elapsed < timedelta(minutes=max(1, cooldown_minutes)):
                return {
                    "status": "cooldown",
                    "decision_id": existing.decision_id,
                    "created_at": existing.created_at,
                    "cooldown_remaining_seconds": int(
                        max(0, timedelta(minutes=cooldown_minutes).total_seconds() - elapsed.total_seconds())
                    ),
                }
    created = create_decision(
        db=db,
        user_id=user_id,
        title=title,
        context=context,
        question=question,
        options=options,
        priority=priority,
    )
    return {
        "status": "created",
        "decision_id": created["decision_id"],
        "created_at": created["created_at"],
        "priority": created["priority"],
    }


def _publish_cycle_decision(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
    signal_payload: dict[str, object],
    case_study_payload: dict[str, object],
    monitor_payload: dict[str, object],
) -> dict[str, object]:
    summary = monitor_payload.get("summary")
    summary_dict = summary if isinstance(summary, dict) else {}
    stop_alerts = int(summary_dict.get("stop_alerts") or 0)
    target_hits = int(summary_dict.get("target_hits") or 0)
    monitoring_count = int(summary_dict.get("monitoring_count") or 0)
    signal_skipped = bool(signal_payload.get("skipped"))
    selected_case = case_study_payload.get("selected_case")
    selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
    thesis_dict = selected_case_dict.get("thesis")
    selected_thesis = thesis_dict if isinstance(thesis_dict, dict) else {}
    selected_thesis_id = str(selected_thesis.get("thesis_id") or "-")
    signal_text = (
        f"signal {signal_payload.get('signal_id')}"
        if signal_payload.get("signal_id")
        else "sinal indisponivel no ciclo"
    )
    top_theses = summarize_top_theses(monitor_payload)
    priority = "high" if stop_alerts > 0 or signal_skipped else "normal"
    title = (
        "Microtrades: atencao no ciclo automatico"
        if priority == "high"
        else "Microtrades: resumo do ciclo automatico"
    )
    context = (
        f"Escopo: {', '.join(config['instruments'])} | {config['interval']} | "
        f"lookback {config['lookback_hours']}h. "
        f"Monitor: {monitor_payload.get('thesis_count', 0)} teses | target {target_hits} | "
        f"stop {stop_alerts} | monitorando {monitoring_count}. "
        f"Case selecionado: {selected_thesis_id} | {signal_text}. "
        f"Top teses: {top_theses}."
    )
    options = (
        [
            {"option_id": "A", "label": "Reduzir risco para BTCUSDT e ETHUSDT apenas"},
            {"option_id": "B", "label": "Manter monitoramento sem novas ordens paper"},
            {"option_id": "C", "label": "Seguir estrategia atual por enquanto"},
        ]
        if priority == "high"
        else [
            {"option_id": "A", "label": "Continuar ciclo automatico no escopo atual"},
            {"option_id": "B", "label": "Focar nas criptos de maior confianca"},
            {"option_id": "C", "label": "Pausar ate nova validacao manual"},
        ]
    )
    return create_decision_with_cooldown(
        db,
        user_id=config["user_id"],
        title=title,
        context=context,
        question="Qual ajuste voce prefere para o proximo ciclo?",
        options=options,
        priority=priority,
        cooldown_minutes=config["decision_cooldown_minutes"],
    )


def _publish_failure_decision(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
    error_message: str,
) -> dict[str, object]:
    return create_decision_with_cooldown(
        db,
        user_id=config["user_id"],
        title="Microtrades: falha no ciclo automatico",
        context=(
            f"Falha capturada: {error_message}. Escopo: {', '.join(config['instruments'])} | "
            f"{config['interval']} | lookback {config['lookback_hours']}h."
        ),
        question="Como devo agir ate voce acessar novamente?",
        options=[
            {"option_id": "A", "label": "Retentar com mais historico no proximo ciclo"},
            {"option_id": "B", "label": "Reduzir escopo para BTCUSDT e ETHUSDT"},
            {"option_id": "C", "label": "Pausar microtrades ate novo comando"},
        ],
        priority="high",
        cooldown_minutes=max(10, config["decision_cooldown_minutes"] // 2),
    )


def run_microtrades_autopilot_cycle(
    db: Session,
    *,
    config: MicrotradesAutopilotConfig,
) -> MicrotradesAutopilotPayload:
    _autopilot_debug(
        config,
        (
            "cycle:start "
            f"user_id={config['user_id']} "
            f"instruments={config['instruments']} "
            f"allow_external_fetches={config['allow_external_fetches']}"
        ),
    )
    started_at = utc_now()
    steps: list[dict[str, object]] = []
    backfill_payload: dict[str, object] = {}
    live_payload: dict[str, object] = {}
    signal_payload: dict[str, object] = {}
    case_study_payload: dict[str, object] = {}
    monitor_payload: dict[str, object] = {}
    decision_payload: dict[str, object] = {"status": "skipped"}
    status = "success"
    error_message: str | None = None

    try:
        try:
            _autopilot_debug(config, "cycle: step backfill")
            backfill_payload = _run_backfill(db, config=config)
            steps.append(
                {
                    "title": "historico",
                    "status": "ok",
                    "meta": (
                        f"{backfill_payload.get('processed_count', 0)} candles processados "
                        f"({backfill_payload.get('failed_count', 0)} falhas)."
                    ),
                }
            )
        except CryptoHistoryProviderError as exc:
            backfill_payload = {"status": "warning", "error": str(exc)}
            steps.append(
                {
                    "title": "historico",
                    "status": "warning",
                    "meta": f"Backfill indisponivel: {exc}",
                }
            )

        try:
            _autopilot_debug(config, "cycle: step live_ingestion")
            live_payload = _run_live_ingestion(db, config=config)
            steps.append(
                {
                    "title": "cotacao",
                    "status": "ok",
                    "meta": f"{live_payload.get('processed_count', 0)} ativos processados.",
                }
            )
        except IntradayProviderError as exc:
            message = str(exc)
            if "FINNHUB_API_TOKEN" in message:
                live_payload = {
                    "status": "warning",
                    "skipped": True,
                    "error": message,
                    "processed_count": 0,
                    "failed_count": 0,
                }
                steps.append(
                    {
                        "title": "cotacao",
                        "status": "warning",
                        "meta": "Token Finnhub ausente. Etapa live ignorada.",
                    }
                )
            else:
                raise

        _autopilot_debug(config, "cycle: step signal_generation")
        signal_payload = _run_signal_generation(db, config=config)
        if signal_payload.get("skipped"):
            status = "partial"
            steps.append(
                {
                    "title": "tese",
                    "status": "warning",
                    "meta": (
                        "Sinal indisponivel no momento. Fluxo segue com comprovacao e monitoramento."
                    ),
                }
            )
        else:
            steps.append(
                {
                    "title": "tese",
                    "status": "ok",
                    "meta": (
                        f"signal {signal_payload.get('signal_id')} em {signal_payload.get('instrument')}"
                    ),
                }
            )

        if not config["allow_external_fetches"]:
            case_study_payload = {
                "skipped": True,
                "reason": "local_only_fast_refresh",
            }
            steps.append(
                {
                    "title": "comprovacao",
                    "status": "warning",
                    "meta": "Case-study pulado no refresh rapido local.",
                }
            )
        else:
            try:
                _autopilot_debug(config, "cycle: step case_study")
                case_study_payload, suitability_created_case = _run_case_study_with_auto_suitability(
                    db,
                    config=config,
                )
                if suitability_created_case:
                    steps.append(
                        {
                            "title": "suitability",
                            "status": "warning",
                            "meta": "Perfil moderado criado automaticamente para case-study.",
                        }
                    )
                selected_case = case_study_payload.get("selected_case")
                selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
                thesis = selected_case_dict.get("thesis")
                thesis_dict = thesis if isinstance(thesis, dict) else {}
                steps.append(
                    {
                        "title": "comprovacao",
                        "status": "ok",
                        "meta": f"Case selecionado: {thesis_dict.get('thesis_id', '-')}",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                status = "partial"
                case_study_payload = {
                    "skipped": True,
                    "error": str(exc),
                }
                steps.append(
                    {
                        "title": "comprovacao",
                        "status": "warning",
                        "meta": f"Case-study indisponivel neste ciclo: {exc}",
                    }
                )

        _autopilot_debug(config, "cycle: step monitor")
        monitor_payload, suitability_created_monitor, monitor_empty = _run_monitor_with_auto_suitability(
            db,
            config=config,
        )
        if suitability_created_monitor:
            steps.append(
                {
                    "title": "suitability",
                    "status": "warning",
                    "meta": "Perfil moderado criado automaticamente para monitoramento.",
                }
            )
        if monitor_empty:
            status = "partial"
            steps.append(
                {
                    "title": "monitoramento",
                    "status": "warning",
                    "meta": "Nao ha teses atuais no recorte. Seguiremos acompanhando.",
                }
            )
        else:
            steps.append(
                {
                    "title": "monitoramento",
                    "status": "ok",
                    "meta": f"{monitor_payload.get('thesis_count', 0)} teses monitoradas.",
                }
            )
        steps.append(
            {
                "title": "sugestoes",
                "status": "ok",
                "meta": summarize_top_theses(monitor_payload),
            }
        )

        if config["publish_decisions"]:
            _autopilot_debug(config, "cycle: step publish_decision")
            decision_payload = _publish_cycle_decision(
                db,
                config=config,
                signal_payload=signal_payload,
                case_study_payload=case_study_payload,
                monitor_payload=monitor_payload,
            )
            if decision_payload.get("status") == "created":
                steps.append(
                    {
                        "title": "centro de decisoes",
                        "status": "ok",
                        "meta": (
                            f"Card publicado ({decision_payload.get('decision_id', 'sem id')})."
                        ),
                    }
                )
            elif decision_payload.get("status") == "cooldown":
                steps.append(
                    {
                        "title": "centro de decisoes",
                        "status": "warning",
                        "meta": "Publicacao em cooldown para evitar excesso de cards.",
                    }
                )
            else:
                steps.append(
                    {
                        "title": "centro de decisoes",
                        "status": "warning",
                        "meta": "Falha ao publicar card no Centro de decisoes.",
                    }
                )

    except Exception as exc:  # noqa: BLE001
        status = "failed"
        error_message = str(exc)
        _autopilot_debug(config, f"cycle: failed error={error_message}")
        steps.append(
            {
                "title": "falha",
                "status": "error",
                "meta": error_message,
            }
        )
        if config["publish_decisions"]:
            try:
                decision_payload = _publish_failure_decision(
                    db,
                    config=config,
                    error_message=error_message,
                )
            except Exception as decision_exc:  # noqa: BLE001
                decision_payload = {
                    "status": "error",
                    "error": str(decision_exc),
                }

    finished_at = utc_now()
    _autopilot_debug(
        config,
        (
            "cycle: finished "
            f"status={status} "
            f"monitor_thesis_count={monitor_payload.get('thesis_count', 0)}"
        ),
    )
    payload: MicrotradesAutopilotPayload = {
        "run_started_at": isoformat(started_at),
        "run_finished_at": isoformat(finished_at),
        "user_id": config["user_id"],
        "status": status,
        "config": {
            "instruments": config["instruments"],
            "provider_name": config["provider_name"],
            "history_provider_name": config["history_provider_name"],
            "interval": config["interval"],
            "lookback_hours": config["lookback_hours"],
            "max_candles_per_instrument": config["max_candles_per_instrument"],
            "horizon_bars": config["horizon_bars"],
            "thesis_count": config["thesis_count"],
            "recent_bars_window": config["recent_bars_window"],
            "auto_recompute_indicators": config["auto_recompute_indicators"],
            "allow_external_fetches": config["allow_external_fetches"],
            "publish_decisions": config["publish_decisions"],
            "decision_cooldown_minutes": config["decision_cooldown_minutes"],
        },
        "steps": steps,
        "backfill": backfill_payload,
        "live_ingestion": live_payload,
        "signal": signal_payload,
        "case_study": case_study_payload,
        "monitor": monitor_payload,
        "decision": decision_payload,
        "error": error_message,
    }
    return payload

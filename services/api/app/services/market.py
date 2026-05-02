from __future__ import annotations

from datetime import UTC

from app.models import IndicatorSnapshot, MarketProviderState, MarketTick
from app.schemas import MarketProviderStatusRequest, MarketTickIngestRequest
from app.services.asset_classes import asset_class_label, classify_instrument
from app.services.audit import record_audit_event
from app.services.indicators import ema, macd, momentum, rsi, sma, volatility
from app.services.notifications import notify_market_price_move
from app.services.point_in_time import ticks_as_of
from app.services.utils import isoformat, to_json, utc_now
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _provider_sort_key(role: str) -> int:
    return 0 if role == "primary" else 1


def _load_provider_states(db: Session) -> list[MarketProviderState]:
    states = list(
        db.scalars(
            select(MarketProviderState).order_by(
                MarketProviderState.is_active.desc(),
                MarketProviderState.role.asc(),
                MarketProviderState.provider_name.asc(),
            )
        )
    )
    return states


def resolve_active_provider(db: Session, provider_name: str) -> MarketProviderState | None:
    provider_name = provider_name.lower()
    states = _load_provider_states(db)
    if not states:
        return None
    named_state = next((state for state in states if state.provider_name == provider_name), None)
    active_state = next((state for state in states if state.is_active), None)
    if active_state is not None:
        return active_state
    if named_state is not None and named_state.status != "failed":
        return named_state
    healthy_candidate = next(
        (state for state in states if state.status != "failed"),
        None,
    )
    return healthy_candidate


def update_provider_status(
    db: Session,
    payload: MarketProviderStatusRequest,
) -> MarketProviderState:
    provider_name = payload.provider_name.lower()
    now = isoformat(utc_now())
    state = db.scalar(
        select(MarketProviderState).where(MarketProviderState.provider_name == provider_name)
    )
    if state is None:
        state = MarketProviderState(
            provider_name=provider_name,
            role=payload.role,
            status="healthy",
            consecutive_failures=0,
            last_event_time=now,
            failover_threshold=payload.failover_threshold,
            is_active=payload.role == "primary",
            details="{}",
        )
        db.add(state)
        db.flush()

    state.role = payload.role
    state.failover_threshold = payload.failover_threshold
    state.last_event_time = now
    if payload.status == "healthy":
        state.status = "healthy"
        state.consecutive_failures = 0
    else:
        state.status = payload.status
        state.consecutive_failures += payload.failure_increment

    state.details = to_json({"notes": payload.notes or "", "status": payload.status})

    if payload.status == "healthy" and state.role == "primary":
        for candidate in _load_provider_states(db):
            candidate.is_active = candidate.provider_name == state.provider_name
    elif state.role == "primary" and state.consecutive_failures >= state.failover_threshold:
        secondary = db.scalar(
            select(MarketProviderState)
            .where(MarketProviderState.role == "secondary")
            .where(MarketProviderState.status != "failed")
            .order_by(MarketProviderState.provider_name.asc())
            .limit(1)
        )
        if secondary is not None:
            state.is_active = False
            secondary.is_active = True
            secondary.last_event_time = now
            secondary.details = to_json(
                {
                    "activated_by_failover": provider_name,
                    "notes": payload.notes or "",
                }
            )
            record_audit_event(
                db,
                "market.provider.failover_activated",
                {
                    "from_provider": state.provider_name,
                    "to_provider": secondary.provider_name,
                    "failure_count": state.consecutive_failures,
                    "threshold": state.failover_threshold,
                },
            )
    elif payload.status == "healthy" and state.role == "secondary":
        primary = db.scalar(
            select(MarketProviderState)
            .where(MarketProviderState.role == "primary")
            .limit(1)
        )
        if primary is None or primary.status != "healthy":
            for candidate in _load_provider_states(db):
                candidate.is_active = candidate.provider_name == state.provider_name

    db.commit()
    db.refresh(state)
    return state


def ingest_tick(db: Session, payload: MarketTickIngestRequest) -> MarketTick:
    instrument = payload.instrument.upper()
    provider_name = payload.provider.lower()
    active_provider = resolve_active_provider(db, provider_name)
    if active_provider is not None and active_provider.provider_name != provider_name:
        raise ValueError(
            "Provedor inativo para ingestao no momento. Utilize o provedor ativo configurado."
        )

    if payload.source_payload_id is not None:
        existing = db.scalar(
            select(MarketTick)
            .where(MarketTick.instrument == instrument)
            .where(MarketTick.provider == provider_name)
            .where(MarketTick.source_payload_id == payload.source_payload_id)
            .order_by(MarketTick.id.desc())
            .limit(1)
        )
        if existing is not None:
            record_audit_event(
                db,
                "market.tick.duplicate_ignored",
                {
                    "instrument": existing.instrument,
                    "provider": existing.provider,
                    "source_payload_id": existing.source_payload_id,
                },
            )
            return existing

    tick = MarketTick(
        instrument=instrument,
        provider=provider_name,
        event_time=isoformat(payload.event_time),
        ingest_time=isoformat(utc_now()),
        price=payload.price,
        volume=payload.volume,
        currency=payload.currency,
        source_payload_id=payload.source_payload_id,
    )
    db.add(tick)
    db.commit()
    db.refresh(tick)
    record_audit_event(
        db,
        "market.tick.ingested",
        {"instrument": tick.instrument, "provider": tick.provider, "price": tick.price},
    )
    return tick


def recompute_indicators(db: Session, instrument: str) -> IndicatorSnapshot:
    as_of = utc_now()
    ticks = ticks_as_of(db, instrument.upper(), as_of)
    prices = [tick.price for tick in ticks]
    if len(prices) < 26:
        raise ValueError("Quantidade insuficiente de ticks para indicadores")
    snapshot = IndicatorSnapshot(
        instrument=instrument.upper(),
        reference_time=ticks[-1].event_time,
        availability_time=isoformat(as_of),
        sma_5=sma(prices, 5),
        sma_10=sma(prices, 10),
        sma_20=sma(prices, 20),
        ema_5=ema(prices, 5),
        ema_12=ema(prices, 12),
        ema_26=ema(prices, 26),
        rsi_14=rsi(prices, 14),
        volatility_10=volatility(prices, 10),
        momentum_5=momentum(prices, 5),
        macd=macd(prices),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    record_audit_event(
        db,
        "analysis.indicators.recomputed",
        {"instrument": snapshot.instrument, "reference_time": snapshot.reference_time},
    )
    return snapshot


def market_tick_to_contract(tick: MarketTick) -> dict[str, object]:
    asset_class = classify_instrument(tick.instrument)
    return {
        "event_type": "market.tick.normalized.v1",
        "version": 1,
        "instrument": tick.instrument,
        "asset_class": asset_class,
        "asset_class_label": asset_class_label(asset_class),
        "provider": tick.provider,
        "event_time": tick.event_time,
        "ingest_time": tick.ingest_time,
        "price": tick.price,
        "volume": tick.volume,
        "currency": tick.currency,
        "source_payload_id": tick.source_payload_id,
    }


def _indicator_snapshot_to_contract(snapshot: IndicatorSnapshot) -> dict[str, object]:
    return {
        "instrument": snapshot.instrument,
        "reference_time": snapshot.reference_time,
        "availability_time": snapshot.availability_time,
        "sma_5": snapshot.sma_5,
        "sma_10": snapshot.sma_10,
        "sma_20": snapshot.sma_20,
        "ema_5": snapshot.ema_5,
        "ema_12": snapshot.ema_12,
        "ema_26": snapshot.ema_26,
        "rsi_14": snapshot.rsi_14,
        "volatility_10": snapshot.volatility_10,
        "momentum_5": snapshot.momentum_5,
        "macd": snapshot.macd,
    }


def ingest_tick_live(
    db: Session,
    payload: MarketTickIngestRequest,
    *,
    auto_recompute_indicators: bool = True,
) -> dict[str, object]:
    tick = ingest_tick(db, payload)
    tick_count = int(
        db.scalar(
            select(func.count())
            .select_from(MarketTick)
            .where(MarketTick.instrument == tick.instrument)
        )
        or 0
    )

    indicator_snapshot: IndicatorSnapshot | None = None
    indicator_updated = False
    learning_status = "warming_up"
    if auto_recompute_indicators and tick_count >= 26:
        try:
            indicator_snapshot = recompute_indicators(db, tick.instrument)
            indicator_updated = True
            learning_status = "updated"
        except ValueError:
            learning_status = "warming_up"

    event_time = payload.event_time
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=UTC)
    processing_lag_seconds = max(
        0.0,
        round((utc_now() - event_time.astimezone(UTC)).total_seconds(), 3),
    )

    record_audit_event(
        db,
        "analysis.realtime.tick_processed",
        {
            "instrument": tick.instrument,
            "provider": tick.provider,
            "tick_count": tick_count,
            "indicator_updated": indicator_updated,
            "processing_lag_seconds": processing_lag_seconds,
        },
    )
    notify_market_price_move(db, tick)

    return {
        "market_tick": market_tick_to_contract(tick),
        "algorithm_update": {
            "indicator_updated": indicator_updated,
            "indicator_snapshot": (
                _indicator_snapshot_to_contract(indicator_snapshot)
                if indicator_snapshot is not None
                else None
            ),
            "tick_count": tick_count,
            "learning_status": learning_status,
            "processing_lag_seconds": processing_lag_seconds,
            "auto_recompute_indicators": auto_recompute_indicators,
        },
    }


def list_provider_states(db: Session) -> list[MarketProviderState]:
    states = _load_provider_states(db)
    return sorted(
        states,
        key=lambda state: (
            0 if state.is_active else 1,
            _provider_sort_key(state.role),
            state.provider_name,
        ),
    )

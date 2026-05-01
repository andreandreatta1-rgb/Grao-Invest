from __future__ import annotations

from datetime import datetime
from statistics import mean

from app.models import (
    BacktestRun,
    CircuitBreakerState,
    KillSwitchState,
    MarketTick,
    PortfolioPosition,
    RiskDecision,
    Signal,
    SuitabilityProfile,
)
from app.services.alerts import maybe_emit_circuit_breaker_alert
from app.services.audit import record_audit_event
from app.services.utils import isoformat
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

PROFILE_LIMITS = {
    "conservador": 2000.0,
    "moderado": 5000.0,
    "arrojado": 10000.0,
}

PROFILE_PORTFOLIO_LIMITS = {
    "conservador": 4000.0,
    "moderado": 9000.0,
    "arrojado": 30000.0,
}

PROFILE_DRAWDOWN_LIMITS = {
    "conservador": -5.0,
    "moderado": -10.0,
    "arrojado": -15.0,
}


def latest_market_price(db: Session, instrument: str, as_of: datetime) -> float:
    tick = db.scalar(
        select(MarketTick)
        .where(MarketTick.instrument == instrument.upper())
        .where(MarketTick.event_time <= as_of.isoformat())
        .order_by(desc(MarketTick.event_time))
        .limit(1)
    )
    if tick is None:
        raise ValueError("Nao ha preco de mercado disponivel para este ativo")
    return float(tick.price)


def evaluate_circuit_breaker(
    db: Session,
    instrument: str,
    as_of: datetime,
) -> CircuitBreakerState | None:
    ticks = list(
        db.scalars(
            select(MarketTick)
            .where(MarketTick.instrument == instrument.upper())
            .where(MarketTick.event_time <= as_of.isoformat())
            .order_by(desc(MarketTick.event_time))
            .limit(10)
        )
    )
    if len(ticks) < 5:
        return None
    prices = [tick.price for tick in reversed(ticks)]
    average_price = mean(prices)
    amplitude = (max(prices) - min(prices)) / average_price if average_price else 0.0
    state = db.scalar(
        select(CircuitBreakerState)
        .where(CircuitBreakerState.instrument == instrument.upper())
        .order_by(desc(CircuitBreakerState.id))
        .limit(1)
    )
    if amplitude >= 0.08:
        if state is None or state.status != "active":
            state = CircuitBreakerState(
                instrument=instrument.upper(),
                status="active",
                reason="Volatilidade de curtissimo prazo acima do limiar de seguranca",
                triggered_at=isoformat(as_of),
                released_at=None,
            )
            db.add(state)
            db.commit()
            db.refresh(state)
            maybe_emit_circuit_breaker_alert(db, state)
            record_audit_event(
                db,
                "risk.circuit_breaker.activated",
                {"instrument": instrument.upper(), "amplitude": round(amplitude, 4)},
            )
        return state
    if state is not None and state.status == "active":
        state.status = "released"
        state.released_at = isoformat(as_of)
        db.commit()
        record_audit_event(
            db,
            "risk.circuit_breaker.released",
            {"instrument": instrument.upper(), "amplitude": round(amplitude, 4)},
        )
    return None


def set_kill_switch(
    db: Session,
    scope_type: str,
    scope_id: str,
    status: str,
    reason: str,
    as_of: datetime,
) -> KillSwitchState:
    state = db.scalar(
        select(KillSwitchState)
        .where(KillSwitchState.scope_type == scope_type)
        .where(KillSwitchState.scope_id == scope_id)
        .order_by(desc(KillSwitchState.id))
        .limit(1)
    )
    if state is None:
        state = KillSwitchState(
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
            reason=reason,
            triggered_at=isoformat(as_of),
            released_at=isoformat(as_of) if status == "released" else None,
        )
        db.add(state)
    else:
        state.status = status
        state.reason = reason
        if status == "active":
            state.triggered_at = isoformat(as_of)
            state.released_at = None
        else:
            state.released_at = isoformat(as_of)
    db.commit()
    db.refresh(state)
    record_audit_event(
        db,
        "risk.kill_switch.updated",
        {"scope_type": scope_type, "scope_id": scope_id, "status": status, "reason": reason},
    )
    return state


def active_kill_switches(db: Session) -> list[KillSwitchState]:
    return list(
        db.scalars(
            select(KillSwitchState)
            .where(KillSwitchState.status == "active")
            .order_by(desc(KillSwitchState.id))
        )
    )


def current_portfolio_exposure(db: Session, user_id: int, as_of: datetime) -> float:
    positions = list(
        db.scalars(
            select(PortfolioPosition).where(PortfolioPosition.user_id == user_id)
        )
    )
    exposure = 0.0
    for position in positions:
        try:
            current_price = latest_market_price(db, position.instrument, as_of)
        except ValueError:
            current_price = position.average_price
        exposure += position.quantity * current_price
    return round(exposure, 2)


def latest_drawdown_pct(db: Session, user_id: int) -> float:
    latest_run = db.scalar(
        select(BacktestRun)
        .where(BacktestRun.user_id == user_id)
        .order_by(desc(BacktestRun.id))
        .limit(1)
    )
    if latest_run is None:
        return 0.0
    return -abs(latest_run.max_drawdown_pct)


def triggered_kill_switch(
    db: Session,
    user_id: int,
    instrument: str,
) -> KillSwitchState | None:
    states = active_kill_switches(db)
    for state in states:
        if state.scope_type == "global":
            return state
        if state.scope_type == "user" and state.scope_id == str(user_id):
            return state
        if state.scope_type == "instrument" and state.scope_id == instrument.upper():
            return state
    return None


def evaluate_risk(
    db: Session,
    user_id: int,
    signal: Signal,
    quantity: int,
    reference_price: float,
    as_of: datetime,
) -> RiskDecision:
    notional = quantity * reference_price
    portfolio_exposure = current_portfolio_exposure(db, user_id, as_of)
    projected_exposure = portfolio_exposure + notional

    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    if profile is None:
        missing_profile_decision = RiskDecision(
            user_id=user_id,
            signal_id=signal.id,
            instrument=signal.instrument,
            decision="rejected",
            notes="Suitability obrigatorio antes de executar paper trading.",
            decided_at=isoformat(as_of),
            portfolio_exposure=portfolio_exposure,
            projected_exposure=projected_exposure,
        )
        db.add(missing_profile_decision)
        db.commit()
        db.refresh(missing_profile_decision)
        record_audit_event(
            db,
            "risk.decision.made",
            {
                "instrument": signal.instrument,
                "decision": "rejected",
                "notes": missing_profile_decision.notes,
            },
            user_id,
        )
        return missing_profile_decision

    investor_profile = profile.investor_profile
    breaker = evaluate_circuit_breaker(db, signal.instrument, as_of)
    max_notional = PROFILE_LIMITS[investor_profile]
    portfolio_limit = PROFILE_PORTFOLIO_LIMITS[investor_profile]
    drawdown_pct = latest_drawdown_pct(db, user_id)
    drawdown_limit = PROFILE_DRAWDOWN_LIMITS[investor_profile]
    kill_switch = triggered_kill_switch(db, user_id, signal.instrument)

    decision = "accepted"
    notes = f"Perfil {investor_profile} com limite maximo de R$ {max_notional:.2f}."
    if kill_switch is not None:
        decision = "rejected"
        notes = f"Kill-switch ativo: {kill_switch.reason}"
    elif breaker is not None and breaker.status == "active":
        decision = "rejected"
        notes = breaker.reason
    elif drawdown_pct <= drawdown_limit:
        decision = "rejected"
        notes = "Drawdown historico acima do limite permitido para o perfil."
    elif signal.anti_hype_score < 40:
        decision = "rejected"
        notes = "Fluxo bloqueado por noticia de baixa credibilidade/alto hype."
    elif signal.confidence < 0.57:
        decision = "rejected"
        notes = "Confianca do sinal abaixo do limiar minimo para simulacao."
    elif notional > max_notional:
        decision = "rejected"
        notes = "Valor nocional acima do limite aceito para o perfil do investidor."
    elif projected_exposure > portfolio_limit:
        decision = "rejected"
        notes = "Exposicao agregada do portfolio acima do limite permitido."

    risk_decision = RiskDecision(
        user_id=user_id,
        signal_id=signal.id,
        instrument=signal.instrument,
        decision=decision,
        notes=notes,
        decided_at=isoformat(as_of),
        portfolio_exposure=portfolio_exposure,
        projected_exposure=projected_exposure,
    )
    db.add(risk_decision)
    db.commit()
    db.refresh(risk_decision)
    record_audit_event(
        db,
        "risk.decision.made",
        {
            "instrument": signal.instrument,
            "decision": decision,
            "notes": notes,
        },
        user_id,
    )
    return risk_decision

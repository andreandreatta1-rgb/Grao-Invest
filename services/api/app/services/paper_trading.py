from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from app.models import MarketTick, PaperOrder, PortfolioPosition, Signal
from app.services.audit import record_audit_event
from app.services.risk import evaluate_risk
from app.services.utils import isoformat, utc_now
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


class ExecutionFriction(TypedDict):
    spread_bps: float
    slippage_bps: float
    participation_rate: float


class CostBreakdown(TypedDict):
    b3_fee: float
    broker_fee: float
    iss_on_broker: float
    total_cost: float


class TaxEstimate(TypedDict):
    regime: str
    estimated_rate: float
    expected_return_pct: float
    expected_tax: float


def latest_market_tick(db: Session, instrument: str, as_of: datetime) -> MarketTick:
    tick = db.scalar(
        select(MarketTick)
        .where(MarketTick.instrument == instrument.upper())
        .where(MarketTick.event_time <= as_of.isoformat())
        .order_by(desc(MarketTick.event_time))
        .limit(1)
    )
    if tick is None:
        raise ValueError("Nao ha preco de mercado disponivel para este ativo")
    return tick


def compute_execution_friction(quantity: int, market_volume: int) -> ExecutionFriction:
    safe_volume = max(1, market_volume)
    participation_rate = min(1.0, quantity / safe_volume)
    spread_bps = 8.0
    slippage_bps = 5.0 + min(25.0, participation_rate * 25.0)
    return {
        "spread_bps": round(spread_bps, 4),
        "slippage_bps": round(slippage_bps, 4),
        "participation_rate": round(participation_rate, 6),
    }


def apply_execution_friction(reference_price: float, friction: ExecutionFriction) -> float:
    total_bps = friction["spread_bps"] + friction["slippage_bps"]
    return round(reference_price * (1 + (total_bps / 10_000)), 4)


def estimate_operational_costs(gross_amount: float) -> CostBreakdown:
    b3_fee = round(gross_amount * 0.0003, 4)
    broker_variable = gross_amount * 0.0002
    broker_fee = round(max(1.25, broker_variable), 4)
    iss_on_broker = round(broker_fee * 0.05, 4)
    total_cost = round(b3_fee + broker_fee + iss_on_broker, 2)
    return {
        "b3_fee": b3_fee,
        "broker_fee": broker_fee,
        "iss_on_broker": iss_on_broker,
        "total_cost": total_cost,
    }


def estimate_tax_v1(signal: Signal, gross_amount: float) -> TaxEstimate:
    regime = "swing_trade"
    estimated_rate = 0.15
    confidence_component = max(0.0, signal.confidence - 0.5) * 8.0
    anti_hype_component = max(0.0, (signal.anti_hype_score - 50.0) / 100.0)
    expected_return_pct = round(min(3.0, confidence_component + anti_hype_component), 4)
    expected_tax = round(gross_amount * (expected_return_pct / 100) * estimated_rate, 2)
    return {
        "regime": regime,
        "estimated_rate": estimated_rate,
        "expected_return_pct": expected_return_pct,
        "expected_tax": expected_tax,
    }


def create_paper_order(db: Session, user_id: int, signal_id: int, quantity: int) -> PaperOrder:
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise ValueError("Sinal nao encontrado")
    if signal.user_id != user_id:
        raise ValueError("Sinal nao pertence ao usuario")

    as_of = utc_now()
    market_tick = latest_market_tick(db, signal.instrument, as_of)
    reference_price = float(market_tick.price)
    risk_decision = evaluate_risk(db, user_id, signal, quantity, reference_price, as_of)
    if risk_decision.decision != "accepted":
        raise ValueError(risk_decision.notes)

    friction = compute_execution_friction(quantity, int(market_tick.volume))
    execution_price = apply_execution_friction(reference_price, friction)
    gross_amount = round(execution_price * quantity, 2)
    cost_breakdown = estimate_operational_costs(gross_amount)
    tax_estimate = estimate_tax_v1(signal, gross_amount)
    estimated_cost = cost_breakdown["total_cost"]
    estimated_tax = tax_estimate["expected_tax"]

    order = PaperOrder(
        user_id=user_id,
        signal_id=signal.id,
        instrument=signal.instrument,
        quantity=quantity,
        reference_price=reference_price,
        execution_price=execution_price,
        gross_amount=gross_amount,
        estimated_cost=estimated_cost,
        estimated_tax=estimated_tax,
        risk_status=risk_decision.decision,
        risk_notes=risk_decision.notes,
        created_at=isoformat(as_of),
    )
    db.add(order)
    db.flush()

    position = db.scalar(
        select(PortfolioPosition)
        .where(PortfolioPosition.user_id == user_id)
        .where(PortfolioPosition.instrument == signal.instrument)
    )
    if position is None:
        position = PortfolioPosition(
            user_id=user_id,
            instrument=signal.instrument,
            quantity=quantity,
            average_price=execution_price,
            updated_at=isoformat(as_of),
        )
        db.add(position)
    else:
        total_quantity = position.quantity + quantity
        weighted_price = (
            (position.average_price * position.quantity) + gross_amount
        ) / total_quantity
        position.quantity = total_quantity
        position.average_price = round(weighted_price, 4)
        position.updated_at = isoformat(as_of)

    db.commit()
    db.refresh(order)

    execution_memory = {
        "market_context": {
            "provider": market_tick.provider,
            "market_event_time": market_tick.event_time,
            "market_volume": market_tick.volume,
            "reference_price": reference_price,
        },
        "friction": friction,
        "cost_breakdown": cost_breakdown,
        "tax_estimate": tax_estimate,
    }
    record_audit_event(
        db,
        "paper.order.executed",
        {
            "order_id": order.id,
            "instrument": order.instrument,
            "quantity": order.quantity,
            "gross_amount": order.gross_amount,
            "execution_memory": execution_memory,
        },
        user_id,
    )
    return order

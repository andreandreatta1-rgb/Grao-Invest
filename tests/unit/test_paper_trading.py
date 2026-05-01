from __future__ import annotations

from app.models import Signal
from app.services.paper_trading import (
    apply_execution_friction,
    compute_execution_friction,
    estimate_operational_costs,
    estimate_tax_v1,
)


def _signal(confidence: float, anti_hype_score: float) -> Signal:
    return Signal(
        user_id=1,
        instrument="PETR4",
        reference_time="2026-04-20T12:00:00+00:00",
        availability_time="2026-04-20T12:00:00+00:00",
        signal_type="bullish_setup",
        confidence=confidence,
        rationale="cenario descritivo para simulacao",
        anti_hype_score=anti_hype_score,
        xai_payload="{}",
    )


def test_execution_friction_increases_with_participation() -> None:
    low_participation = compute_execution_friction(quantity=10, market_volume=1000)
    high_participation = compute_execution_friction(quantity=400, market_volume=1000)
    assert high_participation["slippage_bps"] > low_participation["slippage_bps"]
    assert high_participation["participation_rate"] > low_participation["participation_rate"]


def test_apply_execution_friction_marks_up_reference_price() -> None:
    friction = compute_execution_friction(quantity=100, market_volume=1000)
    execution_price = apply_execution_friction(40.0, friction)
    assert execution_price > 40.0


def test_operational_cost_breakdown_is_consistent() -> None:
    breakdown = estimate_operational_costs(gross_amount=25000.0)
    assert breakdown["b3_fee"] > 0
    assert breakdown["broker_fee"] >= 1.25
    assert breakdown["iss_on_broker"] > 0
    assert breakdown["total_cost"] == round(
        breakdown["b3_fee"] + breakdown["broker_fee"] + breakdown["iss_on_broker"],
        2,
    )


def test_tax_estimate_reflects_signal_quality() -> None:
    weak_signal = _signal(confidence=0.51, anti_hype_score=40.0)
    strong_signal = _signal(confidence=0.74, anti_hype_score=88.0)
    weak_tax = estimate_tax_v1(weak_signal, gross_amount=20000.0)
    strong_tax = estimate_tax_v1(strong_signal, gross_amount=20000.0)
    assert weak_tax["expected_tax"] <= strong_tax["expected_tax"]
    assert strong_tax["estimated_rate"] == 0.15

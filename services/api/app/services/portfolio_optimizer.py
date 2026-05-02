from __future__ import annotations

import json
from statistics import mean, pstdev
from typing import TypedDict

from app.models import (
    AllocationAsset,
    AllocationPlan,
    FundamentalSnapshot,
    MarketTick,
    PortfolioPosition,
    RebalancePlan,
)
from app.services.asset_classes import (
    asset_class_label,
    classify_instrument,
    is_portfolio_asset_class,
)
from app.services.news import SentimentAggregate, aggregate_sentiment_as_of
from app.services.point_in_time import latest_fundamentals_as_of, latest_indicator_as_of
from app.services.utils import anti_recommendation_text, assert_compliant_copy, isoformat, utc_now
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

_LOOKBACK_TICKS = 60
_TOP_SELECTION = 20
_MIN_PRICE = 5.0
_MIN_COVERAGE = 0.8
_MIN_NOTIONAL = 20_000.0
_MAX_WEIGHT = 0.15
_MIN_CASH_WEIGHT = 0.05


class InstrumentScore(TypedDict):
    instrument: str
    asset_class: str
    asset_class_label: str
    latest_price: float
    avg_notional: float
    coverage: float
    technical_score: float
    fundamental_score: float
    sentiment_score: float
    momentum_score: float
    composite_score: float
    expected_return_annual: float
    expected_volatility_annual: float


class AllocationAssetPayload(TypedDict):
    ticker: str
    asset_class: str
    asset_class_label: str
    weight_pct: float
    value_brl: float
    shares_approx: int
    entry_price_target: float
    stop_loss: float
    thesis_id: str | None
    score_composite: float


class AllocationPlanPayload(TypedDict):
    plan_id: int
    user_id: int
    version: int
    capital_brl: float
    risk_profile: str
    assets: list[AllocationAssetPayload]
    expected_sharpe: float
    expected_return_annual: float
    expected_volatility_annual: float
    max_drawdown_estimate: float
    diversification_score: float
    rationale_text: str
    llm_model_version: str
    status: str
    created_at: str


class RebalanceOrderPayload(TypedDict):
    instrument: str
    action: str
    current_weight_pct: float
    target_weight_pct: float
    drift_pct: float
    adjustment_value_brl: float


class RebalancePlanPayload(TypedDict):
    rebalance_plan_id: int
    user_id: int
    allocation_plan_id: int
    generated_at: str
    total_drift_pct: float
    status: str
    orders: list[RebalanceOrderPayload]


def _clamp(value: float, *, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _recent_ticks(
    db: Session,
    instrument: str,
    *,
    limit: int = _LOOKBACK_TICKS,
) -> list[MarketTick]:
    return list(
        db.scalars(
            select(MarketTick)
            .where(MarketTick.instrument == instrument.upper())
            .order_by(desc(MarketTick.ingest_time), desc(MarketTick.id))
            .limit(limit)
        )
    )


def _latest_price(db: Session, instrument: str) -> float | None:
    tick = db.scalar(
        select(MarketTick)
        .where(MarketTick.instrument == instrument.upper())
        .order_by(desc(MarketTick.ingest_time), desc(MarketTick.id))
        .limit(1)
    )
    if tick is None:
        return None
    return float(tick.price)


def _technical_score(
    latest_price: float,
    indicator: object | None,
) -> float:
    if indicator is None:
        return 0.5
    score = 0.0
    snapshot = indicator
    rsi = float(getattr(snapshot, "rsi_14", 50.0))
    if 42 <= rsi <= 65:
        score += 0.22
    if float(getattr(snapshot, "macd", 0.0)) > 0:
        score += 0.2
    sma_5 = float(getattr(snapshot, "sma_5", latest_price))
    sma_10 = float(getattr(snapshot, "sma_10", latest_price))
    sma_20 = float(getattr(snapshot, "sma_20", latest_price))
    ema_12 = float(getattr(snapshot, "ema_12", latest_price))
    ema_26 = float(getattr(snapshot, "ema_26", latest_price))
    if sma_5 >= sma_10:
        score += 0.2
    if sma_10 >= sma_20:
        score += 0.16
    if ema_12 >= ema_26:
        score += 0.16
    if float(getattr(snapshot, "momentum_5", 0.0)) > 0:
        score += 0.12
    return _clamp(score)


def _fundamental_score(fundamentals: FundamentalSnapshot | None) -> float:
    if fundamentals is None:
        return 0.5
    pe = float(fundamentals.pe_ratio)
    pb = float(fundamentals.pb_ratio)
    roe = float(fundamentals.roe)
    dy = float(fundamentals.dividend_yield)
    value_score = _clamp((30.0 - pe) / 30.0) * 0.4 + _clamp((4.0 - pb) / 4.0) * 0.2
    quality_score = _clamp(roe / 25.0) * 0.25 + _clamp(dy / 12.0) * 0.15
    return _clamp(value_score + quality_score)


def _sentiment_score(sentiment: SentimentAggregate) -> float:
    article_count = int(sentiment["article_count"])
    if article_count <= 0:
        return 0.5
    weighted_sentiment = float(sentiment["weighted_sentiment"])
    return _clamp(0.5 + (weighted_sentiment * 0.5))


def _momentum_score_from_ticks(ticks: list[MarketTick]) -> tuple[float, float, float]:
    if len(ticks) < 2:
        return 0.5, 0.0, 0.0
    ordered = list(reversed(ticks))
    first_price = float(ordered[0].price)
    last_price = float(ordered[-1].price)
    if first_price <= 0:
        return 0.5, 0.0, 0.0
    raw_return = (last_price - first_price) / first_price
    momentum_score = _clamp(0.5 + (raw_return * 2.5))
    returns = [
        (float(ordered[index].price) - float(ordered[index - 1].price))
        / max(float(ordered[index - 1].price), 1e-9)
        for index in range(1, len(ordered))
    ]
    expected_annual = mean(returns) * 252 if returns else 0.0
    volatility_annual = pstdev(returns) * (252 ** 0.5) if len(returns) > 1 else 0.0
    return momentum_score, expected_annual, volatility_annual


def _candidate_universe(
    db: Session,
    *,
    instruments: list[str] | None = None,
) -> list[str]:
    if instruments:
        return sorted({instrument.upper() for instrument in instruments if instrument.strip()})
    ticks = list(
        db.scalars(
            select(MarketTick.instrument)
            .order_by(MarketTick.instrument.asc())
            .distinct()
        )
    )
    return [instrument.upper() for instrument in ticks]


def _score_instrument(db: Session, instrument: str) -> InstrumentScore | None:
    asset_class = classify_instrument(instrument)
    if not is_portfolio_asset_class(asset_class):
        return None
    ticks = _recent_ticks(db, instrument)
    if not ticks:
        return None
    latest_price = float(ticks[0].price)
    coverage = len(ticks) / _LOOKBACK_TICKS
    avg_notional = mean(float(tick.price) * float(tick.volume) for tick in ticks[:20])
    if latest_price < _MIN_PRICE or coverage < _MIN_COVERAGE or avg_notional < _MIN_NOTIONAL:
        return None

    as_of = utc_now()
    indicator = latest_indicator_as_of(db, instrument, as_of)
    fundamentals = latest_fundamentals_as_of(db, instrument, as_of)
    sentiment = aggregate_sentiment_as_of(db, instrument, as_of)
    technical_score = _technical_score(latest_price, indicator)
    fundamental_score = _fundamental_score(fundamentals)
    sentiment_score = _sentiment_score(sentiment)
    (
        momentum_score,
        expected_return_annual,
        expected_volatility_annual,
    ) = _momentum_score_from_ticks(ticks)
    composite = (
        0.30 * technical_score
        + 0.25 * fundamental_score
        + 0.25 * sentiment_score
        + 0.20 * momentum_score
    )
    return {
        "instrument": instrument,
        "asset_class": asset_class,
        "asset_class_label": asset_class_label(asset_class),
        "latest_price": latest_price,
        "avg_notional": round(avg_notional, 4),
        "coverage": round(coverage, 4),
        "technical_score": round(technical_score, 4),
        "fundamental_score": round(fundamental_score, 4),
        "sentiment_score": round(sentiment_score, 4),
        "momentum_score": round(momentum_score, 4),
        "composite_score": round(composite, 4),
        "expected_return_annual": round(expected_return_annual, 4),
        "expected_volatility_annual": round(expected_volatility_annual, 4),
    }


def _bounded_weights(
    scores: list[InstrumentScore],
    *,
    max_weight: float = _MAX_WEIGHT,
    min_cash_weight: float = _MIN_CASH_WEIGHT,
) -> tuple[dict[str, float], float]:
    raw = {score["instrument"]: max(score["composite_score"], 0.01) for score in scores}
    total_raw = sum(raw.values())
    if total_raw <= 0:
        raise ValueError("Nao foi possivel calcular pesos de alocacao.")
    target_total = max(0.0, 1.0 - min_cash_weight)
    weights = {
        instrument: (value / total_raw) * target_total
        for instrument, value in raw.items()
    }
    uncapped = set(weights)
    while True:
        excess = 0.0
        capped_now: set[str] = set()
        for instrument in uncapped:
            if weights[instrument] > max_weight:
                excess += weights[instrument] - max_weight
                weights[instrument] = max_weight
                capped_now.add(instrument)
        uncapped -= capped_now
        if excess <= 1e-9 or not uncapped:
            break
        uncapped_total = sum(weights[instrument] for instrument in uncapped)
        if uncapped_total <= 0:
            break
        for instrument in uncapped:
            weights[instrument] += excess * (weights[instrument] / uncapped_total)

    total_weight = sum(weights.values())
    cash_weight = max(0.0, 1.0 - total_weight)
    if cash_weight < min_cash_weight:
        deficit = min_cash_weight - cash_weight
        adjustable = sorted(weights.items(), key=lambda item: item[1], reverse=True)
        for instrument, weight in adjustable:
            reducible = max(0.0, weight - 0.01)
            reduction = min(deficit, reducible)
            weights[instrument] -= reduction
            deficit -= reduction
            if deficit <= 1e-9:
                break
        cash_weight = max(0.0, 1.0 - sum(weights.values()))
    return weights, cash_weight


def _next_plan_version(db: Session, user_id: int) -> int:
    latest = db.scalar(
        select(AllocationPlan)
        .where(AllocationPlan.user_id == user_id)
        .order_by(desc(AllocationPlan.version), desc(AllocationPlan.id))
        .limit(1)
    )
    if latest is None:
        return 1
    return int(latest.version) + 1


def _plan_payload_from_row(db: Session, row: AllocationPlan) -> AllocationPlanPayload:
    assets_rows = list(
        db.scalars(
            select(AllocationAsset)
            .where(AllocationAsset.plan_id == row.id)
            .order_by(AllocationAsset.weight_pct.desc(), AllocationAsset.instrument.asc())
        )
    )
    assets: list[AllocationAssetPayload]
    if assets_rows:
        assets = []
        for asset in assets_rows:
            row_asset_class = classify_instrument(asset.instrument)
            assets.append(
                {
                    "ticker": asset.instrument,
                    "asset_class": row_asset_class,
                    "asset_class_label": asset_class_label(row_asset_class),
                    "weight_pct": round(asset.weight_pct, 4),
                    "value_brl": round(asset.value_brl, 2),
                    "shares_approx": int(asset.shares_approx),
                    "entry_price_target": round(asset.entry_price_target, 4),
                    "stop_loss": round(asset.stop_loss, 4),
                    "thesis_id": asset.thesis_id,
                    "score_composite": round(asset.score_composite, 4),
                }
            )
    else:
        raw_assets = json.loads(row.assets_json)
        assets = [
            {
                "ticker": str(item.get("ticker", "")),
                "asset_class": str(
                    item.get("asset_class")
                    or classify_instrument(str(item.get("ticker", "")))
                ),
                "asset_class_label": str(
                    item.get("asset_class_label")
                    or asset_class_label(
                        classify_instrument(str(item.get("ticker", "")))
                    )
                ),
                "weight_pct": float(item.get("weight_pct", 0.0)),
                "value_brl": float(item.get("value_brl", 0.0)),
                "shares_approx": int(item.get("shares_approx", 0)),
                "entry_price_target": float(item.get("entry_price_target", 0.0)),
                "stop_loss": float(item.get("stop_loss", 0.0)),
                "thesis_id": str(item.get("thesis_id")) if item.get("thesis_id") else None,
                "score_composite": float(item.get("score_composite", 0.0)),
            }
            for item in raw_assets
            if isinstance(item, dict)
        ]
    volatility = max(float(row.expected_return_annual) / max(float(row.expected_sharpe), 1e-9), 0.0)
    diversification_score = 1.0 - sum((asset["weight_pct"] / 100.0) ** 2 for asset in assets)
    return {
        "plan_id": row.id,
        "user_id": row.user_id,
        "version": row.version,
        "capital_brl": round(row.capital_brl, 2),
        "risk_profile": row.risk_profile,
        "assets": assets,
        "expected_sharpe": round(row.expected_sharpe, 4),
        "expected_return_annual": round(row.expected_return_annual, 4),
        "expected_volatility_annual": round(volatility, 4),
        "max_drawdown_estimate": round(row.max_drawdown_estimate, 4),
        "diversification_score": round(diversification_score, 4),
        "rationale_text": row.rationale_text,
        "llm_model_version": row.llm_model_version,
        "status": row.status,
        "created_at": row.created_at,
    }


def allocate_portfolio(
    db: Session,
    *,
    user_id: int,
    capital_brl: float,
    risk_profile: str,
    instruments: list[str] | None = None,
) -> AllocationPlanPayload:
    if capital_brl < 1000:
        raise ValueError("capital_brl deve ser no minimo 1000.")

    universe = _candidate_universe(db, instruments=instruments)
    if not universe:
        raise ValueError("Nao ha dados reais suficientes para construir alocacao.")

    scored = [
        score
        for instrument in universe
        if (score := _score_instrument(db, instrument)) is not None
    ]
    if not scored:
        raise ValueError("Nenhum ativo elegivel apos filtros de dados reais.")

    scored.sort(key=lambda item: item["composite_score"], reverse=True)
    selected = scored[: min(_TOP_SELECTION, len(scored))]
    weights, cash_weight = _bounded_weights(selected)

    weighted_return = sum(
        (weights[item["instrument"]] * item["expected_return_annual"]) for item in selected
    )
    weighted_volatility = sum(
        (weights[item["instrument"]] * max(item["expected_volatility_annual"], 0.01))
        for item in selected
    )
    expected_sharpe = weighted_return / max(weighted_volatility, 1e-9)
    max_drawdown_estimate = max(0.05, weighted_volatility * 1.8)

    assets_payload: list[AllocationAssetPayload] = []
    for item in selected:
        ticker = item["instrument"]
        item_asset_class = item["asset_class"]
        weight = weights[ticker]
        value_brl = capital_brl * weight
        entry_price = item["latest_price"]
        shares = int(value_brl / max(entry_price, 0.01))
        assets_payload.append(
            {
                "ticker": ticker,
                "asset_class": item_asset_class,
                "asset_class_label": asset_class_label(item_asset_class),
                "weight_pct": round(weight * 100, 4),
                "value_brl": round(value_brl, 2),
                "shares_approx": shares,
                "entry_price_target": round(entry_price, 4),
                "stop_loss": round(entry_price * 0.9, 4),
                "thesis_id": None,
                "score_composite": round(item["composite_score"], 4),
            }
        )

    if cash_weight > 0:
        assets_payload.append(
            {
                "ticker": "CASH-BRL",
                "asset_class": "cash",
                "asset_class_label": asset_class_label("cash"),
                "weight_pct": round(cash_weight * 100, 4),
                "value_brl": round(capital_brl * cash_weight, 2),
                "shares_approx": 1,
                "entry_price_target": 1.0,
                "stop_loss": 0.0,
                "thesis_id": None,
                "score_composite": 1.0,
            }
        )

    selected_classes = sorted({item["asset_class_label"] for item in selected})
    rationale = (
        f"Plano autonomo multiativo com {len(selected)} ativos elegiveis "
        f"({', '.join(selected_classes)}), cobrindo liquidez e pontuacao multifator. "
        f"Sharpe esperado {expected_sharpe:.2f}, retorno anual estimado "
        f"{weighted_return * 100:.2f}% e drawdown estimado "
        f"{max_drawdown_estimate * 100:.2f}%."
    )
    rationale = anti_recommendation_text(rationale)
    assert_compliant_copy(rationale)

    for active_plan in db.scalars(
        select(AllocationPlan)
        .where(AllocationPlan.user_id == user_id)
        .where(AllocationPlan.status == "ACTIVE")
    ):
        active_plan.status = "SUPERSEDED"

    version = _next_plan_version(db, user_id)
    now_iso = isoformat(utc_now())
    plan_row = AllocationPlan(
        user_id=user_id,
        version=version,
        capital_brl=round(capital_brl, 2),
        risk_profile=risk_profile,
        assets_json=json.dumps(assets_payload, ensure_ascii=True, sort_keys=True),
        expected_sharpe=round(expected_sharpe, 4),
        expected_return_annual=round(weighted_return, 4),
        max_drawdown_estimate=round(max_drawdown_estimate, 4),
        rationale_text=rationale,
        llm_model_version="baseline-v1",
        created_at=now_iso,
        status="ACTIVE",
        job_id=None,
    )
    db.add(plan_row)
    db.flush()

    for asset in assets_payload:
        db.add(
            AllocationAsset(
                plan_id=plan_row.id,
                instrument=asset["ticker"],
                weight_pct=asset["weight_pct"],
                value_brl=asset["value_brl"],
                shares_approx=asset["shares_approx"],
                entry_price_target=asset["entry_price_target"],
                stop_loss=asset["stop_loss"],
                thesis_id=asset["thesis_id"],
                score_composite=asset["score_composite"],
            )
        )

    db.commit()
    db.refresh(plan_row)
    return _plan_payload_from_row(db, plan_row)


def get_allocation_plan(db: Session, *, user_id: int, plan_id: int) -> AllocationPlanPayload:
    plan = db.scalar(
        select(AllocationPlan)
        .where(AllocationPlan.id == plan_id)
        .where(AllocationPlan.user_id == user_id)
        .limit(1)
    )
    if plan is None:
        raise ValueError("AllocationPlan nao encontrado.")
    return _plan_payload_from_row(db, plan)


def get_latest_allocation_plan(db: Session, *, user_id: int) -> AllocationPlanPayload:
    plan = db.scalar(
        select(AllocationPlan)
        .where(AllocationPlan.user_id == user_id)
        .order_by(desc(AllocationPlan.version), desc(AllocationPlan.id))
        .limit(1)
    )
    if plan is None:
        raise ValueError("Usuario ainda nao possui AllocationPlan.")
    return _plan_payload_from_row(db, plan)


def _target_weights_for_plan(db: Session, plan: AllocationPlan) -> dict[str, float]:
    assets = list(
        db.scalars(
            select(AllocationAsset).where(AllocationAsset.plan_id == plan.id)
        )
    )
    if not assets:
        raw_assets = json.loads(plan.assets_json)
        return {
            str(asset.get("ticker", "")).upper(): float(asset.get("weight_pct", 0.0)) / 100.0
            for asset in raw_assets
            if isinstance(asset, dict)
        }
    return {
        asset.instrument.upper(): float(asset.weight_pct) / 100.0
        for asset in assets
    }


def build_rebalance_plan(
    db: Session,
    *,
    user_id: int,
    plan_id: int | None = None,
) -> RebalancePlanPayload:
    if plan_id is None:
        plan = db.scalar(
            select(AllocationPlan)
            .where(AllocationPlan.user_id == user_id)
            .order_by(desc(AllocationPlan.version), desc(AllocationPlan.id))
            .limit(1)
        )
    else:
        plan = db.scalar(
            select(AllocationPlan)
            .where(AllocationPlan.id == plan_id)
            .where(AllocationPlan.user_id == user_id)
            .limit(1)
        )
    if plan is None:
        raise ValueError("Nenhum AllocationPlan disponivel para rebalance.")

    target_weights = _target_weights_for_plan(db, plan)
    target_instruments = {instrument for instrument in target_weights if instrument != "CASH-BRL"}
    positions = list(
        db.scalars(
            select(PortfolioPosition).where(PortfolioPosition.user_id == user_id)
        )
    )
    current_values: dict[str, float] = {}
    for position in positions:
        latest_price = _latest_price(db, position.instrument) or float(position.average_price)
        current_values[position.instrument.upper()] = float(position.quantity) * latest_price
    current_total = sum(current_values.values())
    if current_total <= 0:
        current_total = float(plan.capital_brl)

    orders: list[RebalanceOrderPayload] = []
    all_instruments = sorted(target_instruments.union(current_values))
    for instrument in all_instruments:
        target_weight = target_weights.get(instrument, 0.0)
        current_value = current_values.get(instrument, 0.0)
        current_weight = current_value / max(current_total, 1e-9)
        drift = target_weight - current_weight
        drift_pct = drift * 100
        if abs(drift_pct) < 3.0:
            continue
        adjustment_value = current_total * drift
        action = "BUY" if adjustment_value > 0 else "SELL"
        orders.append(
            {
                "instrument": instrument,
                "action": action,
                "current_weight_pct": round(current_weight * 100, 4),
                "target_weight_pct": round(target_weight * 100, 4),
                "drift_pct": round(drift_pct, 4),
                "adjustment_value_brl": round(abs(adjustment_value), 2),
            }
        )

    total_drift_pct = round(sum(abs(order["drift_pct"]) for order in orders), 4)
    generated_at = isoformat(utc_now())
    row = RebalancePlan(
        user_id=user_id,
        plan_id=plan.id,
        generated_at=generated_at,
        orders_json=json.dumps(orders, ensure_ascii=True, sort_keys=True),
        total_drift_pct=total_drift_pct,
        status="PENDING",
        executed_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "rebalance_plan_id": row.id,
        "user_id": user_id,
        "allocation_plan_id": plan.id,
        "generated_at": generated_at,
        "total_drift_pct": total_drift_pct,
        "status": row.status,
        "orders": orders,
    }

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from statistics import mean, pstdev
from typing import TypedDict

from app.models import BacktestRun, BacktestTrade, IndicatorSnapshot, Signal
from app.services.alerts import maybe_emit_backtest_alerts
from app.services.audit import record_audit_event
from app.services.news import latest_news_as_of
from app.services.paper_trading import (
    apply_execution_friction,
    compute_execution_friction,
    estimate_operational_costs,
    latest_market_tick,
)
from app.services.risk import evaluate_risk
from app.services.signals import evaluate_signal_context
from app.services.utils import isoformat, utc_now
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

MONTE_CARLO_SIMULATIONS = 250
OVERFITTING_LOOKBACK_HOURS = 24
OVERFITTING_THRESHOLD = 6


class BacktestPerformanceMetrics(TypedDict):
    hit_rate: float
    payoff_ratio: float
    expectancy_pct: float
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    omega_ratio: float
    profit_factor: float


class BacktestRobustnessMetrics(TypedDict):
    monte_carlo_paths: int
    monte_carlo_p05_return_pct: float
    monte_carlo_p50_return_pct: float
    monte_carlo_p95_return_pct: float
    monte_carlo_positive_rate: float


class BacktestValidationSnapshot(TypedDict):
    performance: BacktestPerformanceMetrics
    robustness: BacktestRobustnessMetrics
    risk_flags: list[str]


def compute_max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak == 0:
            continue
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return round(max_drawdown * 100, 4)


def compute_performance_metrics(
    accepted_returns: list[float],
    total_return_pct: float,
    max_drawdown_pct: float,
) -> BacktestPerformanceMetrics:
    if not accepted_returns:
        return {
            "hit_rate": 0.0,
            "payoff_ratio": 0.0,
            "expectancy_pct": 0.0,
            "volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "omega_ratio": 0.0,
            "profit_factor": 0.0,
        }

    wins = [value for value in accepted_returns if value > 0]
    losses = [value for value in accepted_returns if value < 0]
    mean_return = mean(accepted_returns)
    volatility_pct = pstdev(accepted_returns) if len(accepted_returns) > 1 else 0.0
    downside_volatility = pstdev(losses) if len(losses) > 1 else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    avg_win = mean(wins) if wins else 0.0
    avg_loss = abs(mean(losses)) if losses else 0.0
    positive_sum = sum(max(value, 0.0) for value in accepted_returns)
    negative_sum = abs(sum(min(value, 0.0) for value in accepted_returns))

    sharpe_ratio = 0.0
    if volatility_pct > 0:
        sharpe_ratio = (mean_return / volatility_pct) * (len(accepted_returns) ** 0.5)

    sortino_ratio = 0.0
    if downside_volatility > 0:
        sortino_ratio = (mean_return / downside_volatility) * (len(accepted_returns) ** 0.5)

    profit_factor = 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = gross_profit

    omega_ratio = 0.0
    if negative_sum > 0:
        omega_ratio = positive_sum / negative_sum
    elif positive_sum > 0:
        omega_ratio = positive_sum

    return {
        "hit_rate": round((len(wins) / len(accepted_returns)) * 100, 4),
        "payoff_ratio": round(avg_win / avg_loss, 4) if avg_loss > 0 else 0.0,
        "expectancy_pct": round(mean_return, 4),
        "volatility_pct": round(volatility_pct, 4),
        "sharpe_ratio": round(sharpe_ratio, 4),
        "sortino_ratio": round(sortino_ratio, 4),
        "calmar_ratio": (
            round(total_return_pct / max_drawdown_pct, 4)
            if max_drawdown_pct > 0
            else 0.0
        ),
        "omega_ratio": round(omega_ratio, 4),
        "profit_factor": round(profit_factor, 4),
    }


def compute_robustness_metrics(accepted_returns: list[float]) -> BacktestRobustnessMetrics:
    if not accepted_returns:
        return {
            "monte_carlo_paths": 0,
            "monte_carlo_p05_return_pct": 0.0,
            "monte_carlo_p50_return_pct": 0.0,
            "monte_carlo_p95_return_pct": 0.0,
            "monte_carlo_positive_rate": 0.0,
        }

    seed_source = ",".join(f"{value:.6f}" for value in accepted_returns)
    seed = int(hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)

    simulations: list[float] = []
    for _ in range(MONTE_CARLO_SIMULATIONS):
        path = accepted_returns[:]
        rng.shuffle(path)
        equity = 1.0
        for value in path:
            equity *= 1 + (value / 100)
        simulations.append((equity - 1.0) * 100)

    simulations.sort()
    last_index = len(simulations) - 1

    def percentile(level: float) -> float:
        if last_index < 0:
            return 0.0
        position = int(round(last_index * level))
        return simulations[position]

    positive_rate = (sum(1 for value in simulations if value > 0) / len(simulations)) * 100
    return {
        "monte_carlo_paths": MONTE_CARLO_SIMULATIONS,
        "monte_carlo_p05_return_pct": round(percentile(0.05), 4),
        "monte_carlo_p50_return_pct": round(percentile(0.50), 4),
        "monte_carlo_p95_return_pct": round(percentile(0.95), 4),
        "monte_carlo_positive_rate": round(positive_rate, 4),
    }


def _recent_backtest_count(
    db: Session,
    user_id: int,
    instrument: str,
    as_of: datetime,
) -> int:
    window_start = as_of - timedelta(hours=OVERFITTING_LOOKBACK_HOURS)
    runs = list(
        db.scalars(
            select(BacktestRun)
            .where(BacktestRun.user_id == user_id)
            .where(BacktestRun.instrument == instrument.upper())
            .order_by(desc(BacktestRun.id))
            .limit(30)
        )
    )
    return sum(
        1
        for run in runs
        if datetime.fromisoformat(run.started_at).astimezone(UTC) >= window_start
    )


def _apply_exit_friction(reference_price: float, spread_bps: float, slippage_bps: float) -> float:
    total_bps = spread_bps + slippage_bps
    return round(reference_price * (1 - (total_bps / 10_000)), 4)


def _counterfactual_net_return_pct(
    *,
    quantity: int,
    entry_price: float,
    entry_volume: int,
    exit_price: float,
    exit_volume: int,
) -> tuple[float, dict[str, float]]:
    entry_friction = compute_execution_friction(quantity, entry_volume)
    exit_friction = compute_execution_friction(quantity, exit_volume)

    entry_execution_price = apply_execution_friction(entry_price, entry_friction)
    exit_execution_price = _apply_exit_friction(
        exit_price,
        exit_friction["spread_bps"],
        exit_friction["slippage_bps"],
    )

    entry_notional = round(entry_execution_price * quantity, 2)
    exit_notional = round(exit_execution_price * quantity, 2)
    entry_cost = estimate_operational_costs(entry_notional)["total_cost"]
    exit_cost = estimate_operational_costs(exit_notional)["total_cost"]
    total_cost = round(entry_cost + exit_cost, 2)

    gross_pnl = round(exit_notional - entry_notional, 2)
    estimated_tax = round(max(gross_pnl, 0.0) * 0.15, 2)
    net_pnl = round(gross_pnl - total_cost - estimated_tax, 2)

    net_return_pct = 0.0
    if entry_notional > 0:
        net_return_pct = round((net_pnl / entry_notional) * 100, 4)

    diagnostics = {
        "entry_reference_price": entry_price,
        "entry_execution_price": entry_execution_price,
        "exit_reference_price": exit_price,
        "exit_execution_price": exit_execution_price,
        "entry_notional": entry_notional,
        "exit_notional": exit_notional,
        "gross_pnl": gross_pnl,
        "total_cost": total_cost,
        "estimated_tax": estimated_tax,
    }
    return net_return_pct, diagnostics


def build_validation_snapshot(
    *,
    accepted_returns: list[float],
    total_return_pct: float,
    max_drawdown_pct: float,
    recent_backtest_count: int,
) -> BacktestValidationSnapshot:
    performance = compute_performance_metrics(
        accepted_returns,
        total_return_pct,
        max_drawdown_pct,
    )
    robustness = compute_robustness_metrics(accepted_returns)
    risk_flags: list[str] = []
    if len(accepted_returns) < 5:
        risk_flags.append("amostra_curta")
    if max_drawdown_pct >= 12:
        risk_flags.append("drawdown_elevado")
    if performance["profit_factor"] < 1:
        risk_flags.append("profit_factor_abaixo_de_1")
    if recent_backtest_count >= OVERFITTING_THRESHOLD:
        risk_flags.append("excesso_de_tuning")
    return {
        "performance": performance,
        "robustness": robustness,
        "risk_flags": risk_flags,
    }


def trades_for_run(db: Session, run_id: int) -> list[BacktestTrade]:
    return list(
        db.scalars(
            select(BacktestTrade)
            .where(BacktestTrade.run_id == run_id)
            .order_by(BacktestTrade.signal_time.asc())
        )
    )


def build_validation_snapshot_for_run(
    db: Session,
    run: BacktestRun,
    *,
    recent_backtest_count: int = 0,
) -> BacktestValidationSnapshot:
    trades = trades_for_run(db, run.id)
    accepted_returns = [
        trade.pnl_pct for trade in trades if trade.risk_decision == "accepted"
    ]
    return build_validation_snapshot(
        accepted_returns=accepted_returns,
        total_return_pct=run.total_return_pct,
        max_drawdown_pct=run.max_drawdown_pct,
        recent_backtest_count=recent_backtest_count,
    )


def run_backtest(db: Session, user_id: int, instrument: str, quantity: int) -> BacktestRun:
    started_at = utc_now()
    snapshots = list(
        db.scalars(
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.instrument == instrument.upper())
            .order_by(IndicatorSnapshot.availability_time.asc())
        )
    )
    if len(snapshots) < 2:
        raise ValueError("Backtest requer ao menos duas janelas de indicadores")

    recent_runs = _recent_backtest_count(db, user_id, instrument, started_at)

    trades: list[BacktestTrade] = []
    accepted_returns: list[float] = []
    equity_curve = [1.0]
    accepted_count = 0
    rejected_count = 0

    for current_snapshot, next_snapshot in zip(snapshots[:-1], snapshots[1:], strict=False):
        as_of = datetime.fromisoformat(current_snapshot.availability_time)
        news = latest_news_as_of(db, instrument.upper(), as_of)
        anti_hype_score = (
            round(mean(article.anti_hype_score for article in news), 2)
            if news
            else 75.0
        )
        signal_type, confidence, rationale = evaluate_signal_context(
            current_snapshot,
            instrument,
            anti_hype_score,
        )
        simulated_signal = Signal(
            user_id=user_id,
            instrument=instrument.upper(),
            reference_time=current_snapshot.reference_time,
            availability_time=current_snapshot.availability_time,
            signal_type=signal_type,
            confidence=confidence,
            rationale=rationale,
            anti_hype_score=anti_hype_score,
        )
        db.add(simulated_signal)
        db.flush()

        entry_tick = latest_market_tick(db, instrument.upper(), as_of)
        entry_price = float(entry_tick.price)
        risk_decision = evaluate_risk(
            db,
            user_id,
            simulated_signal,
            quantity,
            entry_price,
            as_of,
        )
        exit_tick = latest_market_tick(
            db,
            instrument.upper(),
            datetime.fromisoformat(next_snapshot.availability_time).astimezone(UTC),
        )
        exit_price = float(exit_tick.price)
        counterfactual_return_pct, diagnostics = _counterfactual_net_return_pct(
            quantity=quantity,
            entry_price=entry_price,
            entry_volume=int(entry_tick.volume),
            exit_price=exit_price,
            exit_volume=int(exit_tick.volume),
        )

        realized_return_pct = 0.0
        if risk_decision.decision == "accepted":
            accepted_count += 1
            realized_return_pct = counterfactual_return_pct
            accepted_returns.append(realized_return_pct)
            equity_curve.append(equity_curve[-1] * (1 + (realized_return_pct / 100)))
        else:
            rejected_count += 1
            equity_curve.append(equity_curve[-1])

        trade_rationale = (
            f"{rationale} | sim_realista: "
            f"counterfactual={counterfactual_return_pct:.4f}% "
            f"realizado={realized_return_pct:.4f}% "
            f"custos={diagnostics['total_cost']:.2f} "
            f"ir={diagnostics['estimated_tax']:.2f}"
        )
        trade = BacktestTrade(
            run_id=0,
            instrument=instrument.upper(),
            signal_time=current_snapshot.availability_time,
            signal_type=signal_type,
            confidence=confidence,
            anti_hype_score=anti_hype_score,
            entry_price=diagnostics["entry_execution_price"],
            exit_price=diagnostics["exit_execution_price"],
            pnl_pct=realized_return_pct,
            risk_decision=risk_decision.decision,
            rationale=trade_rationale,
        )
        trades.append(trade)

    trade_count = len(trades)
    win_rate = (
        round((sum(1 for value in accepted_returns if value > 0) / len(accepted_returns)) * 100, 4)
        if accepted_returns
        else 0.0
    )
    total_return_pct = round((equity_curve[-1] - 1.0) * 100, 4)
    max_drawdown_pct = compute_max_drawdown(equity_curve)

    validation_snapshot = build_validation_snapshot(
        accepted_returns=accepted_returns,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        recent_backtest_count=recent_runs,
    )
    summary = (
        "Backtest com "
        f"{trade_count} sinais, {accepted_count} aceitos, "
        f"retorno {total_return_pct:.2f}%, "
        f"Sharpe {validation_snapshot['performance']['sharpe_ratio']:.2f}, "
        f"ProfitFactor {validation_snapshot['performance']['profit_factor']:.2f}."
    )
    if validation_snapshot["risk_flags"]:
        summary += f" Flags: {', '.join(validation_snapshot['risk_flags'])}."

    run = BacktestRun(
        user_id=user_id,
        instrument=instrument.upper(),
        started_at=isoformat(started_at),
        finished_at=isoformat(utc_now()),
        trade_count=trade_count,
        accepted_trade_count=accepted_count,
        rejected_trade_count=rejected_count,
        win_rate=win_rate,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        summary=summary,
    )
    db.add(run)
    db.flush()

    for trade in trades:
        trade.run_id = run.id
        db.add(trade)

    db.commit()
    db.refresh(run)
    maybe_emit_backtest_alerts(db, run, validation_snapshot)
    record_audit_event(
        db,
        "backtest.run.completed",
        {
            "run_id": run.id,
            "instrument": run.instrument,
            "trade_count": run.trade_count,
            "total_return_pct": run.total_return_pct,
            "validation_snapshot": validation_snapshot,
        },
        user_id,
    )
    return run

from __future__ import annotations

from statistics import mean

from app.models import (
    AlertEvent,
    BacktestRun,
    PaperOrder,
    PortfolioPosition,
    RiskDecision,
    Signal,
)
from app.services.backtest import build_validation_snapshot_for_run, trades_for_run
from app.services.utils import DISCLAIMER
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


def build_user_report(db: Session, user_id: int) -> dict[str, object]:
    positions = list(
        db.scalars(select(PortfolioPosition).where(PortfolioPosition.user_id == user_id))
    )
    orders = list(
        db.scalars(
            select(PaperOrder)
            .where(PaperOrder.user_id == user_id)
            .order_by(desc(PaperOrder.id))
            .limit(50)
        )
    )
    signals = list(
        db.scalars(
            select(Signal).where(Signal.user_id == user_id).order_by(desc(Signal.id)).limit(50)
        )
    )
    risks = list(
        db.scalars(
            select(RiskDecision)
            .where(RiskDecision.user_id == user_id)
            .order_by(desc(RiskDecision.id))
            .limit(50)
        )
    )
    alerts = list(
        db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == user_id)
            .order_by(desc(AlertEvent.id))
            .limit(50)
        )
    )
    backtests = list(
        db.scalars(
            select(BacktestRun)
            .where(BacktestRun.user_id == user_id)
            .order_by(desc(BacktestRun.id))
            .limit(10)
        )
    )

    strategy_validation: dict[str, object] | None = None
    top_backtest_trades: list[dict[str, object]] = []
    if backtests:
        validations = [build_validation_snapshot_for_run(db, run) for run in backtests]
        sharpe_values = [item["performance"]["sharpe_ratio"] for item in validations]
        sortino_values = [item["performance"]["sortino_ratio"] for item in validations]
        profit_factors = [item["performance"]["profit_factor"] for item in validations]
        monte_carlo_positive_rates = [
            item["robustness"]["monte_carlo_positive_rate"] for item in validations
        ]
        all_risk_flags = sorted(
            {
                flag
                for snapshot in validations
                for flag in snapshot["risk_flags"]
            }
        )

        best_run = max(backtests, key=lambda run: run.total_return_pct)
        worst_drawdown_run = max(backtests, key=lambda run: run.max_drawdown_pct)
        strategy_validation = {
            "run_count": len(backtests),
            "average_return_pct": round(mean(run.total_return_pct for run in backtests), 4),
            "average_win_rate": round(mean(run.win_rate for run in backtests), 4),
            "average_max_drawdown_pct": round(mean(run.max_drawdown_pct for run in backtests), 4),
            "average_sharpe_ratio": round(mean(sharpe_values), 4),
            "average_sortino_ratio": round(mean(sortino_values), 4),
            "average_profit_factor": round(mean(profit_factors), 4),
            "average_monte_carlo_positive_rate": round(mean(monte_carlo_positive_rates), 4),
            "best_run": {
                "run_id": best_run.id,
                "instrument": best_run.instrument,
                "total_return_pct": best_run.total_return_pct,
            },
            "worst_drawdown_run": {
                "run_id": worst_drawdown_run.id,
                "instrument": worst_drawdown_run.instrument,
                "max_drawdown_pct": worst_drawdown_run.max_drawdown_pct,
            },
            "risk_flags": all_risk_flags,
        }

        trade_rows: list[tuple[float, dict[str, object]]] = []
        for run in backtests:
            for trade in trades_for_run(db, run.id):
                if trade.risk_decision != "accepted":
                    continue
                trade_rows.append(
                    (
                        trade.pnl_pct,
                        {
                        "run_id": run.id,
                        "instrument": trade.instrument,
                        "signal_time": trade.signal_time,
                        "pnl_pct": trade.pnl_pct,
                        "rationale": trade.rationale,
                        },
                    )
                )
        trade_rows.sort(key=lambda row: row[0], reverse=True)
        top_backtest_trades = [row[1] for row in trade_rows[:5]]

    return {
        "user_id": user_id,
        "positions_count": len(positions),
        "orders_count": len(orders),
        "accepted_orders": sum(1 for order in orders if order.risk_status == "accepted"),
        "signals_count": len(signals),
        "average_signal_confidence": round(
            sum(signal.confidence for signal in signals) / len(signals), 4
        )
        if signals
        else 0.0,
        "risk_rejections": sum(1 for risk in risks if risk.decision != "accepted"),
        "alert_events": len(alerts),
        "latest_backtest": (
            {
                "run_id": backtests[0].id,
                "total_return_pct": backtests[0].total_return_pct,
                "max_drawdown_pct": backtests[0].max_drawdown_pct,
            }
            if backtests
            else None
        ),
        "strategy_validation": strategy_validation,
        "top_backtest_trades": top_backtest_trades,
        "disclaimer": DISCLAIMER,
    }

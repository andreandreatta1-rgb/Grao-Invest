from __future__ import annotations

from app.services.backtest import (
    build_validation_snapshot,
    compute_max_drawdown,
    compute_performance_metrics,
    compute_robustness_metrics,
)


def test_compute_max_drawdown() -> None:
    equity_curve = [1.0, 1.05, 1.02, 1.08, 0.99]
    assert compute_max_drawdown(equity_curve) == 8.3333


def test_compute_performance_metrics_with_mixed_returns() -> None:
    metrics = compute_performance_metrics(
        [1.5, -0.5, 2.0, -1.0],
        total_return_pct=1.9,
        max_drawdown_pct=3.2,
    )
    assert metrics["hit_rate"] == 50.0
    assert metrics["profit_factor"] > 1.0
    assert metrics["calmar_ratio"] > 0
    assert metrics["payoff_ratio"] > 1.0


def test_compute_robustness_metrics_is_deterministic() -> None:
    returns = [1.2, -0.4, 0.8, 1.0, -0.2]
    first = compute_robustness_metrics(returns)
    second = compute_robustness_metrics(returns)
    assert first == second
    assert first["monte_carlo_paths"] == 250
    assert first["monte_carlo_p95_return_pct"] >= first["monte_carlo_p05_return_pct"]


def test_build_validation_snapshot_flags_high_risk_patterns() -> None:
    snapshot = build_validation_snapshot(
        accepted_returns=[-0.8, -0.6],
        total_return_pct=-1.4,
        max_drawdown_pct=15.0,
        recent_backtest_count=7,
    )
    assert "amostra_curta" in snapshot["risk_flags"]
    assert "drawdown_elevado" in snapshot["risk_flags"]
    assert "profit_factor_abaixo_de_1" in snapshot["risk_flags"]
    assert "excesso_de_tuning" in snapshot["risk_flags"]

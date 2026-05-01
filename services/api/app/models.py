from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[str] = mapped_column(String(40))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(200))
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40))


class LoginAttemptState(Base):
    __tablename__ = "login_attempt_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    lock_level: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(40))


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    accepted_terms: Mapped[bool] = mapped_column(Boolean)
    accepted_privacy: Mapped[bool] = mapped_column(Boolean)
    consented_at: Mapped[str] = mapped_column(String(40))


class SuitabilityProfile(Base):
    __tablename__ = "suitability_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    investor_profile: Mapped[str] = mapped_column(String(50))
    time_horizon: Mapped[str] = mapped_column(String(50))
    risk_tolerance: Mapped[str] = mapped_column(String(50))
    liquidity_need: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[str] = mapped_column(String(40))


class MarketTick(Base):
    __tablename__ = "market_ticks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    event_time: Mapped[str] = mapped_column(String(40), index=True)
    ingest_time: Mapped[str] = mapped_column(String(40), index=True)
    price: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="BRL")
    source_payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class MarketProviderState(Base):
    __tablename__ = "market_provider_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_event_time: Mapped[str] = mapped_column(String(40))
    failover_threshold: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[str] = mapped_column(Text, default="{}")


class IndicatorSnapshot(Base):
    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    reference_time: Mapped[str] = mapped_column(String(40), index=True)
    availability_time: Mapped[str] = mapped_column(String(40), index=True)
    sma_5: Mapped[float] = mapped_column(Float)
    sma_10: Mapped[float] = mapped_column(Float)
    sma_20: Mapped[float] = mapped_column(Float, default=0.0)
    ema_5: Mapped[float] = mapped_column(Float)
    ema_12: Mapped[float] = mapped_column(Float, default=0.0)
    ema_26: Mapped[float] = mapped_column(Float, default=0.0)
    rsi_14: Mapped[float] = mapped_column(Float)
    volatility_10: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_5: Mapped[float] = mapped_column(Float, default=0.0)
    macd: Mapped[float] = mapped_column(Float, default=0.0)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    reference_time: Mapped[str] = mapped_column(String(40), index=True)
    availability_time: Mapped[str] = mapped_column(String(40), index=True)
    signal_type: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    anti_hype_score: Mapped[float] = mapped_column(Float, default=100.0)
    xai_payload: Mapped[str] = mapped_column(Text, default="{}")
    signal_status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expiry_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"))
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    reference_price: Mapped[float] = mapped_column(Float)
    execution_price: Mapped[float] = mapped_column(Float)
    gross_amount: Mapped[float] = mapped_column(Float)
    estimated_cost: Mapped[float] = mapped_column(Float)
    estimated_tax: Mapped[float] = mapped_column(Float)
    risk_status: Mapped[str] = mapped_column(String(32), default="accepted")
    risk_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40))


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    average_price: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[str] = mapped_column(String(40))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), index=True)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    headline: Mapped[str] = mapped_column(String(400))
    source_name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(32))
    credibility_score: Mapped[float] = mapped_column(Float)
    anti_hype_score: Mapped[float] = mapped_column(Float)
    published_at: Mapped[str] = mapped_column(String(40), index=True)
    captured_at: Mapped[str] = mapped_column(String(40), index=True)


class NewsAnalysisSnapshot(Base):
    __tablename__ = "news_analysis_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    sector: Mapped[str] = mapped_column(String(64))
    theme: Mapped[str] = mapped_column(String(64))
    sentiment_label: Mapped[str] = mapped_column(String(16))
    sentiment_score: Mapped[float] = mapped_column(Float)
    magnitude_score: Mapped[float] = mapped_column(Float)
    model_confidence: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="pt-BR")
    availability_time: Mapped[str] = mapped_column(String(40), index=True)


class FundamentalSnapshot(Base):
    __tablename__ = "fundamental_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(32))
    reference_time: Mapped[str] = mapped_column(String(40), index=True)
    availability_time: Mapped[str] = mapped_column(String(40), index=True)
    pe_ratio: Mapped[float] = mapped_column(Float)
    pb_ratio: Mapped[float] = mapped_column(Float)
    ev_ebitda: Mapped[float] = mapped_column(Float)
    dividend_yield: Mapped[float] = mapped_column(Float)
    roe: Mapped[float] = mapped_column(Float)
    net_margin: Mapped[float] = mapped_column(Float)
    revenue_growth: Mapped[float] = mapped_column(Float)
    payout_ratio: Mapped[float] = mapped_column(Float)
    version_tag: Mapped[str] = mapped_column(String(64))


class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[str] = mapped_column(String(40))
    released_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class RiskDecision(Base):
    __tablename__ = "risk_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[str] = mapped_column(String(40))
    portfolio_exposure: Mapped[float] = mapped_column(Float, default=0.0)
    projected_exposure: Mapped[float] = mapped_column(Float, default=0.0)


class KillSwitchState(Base):
    __tablename__ = "kill_switch_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_type: Mapped[str] = mapped_column(String(32), index=True)
    scope_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[str] = mapped_column(String(40))
    released_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[str] = mapped_column(String(40))
    finished_at: Mapped[str] = mapped_column(String(40))
    trade_count: Mapped[int] = mapped_column(Integer)
    accepted_trade_count: Mapped[int] = mapped_column(Integer)
    rejected_trade_count: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float] = mapped_column(Float)
    total_return_pct: Mapped[float] = mapped_column(Float)
    max_drawdown_pct: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text)


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    signal_time: Mapped[str] = mapped_column(String(40))
    signal_type: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    anti_hype_score: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    risk_decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)


class AgentJobLog(Base):
    __tablename__ = "agent_job_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[str] = mapped_column(String(40))
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worker_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    last_run_at: Mapped[str] = mapped_column(String(40), index=True)
    next_run_at: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cycles_today: Mapped[int] = mapped_column(Integer, default=0)


class LLMCostLog(Base):
    __tablename__ = "llm_cost_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    module: Mapped[str] = mapped_column(String(32), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(80), default="")


class AllocationPlan(Base):
    __tablename__ = "allocation_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    capital_brl: Mapped[float] = mapped_column(Float)
    risk_profile: Mapped[str] = mapped_column(String(24))
    assets_json: Mapped[str] = mapped_column(Text, default="[]")
    expected_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    expected_return_annual: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    rationale_text: Mapped[str] = mapped_column(Text, default="")
    llm_model_version: Mapped[str] = mapped_column(String(80), default="baseline-v1")
    created_at: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", index=True)
    job_id: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AllocationAsset(Base):
    __tablename__ = "allocation_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("allocation_plans.id"), index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    weight_pct: Mapped[float] = mapped_column(Float)
    value_brl: Mapped[float] = mapped_column(Float)
    shares_approx: Mapped[int] = mapped_column(Integer)
    entry_price_target: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    thesis_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    score_composite: Mapped[float] = mapped_column(Float, default=0.0)


class RebalancePlan(Base):
    __tablename__ = "rebalance_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("allocation_plans.id"), index=True)
    generated_at: Mapped[str] = mapped_column(String(40), index=True)
    orders_json: Mapped[str] = mapped_column(Text, default="[]")
    total_drift_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    executed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(32))
    instrument: Mapped[str | None] = mapped_column(String(32), nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(40))


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    alert_rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32))
    instrument: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40))

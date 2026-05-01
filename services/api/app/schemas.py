from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    accepted_terms: bool
    accepted_privacy: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: str | None = None


class MFASetupRequest(BaseModel):
    user_id: int


class MFAVerifyRequest(BaseModel):
    user_id: int
    otp_code: str = Field(min_length=6, max_length=6)


class SuitabilityRequest(BaseModel):
    user_id: int
    time_horizon: str
    risk_tolerance: str
    liquidity_need: str
    investment_experience: str


class MarketTickIngestRequest(BaseModel):
    instrument: str
    provider: str
    event_time: datetime
    price: float = Field(gt=0)
    volume: int = Field(ge=0)
    currency: str = "BRL"
    source_payload_id: str | None = None


class MarketTickLiveIngestRequest(MarketTickIngestRequest):
    auto_recompute_indicators: bool = True


class MarketProviderStatusRequest(BaseModel):
    provider_name: str = Field(min_length=2, max_length=64)
    role: str = Field(pattern="^(primary|secondary)$")
    status: str = Field(pattern="^(healthy|degraded|failed)$")
    failure_increment: int = Field(default=1, ge=0, le=10)
    failover_threshold: int = Field(default=3, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=400)


class RecomputeIndicatorsRequest(BaseModel):
    instrument: str


class RecomputePortfolioIndicatorsRequest(BaseModel):
    instruments: list[str] = Field(min_length=1, max_length=20)


class GenerateSignalRequest(BaseModel):
    user_id: int
    instrument: str


class NewsIngestRequest(BaseModel):
    instrument: str
    headline: str = Field(min_length=4, max_length=400)
    source_name: str = Field(min_length=2, max_length=120)
    source_type: str = Field(min_length=2, max_length=32)
    published_at: datetime
    source_url: str | None = Field(default=None, max_length=400)
    language: str = Field(default="pt-BR", min_length=2, max_length=8)


class ExternalNewsSyncRequest(BaseModel):
    user_id: int
    start_date: date
    end_date: date
    instruments: list[str] = Field(min_length=1, max_length=60)
    max_articles_per_instrument: int = Field(default=80, ge=1, le=500)
    language: str = Field(default="pt-BR", min_length=2, max_length=8)


class ExternalFundamentalsSyncRequest(BaseModel):
    user_id: int
    provider_name: str = Field(default="auto", min_length=2, max_length=64)
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=4000)
    max_instruments: int = Field(default=600, ge=1, le=4000)
    only_missing: bool = True


class FundamentalIngestRequest(BaseModel):
    instrument: str
    source_name: str = Field(min_length=2, max_length=120)
    source_type: str = Field(min_length=2, max_length=32)
    reference_time: datetime
    availability_time: datetime
    pe_ratio: float = Field(ge=0)
    pb_ratio: float = Field(ge=0)
    ev_ebitda: float = Field(ge=0)
    dividend_yield: float = Field(ge=0)
    roe: float = Field(ge=-1000, le=1000)
    net_margin: float = Field(ge=-1000, le=1000)
    revenue_growth: float = Field(ge=-1000, le=1000)
    payout_ratio: float = Field(ge=0, le=1000)
    version_tag: str = Field(min_length=1, max_length=64)


class CreatePaperOrderRequest(BaseModel):
    user_id: int
    quantity: int = Field(gt=0)


class BacktestRunRequest(BaseModel):
    user_id: int
    instrument: str
    quantity: int = Field(default=10, gt=0)


class KillSwitchUpdateRequest(BaseModel):
    scope_type: str = Field(pattern="^(global|user|instrument)$")
    scope_id: str = Field(min_length=1, max_length=64)
    status: str = Field(pattern="^(active|released)$")
    reason: str = Field(min_length=4, max_length=400)


class AlertRuleRequest(BaseModel):
    user_id: int
    rule_type: str = Field(
        pattern=(
            "^("
            "signal_confidence|anti_hype|circuit_breaker|news_magnitude|"
            "backtest_return|backtest_drawdown|backtest_win_rate"
            ")$"
        )
    )
    instrument: str | None = None
    threshold_value: float | None = None


class PortfolioAllocateRequest(BaseModel):
    user_id: int | None = None
    capital_brl: float = Field(ge=1000, le=10000000)
    risk_profile: str = Field(pattern="^(conservador|moderado|arrojado)$")
    universe: str = Field(default="ibov", pattern="^(ibov|smll|custom)$")
    custom_instruments: list[str] | None = Field(default=None, min_length=1, max_length=120)


class PortfolioRebalanceRequest(BaseModel):
    user_id: int | None = None
    plan_id: int | None = None


class DashboardResponse(BaseModel):
    user_id: int
    investor_profile: str | None
    open_positions: list[dict[str, object]]
    latest_signals: list[dict[str, object]]
    latest_orders: list[dict[str, object]]
    latest_audit_events: list[dict[str, object]]
    risk_decisions: list[dict[str, object]]
    latest_news: list[dict[str, object]]
    latest_backtests: list[dict[str, object]]
    circuit_breaker: dict[str, object] | None
    kill_switches: list[dict[str, object]]
    alert_events: list[dict[str, object]]
    strategy_validation: dict[str, object] | None = None
    alert_summary: dict[str, object] | None = None
    market_coverage: dict[str, object] | None = None
    data_quality_gate: dict[str, object] | None = None
    phase_kickoff_date: str | None = None
    historical_analysis_summary: dict[str, object] | None = None
    current_simulation_summary: dict[str, object] | None = None
    current_simulation_daily: list[dict[str, object]] | None = None
    thesis_executive_summary: dict[str, object] | None = None
    thesis_open_operations: list[dict[str, object]] | None = None
    disclaimer: str


class ThesisCaseStudyRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=40)
    horizon_bars: int = Field(default=8, ge=3, le=30)


class ThesisGamePlayerDecisionRequest(BaseModel):
    thesis_id: str = Field(min_length=6, max_length=120)
    follow: bool
    option_id: str = Field(pattern="^(A|B|C)$")
    allocation_pct: float = Field(ge=0, le=35)


class ThesisGamePlayerRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    initial_capital: float = Field(gt=0)
    strategy_profile: str = Field(
        default="custom",
        pattern="^(auto_conservative|auto_balanced|auto_aggressive|custom)$",
    )
    decisions: list[ThesisGamePlayerDecisionRequest] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )


class ThesisGameSimulationRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=80)
    horizon_bars: int = Field(default=8, ge=3, le=30)
    thesis_count: int = Field(default=10, ge=5, le=20)
    players: list[ThesisGamePlayerRequest] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )


class ThesisGamePlaybookRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=80)
    horizon_bars: int = Field(default=8, ge=3, le=30)
    thesis_count: int = Field(default=5, ge=3, le=10)
    player_initial_capital: float = Field(default=100000.0, gt=0, le=10000000)


class ThesisSkillLearningRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=4000)
    horizon_bars: int = Field(default=12, ge=3, le=60)
    max_candidates: int = Field(default=1500, ge=50, le=20000)


class ThesisCurrentMonitorRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=4000)
    horizon_bars: int = Field(default=8, ge=3, le=60)
    thesis_count: int = Field(default=8, ge=1, le=30)
    recent_bars_window: int = Field(default=7, ge=2, le=40)


class B3MarketSyncRequest(BaseModel):
    user_id: int
    year: int = Field(default=2025, ge=2000, le=2100)
    instruments: list[str] = Field(
        default_factory=lambda: [
            "PETR4",
            "VALE3",
            "ITUB4",
            "BBDC4",
            "BBAS3",
            "ABEV3",
            "WEGE3",
            "B3SA3",
            "RENT3",
            "SUZB3",
            "JBSS3",
            "PRIO3",
            "RADL3",
            "GGBR4",
            "VBBR3",
            "LREN3",
            "HAPV3",
            "BPAC11",
            "RAIL3",
            "CMIG4",
        ],
        min_length=1,
        max_length=40,
    )
    max_days_per_instrument: int = Field(default=120, ge=1, le=1000)


class B3MarketSyncRangeRequest(BaseModel):
    user_id: int
    start_year: int = Field(default=2023, ge=2000, le=2100)
    end_year: int = Field(default=2025, ge=2000, le=2100)
    instruments: list[str] = Field(
        default_factory=lambda: [
            "PETR4",
            "VALE3",
            "ITUB4",
            "BBDC4",
            "BBAS3",
            "ABEV3",
            "WEGE3",
            "B3SA3",
            "RENT3",
            "SUZB3",
            "JBSS3",
            "PRIO3",
            "RADL3",
            "GGBR4",
            "VBBR3",
            "LREN3",
            "HAPV3",
            "BPAC11",
            "RAIL3",
            "CMIG4",
        ],
        min_length=1,
        max_length=40,
    )
    max_days_per_instrument_per_year: int = Field(default=180, ge=1, le=1000)


class B3MarketSyncUniverseRangeRequest(BaseModel):
    user_id: int
    start_year: int = Field(default=2020, ge=2000, le=2100)
    end_year: int = Field(default=2025, ge=2000, le=2100)
    max_days_per_instrument_per_year: int = Field(default=250, ge=1, le=1000)
    max_instruments: int | None = Field(default=1500, ge=1, le=4000)
    allowed_bdi_codes: list[str] = Field(
        default_factory=lambda: ["02"],
        min_length=1,
        max_length=10,
    )
    allowed_market_types: list[str] = Field(
        default_factory=lambda: ["010"],
        min_length=1,
        max_length=10,
    )


class IntradayFetchRequest(BaseModel):
    user_id: int
    provider_name: str = Field(default="finnhub", min_length=2, max_length=64)
    instruments: list[str] = Field(min_length=1, max_length=100)
    symbol_overrides: dict[str, str] | None = None
    auto_recompute_indicators: bool = True

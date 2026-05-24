from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.services.asset_classes import DEFAULT_MULTI_ASSET_UNIVERSE


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


class WhatsAppNotificationCategories(BaseModel):
    thesis_new: bool = True
    thesis_update: bool = True
    stock_alert: bool = True
    daily_digest: bool = True


class WhatsAppNotificationThresholds(BaseModel):
    thesis_confidence_pct: float = Field(default=55.0, ge=0, le=100)
    thesis_expected_pct: float = Field(default=0.0, ge=-100, le=100)
    thesis_progress_delta_pct: float = Field(default=20.0, ge=1, le=150)
    stock_price_move_pct: float = Field(default=3.0, ge=0.1, le=100)
    news_magnitude: float = Field(default=0.75, ge=0, le=1)
    signal_confidence: float = Field(default=0.6, ge=0, le=1)


class WhatsAppNotificationSettingsRequest(BaseModel):
    user_id: int
    phone_number: str = Field(min_length=10, max_length=24, pattern=r"^\+?[0-9 ()-]{10,24}$")
    display_name: str | None = Field(default=None, max_length=120)
    opt_in: bool = True
    categories: WhatsAppNotificationCategories = Field(
        default_factory=WhatsAppNotificationCategories
    )
    thresholds: WhatsAppNotificationThresholds = Field(
        default_factory=WhatsAppNotificationThresholds
    )


class WhatsAppNotificationTestRequest(BaseModel):
    user_id: int


class PortfolioAllocateRequest(BaseModel):
    user_id: int | None = None
    capital_brl: float = Field(ge=1000, le=10000000)
    risk_profile: str = Field(pattern="^(conservador|moderado|arrojado)$")
    universe: str = Field(default="multiasset", pattern="^(ibov|smll|multiasset|custom)$")
    custom_instruments: list[str] | None = Field(default=None, min_length=1, max_length=120)


class PortfolioRebalanceRequest(BaseModel):
    user_id: int | None = None
    plan_id: int | None = None


class AssistantDecisionOptionRequest(BaseModel):
    option_id: str = Field(min_length=1, max_length=12)
    label: str = Field(min_length=2, max_length=160)


class AssistantDecisionCreateRequest(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    context: str = Field(default="", max_length=1000)
    question: str = Field(min_length=4, max_length=400)
    options: list[AssistantDecisionOptionRequest] = Field(min_length=1, max_length=5)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class AssistantDecisionAnswerRequest(BaseModel):
    option_id: str | None = Field(default=None, min_length=1, max_length=12)
    free_text: str | None = Field(default=None, max_length=1000)


class RealEstateCandidateBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    source_url: str = Field(default="", max_length=500)
    origin: str = Field(default="Venda direta vendedor", max_length=60)
    strategy: str = Field(default="House flipping", max_length=60)
    city: str = Field(default="", max_length=120)
    neighborhood: str = Field(default="", max_length=120)
    property_type: str = Field(default="", max_length=80)
    private_area_m2: float = Field(default=0.0, ge=0)
    bedrooms: int = Field(default=0, ge=0, le=20)
    parking_spaces: int = Field(default=0, ge=0, le=20)
    asking_price: float = Field(default=0.0, ge=0)
    appraisal_value: float = Field(default=0.0, ge=0)
    market_value_estimate: float = Field(default=0.0, ge=0)
    estimated_sale_conservative: float = Field(default=0.0, ge=0)
    estimated_sale_base: float = Field(default=0.0, ge=0)
    estimated_sale_optimistic: float = Field(default=0.0, ge=0)
    estimated_rent_conservative: float = Field(default=0.0, ge=0)
    accepts_financing: bool = False
    financing_validated: bool = False
    occupancy_status: str = Field(
        default="desconhecido",
        pattern="^(desconhecido|desocupado|ocupado)$",
    )
    has_registration: bool = False
    has_edital: bool = False
    condo_debt_known: bool = False
    iptu_debt_known: bool = False
    renovation_type: str = Field(default="desconhecida", max_length=40)
    renovation_budget: float = Field(default=0.0, ge=0)
    carrying_months: int = Field(default=6, ge=0, le=60)
    monthly_carrying_cost: float = Field(default=0.0, ge=0)
    acquisition_costs: float = Field(default=0.0, ge=0)
    selling_commission_pct: float = Field(default=6.0, ge=0, le=20)
    cash_needed: float = Field(default=0.0, ge=0)
    sale_comparables_count: int = Field(default=0, ge=0, le=50)
    rent_comparables_count: int = Field(default=0, ge=0, le=50)
    payment_terms: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    first_operation: bool = True
    plan_a: str = Field(default="", max_length=1000)
    plan_b: str = Field(default="", max_length=1000)
    plan_c: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=2000)


class RealEstateCandidateCreateRequest(RealEstateCandidateBase):
    pass


class RealEstateCandidateUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    origin: str | None = Field(default=None, max_length=60)
    strategy: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=120)
    property_type: str | None = Field(default=None, max_length=80)
    private_area_m2: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    parking_spaces: int | None = Field(default=None, ge=0, le=20)
    asking_price: float | None = Field(default=None, ge=0)
    appraisal_value: float | None = Field(default=None, ge=0)
    market_value_estimate: float | None = Field(default=None, ge=0)
    estimated_sale_conservative: float | None = Field(default=None, ge=0)
    estimated_sale_base: float | None = Field(default=None, ge=0)
    estimated_sale_optimistic: float | None = Field(default=None, ge=0)
    estimated_rent_conservative: float | None = Field(default=None, ge=0)
    accepts_financing: bool | None = None
    financing_validated: bool | None = None
    occupancy_status: str | None = Field(
        default=None,
        pattern="^(desconhecido|desocupado|ocupado)$",
    )
    has_registration: bool | None = None
    has_edital: bool | None = None
    condo_debt_known: bool | None = None
    iptu_debt_known: bool | None = None
    renovation_type: str | None = Field(default=None, max_length=40)
    renovation_budget: float | None = Field(default=None, ge=0)
    carrying_months: int | None = Field(default=None, ge=0, le=60)
    monthly_carrying_cost: float | None = Field(default=None, ge=0)
    acquisition_costs: float | None = Field(default=None, ge=0)
    selling_commission_pct: float | None = Field(default=None, ge=0, le=20)
    cash_needed: float | None = Field(default=None, ge=0)
    sale_comparables_count: int | None = Field(default=None, ge=0, le=50)
    rent_comparables_count: int | None = Field(default=None, ge=0, le=50)
    payment_terms: list[dict[str, Any]] | None = Field(default=None, max_length=12)
    first_operation: bool | None = None
    plan_a: str | None = Field(default=None, max_length=1000)
    plan_b: str | None = Field(default=None, max_length=1000)
    plan_c: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class RealEstateCandidateDiscardRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=1000)


class RealEstateVisitEvidenceRequest(BaseModel):
    section: str = Field(min_length=2, max_length=80)
    evidence: str = Field(min_length=2, max_length=1200)


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
    thesis_history_overview: dict[str, object] | None = None
    thesis_executive_summary: dict[str, object] | None = None
    thesis_open_operations: list[dict[str, object]] | None = None
    front_overview: dict[str, object] | None = None
    ops_health: dict[str, object] | None = None
    disclaimer: str


class ThesisCaseStudyRequest(BaseModel):
    user_id: int
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=40)
    horizon_bars: int = Field(default=8, ge=3, le=30)


class ThesisAiAnalysisRequest(BaseModel):
    user_id: int
    instrument: str = Field(min_length=1, max_length=32)
    question: str | None = Field(default=None, max_length=400)
    horizon_days: int = Field(default=20, ge=1, le=365)


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
        default_factory=lambda: [*DEFAULT_MULTI_ASSET_UNIVERSE, "BPAC11", "BBAS3"],
        min_length=1,
        max_length=40,
    )
    max_days_per_instrument: int = Field(default=120, ge=1, le=1000)


class B3MarketSyncRangeRequest(BaseModel):
    user_id: int
    start_year: int = Field(default=2023, ge=2000, le=2100)
    end_year: int = Field(default=2025, ge=2000, le=2100)
    instruments: list[str] = Field(
        default_factory=lambda: [*DEFAULT_MULTI_ASSET_UNIVERSE, "BPAC11", "BBAS3"],
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
        default_factory=lambda: ["02", "12", "14", "34"],
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


class CryptoHistoryBackfillRequest(BaseModel):
    user_id: int
    provider_name: str = Field(default="binance", min_length=2, max_length=64)
    instruments: list[str] = Field(min_length=1, max_length=100)
    interval: str = Field(
        default="5m",
        pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$",
    )
    lookback_hours: int = Field(default=168, ge=1, le=24 * 365)
    max_candles_per_instrument: int = Field(default=1500, ge=50, le=5000)
    symbol_overrides: dict[str, str] | None = None
    auto_recompute_indicators: bool = True


class MicrotradesAutopilotRunRequest(BaseModel):
    user_id: int | None = None
    instruments: list[str] | None = Field(default=None, min_length=1, max_length=100)
    provider_name: str = Field(default="finnhub", min_length=2, max_length=64)
    history_provider_name: str = Field(default="binance", min_length=2, max_length=64)
    interval: str = Field(
        default="5m",
        pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d)$",
    )
    lookback_hours: int = Field(default=168, ge=1, le=24 * 365)
    max_candles_per_instrument: int = Field(default=1200, ge=50, le=5000)
    horizon_bars: int = Field(default=8, ge=3, le=60)
    thesis_count: int = Field(default=8, ge=1, le=30)
    recent_bars_window: int = Field(default=7, ge=2, le=40)
    auto_recompute_indicators: bool = True
    publish_decisions: bool = True
    decision_cooldown_minutes: int = Field(default=45, ge=5, le=24 * 12)

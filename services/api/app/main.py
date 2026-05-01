from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine, get_db, run_startup_migrations
from app.models import (
    AlertEvent,
    AuditEvent,
    BacktestRun,
    CircuitBreakerState,
    KillSwitchState,
    MarketTick,
    NewsArticle,
    PaperOrder,
    PortfolioPosition,
    RiskDecision,
    Signal,
    SuitabilityProfile,
    User,
)
from app.schemas import (
    AlertRuleRequest,
    B3MarketSyncRangeRequest,
    B3MarketSyncRequest,
    B3MarketSyncUniverseRangeRequest,
    BacktestRunRequest,
    CreatePaperOrderRequest,
    DashboardResponse,
    ExternalFundamentalsSyncRequest,
    ExternalNewsSyncRequest,
    FundamentalIngestRequest,
    GenerateSignalRequest,
    IntradayFetchRequest,
    KillSwitchUpdateRequest,
    LoginRequest,
    MarketProviderStatusRequest,
    MarketTickIngestRequest,
    MarketTickLiveIngestRequest,
    MFASetupRequest,
    MFAVerifyRequest,
    NewsIngestRequest,
    PortfolioAllocateRequest,
    PortfolioRebalanceRequest,
    RecomputeIndicatorsRequest,
    RecomputePortfolioIndicatorsRequest,
    SignupRequest,
    SuitabilityRequest,
    ThesisCaseStudyRequest,
    ThesisCurrentMonitorRequest,
    ThesisGamePlaybookRequest,
    ThesisGameSimulationRequest,
    ThesisSkillLearningRequest,
)
from app.services.alerts import create_alert_rule
from app.services.auth import (
    authenticate_user,
    create_user,
    issue_access_token,
    setup_mfa,
    verify_mfa,
)
from app.services.b3_external import (
    B3SyncPayload,
    B3SyncRangePayload,
    sync_b3_cotahist_portfolio,
    sync_b3_cotahist_portfolio_range,
    sync_b3_cotahist_universe_range,
)
from app.services.backtest import (
    build_validation_snapshot_for_run,
    run_backtest,
    trades_for_run,
)
from app.services.data_quality import build_data_quality_gate_snapshot
from app.services.feed_health import provider_feed_health, universe_coverage_snapshot
from app.services.fundamentals import fundamentals_to_response, ingest_fundamentals
from app.services.fundamentals_external import (
    fundamentals_coverage_snapshot,
    sync_external_fundamentals,
)
from app.services.game_playbook import GamePlaybookPayload, build_game_playbook
from app.services.intraday_provider import IntradayProviderError, fetch_intraday_quotes
from app.services.market import (
    ingest_tick,
    ingest_tick_live,
    list_provider_states,
    market_tick_to_contract,
    recompute_indicators,
    update_provider_status,
)
from app.services.news import (
    aggregate_sentiment_as_of,
    ingest_news,
    latest_news_as_of,
    source_credibility_history_as_of,
)
from app.services.news_external import sync_external_news_period
from app.services.paper_trading import create_paper_order
from app.services.point_in_time import (
    latest_fundamentals_as_of,
    latest_indicator_as_of,
    ticks_as_of,
)
from app.services.portfolio_optimizer import (
    AllocationPlanPayload,
    RebalancePlanPayload,
    allocate_portfolio,
    build_rebalance_plan,
    get_allocation_plan,
    get_latest_allocation_plan,
)
from app.services.reports import build_user_report
from app.services.risk import evaluate_circuit_breaker, set_kill_switch
from app.services.signals import generate_signal
from app.services.suitability import save_suitability
from app.services.thesis_case_study import CaseStudyPayload, run_thesis_case_study
from app.services.thesis_gamification import (
    GameSimulationPayload,
    OptionId,
    PlayerConfigInput,
    PlayerDecisionInput,
    StrategyProfile,
    run_thesis_game_simulation,
)
from app.services.thesis_learning import ThesisLearningPayload, run_thesis_skill_learning_cycle
from app.services.thesis_current_monitor import (
    CurrentThesisMonitorPayload,
    run_current_thesis_monitor,
)
from app.services.utils import DISCLAIMER, access_token_ttl_seconds, decode_access_token
from app.workers import AgentLoop

Base.metadata.create_all(bind=engine)
run_startup_migrations()

app = FastAPI(
    title="AI-Powered Investment Advisor MVP",
    version="0.1.0",
    description=(
        "MVP funcional da Fase 1, focado em simulacao, paper trading e postura anti-recomendacao."
    ),
)

static_dir = Path(__file__).resolve().parent.parent / "static"
data_dir = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parents[3] / "data")))
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
agent_loop = AgentLoop()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecalho Authorization ausente",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer invalido",
        )
    return token


def current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado",
        ) from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario do token nao encontrado",
        )
    return user


def assert_user_scope(target_user_id: int, user: User) -> None:
    if target_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operacao nao permitida para este usuario",
        )


def _is_sqlite_lock_error(exc: OperationalError) -> bool:
    raw = str(getattr(exc, "orig", exc)).lower()
    return "database is locked" in raw


def signal_to_payload(signal: Signal) -> dict[str, object]:
    return {
        "signal_id": signal.id,
        "user_id": signal.user_id,
        "instrument": signal.instrument,
        "reference_time": signal.reference_time,
        "availability_time": signal.availability_time,
        "signal_type": signal.signal_type,
        "confidence": signal.confidence,
        "rationale": signal.rationale,
        "anti_hype_score": signal.anti_hype_score,
        "signal_status": signal.signal_status,
        "expires_at": signal.expires_at,
        "expiry_reason": signal.expiry_reason,
        "xai_payload": signal.xai_payload,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "simulation-only"}


@app.post("/api/auth/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user = create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OperationalError as exc:
        db.rollback()
        if _is_sqlite_lock_error(exc):
            raise HTTPException(
                status_code=503,
                detail="Base ocupada no momento. Tente novamente em alguns segundos.",
            ) from exc
        raise
    return {"user_id": user.id, "tenant_id": user.tenant_id, "email": user.email}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user = authenticate_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OperationalError as exc:
        db.rollback()
        if _is_sqlite_lock_error(exc):
            raise HTTPException(
                status_code=503,
                detail="Base ocupada no momento. Tente novamente em alguns segundos.",
            ) from exc
        raise
    return {
        "user_id": user.id,
        "email": user.email,
        "mfa_enabled": user.mfa_enabled,
        "token_type": "bearer",
        "expires_in": access_token_ttl_seconds(),
        "access_token": issue_access_token(user),
    }


@app.post("/api/auth/mfa/setup")
def mfa_setup(
    payload: MFASetupRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, str]:
    assert_user_scope(payload.user_id, user)
    try:
        uri = setup_mfa(db, payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"provisioning_uri": uri}


@app.post("/api/auth/mfa/verify")
def mfa_verify(payload: MFAVerifyRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        user = verify_mfa(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user_id": user.id, "mfa_enabled": user.mfa_enabled}


@app.post("/api/suitability")
def suitability(
    payload: SuitabilityRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    profile = save_suitability(db, payload)
    return {"user_id": profile.user_id, "investor_profile": profile.investor_profile}


@app.post("/api/market/ticks/ingest")
def market_ingest(
    payload: MarketTickIngestRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        tick = ingest_tick(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return market_tick_to_contract(tick)


@app.post("/api/market/ticks/ingest-live")
def market_ingest_live(
    payload: MarketTickLiveIngestRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return ingest_tick_live(
            db,
            payload,
            auto_recompute_indicators=payload.auto_recompute_indicators,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/market/providers/status")
def market_provider_status(
    payload: MarketProviderStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    state = update_provider_status(db, payload)
    return {
        "provider_name": state.provider_name,
        "role": state.role,
        "status": state.status,
        "consecutive_failures": state.consecutive_failures,
        "failover_threshold": state.failover_threshold,
        "is_active": state.is_active,
        "last_event_time": state.last_event_time,
    }


@app.get("/api/market/providers")
def market_provider_list(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    states = list_provider_states(db)
    return [
        {
            "provider_name": state.provider_name,
            "role": state.role,
            "status": state.status,
            "consecutive_failures": state.consecutive_failures,
            "failover_threshold": state.failover_threshold,
            "is_active": state.is_active,
            "last_event_time": state.last_event_time,
        }
        for state in states
    ]


@app.post("/api/market/external/b3/sync")
def market_external_b3_sync(
    payload: B3MarketSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> B3SyncPayload:
    assert_user_scope(payload.user_id, user)
    try:
        return sync_b3_cotahist_portfolio(
            db,
            user_id=payload.user_id,
            year=payload.year,
            instruments=payload.instruments,
            max_days_per_instrument=payload.max_days_per_instrument,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/market/external/b3/sync-range")
def market_external_b3_sync_range(
    payload: B3MarketSyncRangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> B3SyncRangePayload:
    assert_user_scope(payload.user_id, user)
    try:
        return sync_b3_cotahist_portfolio_range(
            db,
            user_id=payload.user_id,
            start_year=payload.start_year,
            end_year=payload.end_year,
            instruments=payload.instruments,
            max_days_per_instrument_per_year=payload.max_days_per_instrument_per_year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/market/external/b3/sync-universe-range")
def market_external_b3_sync_universe_range(
    payload: B3MarketSyncUniverseRangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> B3SyncRangePayload:
    assert_user_scope(payload.user_id, user)
    try:
        return sync_b3_cotahist_universe_range(
            db,
            user_id=payload.user_id,
            start_year=payload.start_year,
            end_year=payload.end_year,
            max_days_per_instrument_per_year=payload.max_days_per_instrument_per_year,
            max_instruments=payload.max_instruments,
            allowed_bdi_codes=payload.allowed_bdi_codes,
            allowed_market_types=payload.allowed_market_types,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/market/intraday/fetch-live")
def market_intraday_fetch_live(
    payload: IntradayFetchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        quotes = fetch_intraday_quotes(
            payload.provider_name,
            payload.instruments,
            payload.symbol_overrides,
        )
    except IntradayProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    processed: list[dict[str, object]] = []
    failed: list[dict[str, str]] = []
    for quote in quotes:
        try:
            result = ingest_tick_live(
                db,
                MarketTickIngestRequest(
                    instrument=quote["instrument"],
                    provider=f"intraday-{quote['provider_name']}",
                    event_time=quote["event_time"],
                    price=quote["price"],
                    volume=quote["volume"],
                    currency=quote["currency"],
                    source_payload_id=quote["source_payload_id"],
                ),
                auto_recompute_indicators=payload.auto_recompute_indicators,
            )
            processed.append(
                {
                    "instrument": quote["instrument"],
                    "provider_symbol": quote["provider_symbol"],
                    "market_tick": result["market_tick"],
                    "algorithm_update": result["algorithm_update"],
                }
            )
        except ValueError as exc:
            failed.append(
                {
                    "instrument": quote["instrument"],
                    "provider_symbol": quote["provider_symbol"],
                    "error": str(exc),
                }
            )

    return {
        "provider_name": payload.provider_name,
        "requested_instruments": payload.instruments,
        "processed_count": len(processed),
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
    }


@app.get("/api/market/feed/health")
def market_feed_health(
    stale_threshold_seconds: int = Query(default=1800, ge=30, le=86400),
    latency_threshold_seconds: int = Query(default=120, ge=1, le=3600),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    providers = provider_feed_health(
        db,
        stale_threshold_seconds=stale_threshold_seconds,
        latency_threshold_seconds=latency_threshold_seconds,
    )
    critical_count = sum(1 for row in providers if row["health_status"] == "critical")
    warning_count = sum(1 for row in providers if row["health_status"] == "warning")
    no_data_count = sum(1 for row in providers if row["health_status"] == "no_data")
    return {
        "providers": providers,
        "summary": {
            "provider_count": len(providers),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "no_data_count": no_data_count,
        },
        "thresholds": {
            "stale_threshold_seconds": stale_threshold_seconds,
            "latency_threshold_seconds": latency_threshold_seconds,
        },
    }


@app.get("/api/market/universe/coverage")
def market_universe_coverage(
    max_rows: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return cast(dict[str, object], universe_coverage_snapshot(db, max_rows=max_rows))


@app.get("/api/data-quality/gate")
def data_quality_gate(
    instruments: str | None = Query(
        default=None,
        description="Lista CSV de instrumentos alvo (ex.: PETR4,VALE3).",
    ),
    market_max_lag_seconds: int = Query(default=1800, ge=30, le=86400),
    market_min_fresh_coverage_pct: float = Query(default=95.0, ge=0.0, le=100.0),
    fundamentals_min_coverage_pct: float = Query(default=90.0, ge=0.0, le=100.0),
    fundamentals_max_staleness_days: int = Query(default=1, ge=0, le=3650),
    fundamentals_min_fresh_coverage_pct: float = Query(default=90.0, ge=0.0, le=100.0),
    news_lookback_days: int = Query(default=7, ge=1, le=3650),
    news_min_coverage_pct: float = Query(default=60.0, ge=0.0, le=100.0),
    max_critical_providers: int = Query(default=0, ge=0, le=100),
    max_no_data_providers: int = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    instrument_list: list[str] | None = None
    if instruments is not None:
        instrument_list = [
            item.strip().upper()
            for item in instruments.split(",")
            if item.strip()
        ]
    try:
        payload = build_data_quality_gate_snapshot(
            db,
            instruments=instrument_list,
            market_max_lag_seconds=market_max_lag_seconds,
            market_min_fresh_coverage_pct=market_min_fresh_coverage_pct,
            fundamentals_min_coverage_pct=fundamentals_min_coverage_pct,
            fundamentals_max_staleness_days=fundamentals_max_staleness_days,
            fundamentals_min_fresh_coverage_pct=fundamentals_min_fresh_coverage_pct,
            news_lookback_days=news_lookback_days,
            news_min_coverage_pct=news_min_coverage_pct,
            max_critical_providers=max_critical_providers,
            max_no_data_providers=max_no_data_providers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return cast(dict[str, object], payload)


@app.post("/api/news/ingest")
def news_ingest(payload: NewsIngestRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    article = ingest_news(db, payload)
    sentiment = aggregate_sentiment_as_of(db, article.instrument, datetime.now(UTC))
    return {
        "news_id": article.id,
        "instrument": article.instrument,
        "anti_hype_score": article.anti_hype_score,
        "credibility_score": article.credibility_score,
        "sentiment": sentiment,
    }


@app.post("/api/news/external/sync-period")
def news_external_sync_period(
    payload: ExternalNewsSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        return dict(
            sync_external_news_period(
                db,
                user_id=payload.user_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
                instruments=payload.instruments,
                max_articles_per_instrument=payload.max_articles_per_instrument,
                language=payload.language,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/fundamentals/ingest")
def fundamentals_ingest(
    payload: FundamentalIngestRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        snapshot = ingest_fundamentals(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return fundamentals_to_response(snapshot)


@app.post("/api/fundamentals/external/sync")
def fundamentals_external_sync(
    payload: ExternalFundamentalsSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        return dict(
            sync_external_fundamentals(
                db,
                user_id=payload.user_id,
                provider_name=payload.provider_name,
                instruments=payload.instruments,
                only_missing=payload.only_missing,
                max_instruments=payload.max_instruments,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/fundamentals/coverage")
def fundamentals_coverage(
    max_rows: int = Query(default=200, ge=1, le=5000),
    only_missing: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return cast(
        dict[str, object],
        fundamentals_coverage_snapshot(
            db,
            max_rows=max_rows,
            only_missing=only_missing,
        ),
    )


@app.get("/api/fundamentals/{instrument}")
def fundamentals_latest(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    snapshot = latest_fundamentals_as_of(db, instrument.upper(), timestamp)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Nenhum fundamento disponivel")
    return fundamentals_to_response(snapshot)


@app.get("/api/news/{instrument}")
def news_list(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    articles = latest_news_as_of(db, instrument.upper(), timestamp)
    return [
        {
            "news_id": article.id,
            "headline": article.headline,
            "source_name": article.source_name,
            "source_type": article.source_type,
            "credibility_score": article.credibility_score,
            "anti_hype_score": article.anti_hype_score,
            "published_at": article.published_at,
        }
        for article in articles
    ]


@app.get("/api/news/sentiment/{instrument}")
def news_sentiment(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    payload = aggregate_sentiment_as_of(db, instrument.upper(), timestamp)
    return {
        "instrument": payload["instrument"],
        "sector": payload["sector"],
        "article_count": payload["article_count"],
        "weighted_sentiment": payload["weighted_sentiment"],
        "average_magnitude": payload["average_magnitude"],
        "average_confidence": payload["average_confidence"],
        "sentiment_bias": payload["sentiment_bias"],
    }


@app.get("/api/news/sources/{instrument}")
def news_sources(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    return [
        {
            "source_name": row["source_name"],
            "source_type": row["source_type"],
            "article_count": row["article_count"],
            "average_credibility": row["average_credibility"],
            "average_anti_hype": row["average_anti_hype"],
            "average_magnitude": row["average_magnitude"],
            "weighted_sentiment": row["weighted_sentiment"],
            "latest_published_at": row["latest_published_at"],
            "latest_captured_at": row["latest_captured_at"],
        }
        for row in source_credibility_history_as_of(db, instrument.upper(), timestamp)
    ]


@app.get("/api/market/ticks/{instrument}")
def market_ticks(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    ticks = ticks_as_of(db, instrument.upper(), timestamp)
    return [market_tick_to_contract(tick) for tick in ticks]


@app.post("/api/analysis/indicators/recompute")
def indicators_recompute(
    payload: RecomputeIndicatorsRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        snapshot = recompute_indicators(db, payload.instrument)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "instrument": snapshot.instrument,
        "reference_time": snapshot.reference_time,
        "availability_time": snapshot.availability_time,
        "sma_5": snapshot.sma_5,
        "sma_10": snapshot.sma_10,
        "sma_20": snapshot.sma_20,
        "ema_5": snapshot.ema_5,
        "ema_12": snapshot.ema_12,
        "ema_26": snapshot.ema_26,
        "rsi_14": snapshot.rsi_14,
        "volatility_10": snapshot.volatility_10,
        "momentum_5": snapshot.momentum_5,
        "macd": snapshot.macd,
    }


@app.post("/api/analysis/indicators/recompute-batch")
def indicators_recompute_batch(
    payload: RecomputePortfolioIndicatorsRequest,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for instrument in payload.instruments:
        try:
            snapshot = recompute_indicators(db, instrument)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"{instrument}: {exc}") from exc
        results.append(
            {
                "instrument": snapshot.instrument,
                "reference_time": snapshot.reference_time,
                "availability_time": snapshot.availability_time,
                "sma_5": snapshot.sma_5,
                "sma_10": snapshot.sma_10,
                "sma_20": snapshot.sma_20,
                "ema_5": snapshot.ema_5,
                "ema_12": snapshot.ema_12,
                "ema_26": snapshot.ema_26,
                "rsi_14": snapshot.rsi_14,
                "volatility_10": snapshot.volatility_10,
                "momentum_5": snapshot.momentum_5,
                "macd": snapshot.macd,
            }
        )
    return results


@app.get("/api/analysis/indicators/{instrument}")
def indicators_latest(
    instrument: str,
    as_of: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    timestamp = datetime.fromisoformat(as_of) if as_of else datetime.now(UTC)
    snapshot = latest_indicator_as_of(db, instrument.upper(), timestamp)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Nenhum indicador disponivel")
    return {
        "instrument": snapshot.instrument,
        "reference_time": snapshot.reference_time,
        "availability_time": snapshot.availability_time,
        "sma_5": snapshot.sma_5,
        "sma_10": snapshot.sma_10,
        "sma_20": snapshot.sma_20,
        "ema_5": snapshot.ema_5,
        "ema_12": snapshot.ema_12,
        "ema_26": snapshot.ema_26,
        "rsi_14": snapshot.rsi_14,
        "volatility_10": snapshot.volatility_10,
        "momentum_5": snapshot.momentum_5,
        "macd": snapshot.macd,
    }


@app.post("/api/signals/generate")
def signals_generate(
    payload: GenerateSignalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        signal = generate_signal(db, payload.user_id, payload.instrument)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return signal_to_payload(signal)


@app.get("/api/signals")
def signals_list(
    user_id: int = Query(..., ge=1),
    status_filter: str = Query(default="active", alias="status", pattern="^(active|expired|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    assert_user_scope(user_id, user)
    query = select(Signal).where(Signal.user_id == user_id)
    if status_filter != "all":
        query = query.where(Signal.signal_status == status_filter)
    rows = list(db.scalars(query.order_by(desc(Signal.id)).limit(limit)))
    return [signal_to_payload(row) for row in rows]


@app.post("/api/alerts/rules")
def alert_rule_create(
    payload: AlertRuleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    rule = create_alert_rule(
        db,
        payload.user_id,
        payload.rule_type,
        payload.instrument,
        payload.threshold_value,
    )
    return {
        "alert_rule_id": rule.id,
        "rule_type": rule.rule_type,
        "instrument": rule.instrument,
        "threshold_value": rule.threshold_value,
        "is_active": rule.is_active,
    }


@app.get("/api/alerts/events/{user_id}")
def alert_events(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    assert_user_scope(user_id, user)
    events = list(
        db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == user_id)
            .order_by(desc(AlertEvent.id))
            .limit(20)
        )
    )
    return [
        {
            "alert_event_id": event.id,
            "event_type": event.event_type,
            "instrument": event.instrument,
            "payload": event.payload,
            "created_at": event.created_at,
        }
        for event in events
    ]


@app.get("/api/audit/events")
def audit_events(
    event_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    query = (
        select(AuditEvent)
        .where(or_(AuditEvent.user_id == user.id, AuditEvent.user_id.is_(None)))
        .order_by(desc(AuditEvent.id))
        .limit(50)
    )
    if event_type is not None:
        query = query.where(AuditEvent.event_type == event_type)
    events = list(db.scalars(query))
    return [
        {
            "audit_event_id": event.id,
            "user_id": event.user_id,
            "event_type": event.event_type,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event in events
    ]


@app.post("/api/paper/orders/from-signal/{signal_id}")
def paper_order_from_signal(
    signal_id: int,
    payload: CreatePaperOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        order = create_paper_order(db, payload.user_id, signal_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "order_id": order.id,
        "instrument": order.instrument,
        "quantity": order.quantity,
        "execution_price": order.execution_price,
        "estimated_cost": order.estimated_cost,
        "estimated_tax": order.estimated_tax,
        "risk_status": order.risk_status,
        "risk_notes": order.risk_notes,
    }


@app.post("/api/backtests/run")
def backtest_run(
    payload: BacktestRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        run = run_backtest(db, payload.user_id, payload.instrument, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    validation_snapshot = build_validation_snapshot_for_run(db, run)
    return {
        "run_id": run.id,
        "instrument": run.instrument,
        "trade_count": run.trade_count,
        "accepted_trade_count": run.accepted_trade_count,
        "rejected_trade_count": run.rejected_trade_count,
        "win_rate": run.win_rate,
        "total_return_pct": run.total_return_pct,
        "max_drawdown_pct": run.max_drawdown_pct,
        "summary": run.summary,
        "validation_snapshot": validation_snapshot,
    }


@app.get("/api/backtests/{run_id}")
def backtest_detail(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest nao encontrado")
    assert_user_scope(run.user_id, user)
    trades = trades_for_run(db, run_id)
    validation_snapshot = build_validation_snapshot_for_run(db, run)
    return {
        "run_id": run.id,
        "instrument": run.instrument,
        "trade_count": run.trade_count,
        "accepted_trade_count": run.accepted_trade_count,
        "rejected_trade_count": run.rejected_trade_count,
        "win_rate": run.win_rate,
        "total_return_pct": run.total_return_pct,
        "max_drawdown_pct": run.max_drawdown_pct,
        "summary": run.summary,
        "validation_snapshot": validation_snapshot,
        "trades": [
            {
                "signal_time": trade.signal_time,
                "signal_type": trade.signal_type,
                "confidence": trade.confidence,
                "anti_hype_score": trade.anti_hype_score,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl_pct": trade.pnl_pct,
                "risk_decision": trade.risk_decision,
                "rationale": trade.rationale,
            }
            for trade in trades
        ],
    }


@app.get("/api/risk/circuit-breaker/{instrument}")
def circuit_breaker_status(instrument: str, db: Session = Depends(get_db)) -> dict[str, object]:
    state = evaluate_circuit_breaker(db, instrument.upper(), datetime.now(UTC))
    if state is None:
        return {"instrument": instrument.upper(), "status": "clear", "reason": None}
    return {
        "instrument": state.instrument,
        "status": state.status,
        "reason": state.reason,
        "triggered_at": state.triggered_at,
        "released_at": state.released_at,
    }


@app.post("/api/risk/kill-switch")
def kill_switch_update(
    payload: KillSwitchUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    if payload.scope_type != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Escopos global e instrument sao restritos a operacao administrativa",
        )
    try:
        scope_user_id = int(payload.scope_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="scope_id deve ser numerico para escopo user",
        ) from exc
    assert_user_scope(scope_user_id, user)
    state = set_kill_switch(
        db,
        payload.scope_type,
        payload.scope_id,
        payload.status,
        payload.reason,
        datetime.now(UTC),
    )
    return {
        "kill_switch_id": state.id,
        "scope_type": state.scope_type,
        "scope_id": state.scope_id,
        "status": state.status,
        "reason": state.reason,
        "triggered_at": state.triggered_at,
        "released_at": state.released_at,
    }


@app.get("/api/risk/kill-switch")
def kill_switch_list(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    states = list(
        db.scalars(
            select(KillSwitchState)
            .where(
                or_(
                    KillSwitchState.scope_type == "global",
                    and_(
                        KillSwitchState.scope_type == "user",
                        KillSwitchState.scope_id == str(user.id),
                    ),
                )
            )
            .order_by(desc(KillSwitchState.id))
            .limit(20)
        )
    )
    return [
        {
            "kill_switch_id": state.id,
            "scope_type": state.scope_type,
            "scope_id": state.scope_id,
            "status": state.status,
            "reason": state.reason,
            "triggered_at": state.triggered_at,
            "released_at": state.released_at,
        }
        for state in states
    ]


@app.get("/api/reports/summary/{user_id}")
def report_summary(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(user_id, user)
    return build_user_report(db, user_id)


@app.get("/api/reports/executive")
def report_executive() -> dict[str, object]:
    report_path = data_dir / "executive_report_latest.json"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Reporte executivo ainda nao foi gerado.",
        )
    try:
        payload = report_path.read_text(encoding="utf-8")
        report = cast(dict[str, object], json.loads(payload))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Falha ao carregar reporte executivo.",
        ) from exc
    return report


@app.get("/api/reports/executive/snapshot.svg", include_in_schema=False)
def report_executive_snapshot() -> FileResponse:
    snapshot_path = data_dir / "executive_report_snapshot.svg"
    if not snapshot_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Snapshot executivo ainda nao foi gerado.",
        )
    return FileResponse(snapshot_path, media_type="image/svg+xml")


@app.get("/executive", include_in_schema=False)
def executive_page() -> HTMLResponse:
    snapshot_path = data_dir / "executive_report_snapshot.svg"
    report_path = data_dir / "executive_report_latest.json"
    monitor_path = data_dir / "current_thesis_monitor_latest.json"
    if not report_path.exists():
        return HTMLResponse(
            content=(
                "<html><body style='font-family:Segoe UI,Arial;padding:24px'>"
                "<h2>Reporte executivo ainda nao foi gerado.</h2>"
                "<p>Rode o gerador e tente novamente.</p>"
                "</body></html>"
            ),
            status_code=404,
        )
    report = cast(dict[str, object], json.loads(report_path.read_text(encoding="utf-8")))
    kpis = cast(dict[str, object], report.get("kpis", {}))
    evolution = cast(dict[str, object], report.get("evolution", {}))
    examples = report.get("examples", [])

    monitor_payload: dict[str, object] | None = None
    if monitor_path.exists():
        try:
            monitor_payload = cast(
                dict[str, object],
                json.loads(monitor_path.read_text(encoding="utf-8")),
            )
        except (OSError, ValueError):
            monitor_payload = None

    def fmt_pct(value: object) -> str:
        if isinstance(value, (int, float)):
            return f"{float(value):.2f}%"
        return "-"

    def fmt_money(value: object) -> str:
        if not isinstance(value, (int, float)):
            return "-"
        text = f"{float(value):,.2f}"
        return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")

    def fmt_raw(value: object) -> str:
        if value is None:
            return "-"
        return str(value)

    def safe_cell(value: object) -> str:
        return fmt_raw(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    examples_rows = ""
    if isinstance(examples, list):
        for item in examples:
            if not isinstance(item, dict):
                continue
            examples_rows += (
                "<tr>"
                f"<td>{safe_cell(item.get('instrument'))}</td>"
                f"<td>{safe_cell(item.get('reason'))}</td>"
                f"<td>{safe_cell(item.get('strategy'))}</td>"
                f"<td>{safe_cell(item.get('entry_date'))} @ {safe_cell(fmt_money(item.get('entry_price')))}</td>"
                f"<td>{safe_cell(fmt_money(item.get('target_price')))}</td>"
                f"<td>{safe_cell(fmt_money(item.get('high_guard')))} / {safe_cell(fmt_money(item.get('low_guard')))}</td>"
                f"<td>{safe_cell(item.get('exit_date'))} @ {safe_cell(fmt_money(item.get('exit_price')))}</td>"
                f"<td>{safe_cell(fmt_pct(item.get('realized_financial_pct')))}</td>"
                "</tr>"
            )
    if not examples_rows:
        examples_rows = "<tr><td colspan='8'>Sem exemplos no reporte.</td></tr>"

    monitor_rows = ""
    monitor_summary_html = "<p style='color:#94a3b8;margin:6px 0 0'>Sem monitor diario gerado.</p>"
    if isinstance(monitor_payload, dict):
        summary = monitor_payload.get("summary", {})
        theses = monitor_payload.get("theses", [])
        if isinstance(summary, dict):
            monitor_summary_html = (
                "<p style='margin:6px 0 0;color:#cbd5e1'>"
                f"Hits de alvo: <strong>{safe_cell(summary.get('target_hits'))}</strong> | "
                f"Alertas de stop: <strong>{safe_cell(summary.get('stop_alerts'))}</strong> | "
                f"Retorno medio atual: <strong>{safe_cell(fmt_pct(summary.get('avg_unrealized_financial_pct')))}</strong>"
                "</p>"
            )
        if isinstance(theses, list):
            for item in theses[:8]:
                if not isinstance(item, dict):
                    continue
                monitor_rows += (
                    "<tr>"
                    f"<td>{safe_cell(item.get('instrument'))}</td>"
                    f"<td>{safe_cell(item.get('reason_category'))}</td>"
                    f"<td>{safe_cell(fmt_money(item.get('entry_price')))}</td>"
                    f"<td>{safe_cell(fmt_money(item.get('target_price')))}</td>"
                    f"<td>{safe_cell(fmt_money(item.get('stop_price')))}</td>"
                    f"<td>{safe_cell(fmt_money(item.get('latest_price')))}</td>"
                    f"<td>{safe_cell(item.get('monitor_status'))}</td>"
                    f"<td>{safe_cell(item.get('suggested_action'))}</td>"
                    "</tr>"
                )
    if not monitor_rows:
        monitor_rows = "<tr><td colspan='8'>Sem teses atuais monitoradas.</td></tr>"

    snapshot_block = ""
    if snapshot_path.exists():
        snapshot_block = (
            "<div style='margin-top:18px'>"
            "<img src='/api/reports/executive/snapshot.svg' alt='snapshot executivo' "
            "style='width:100%;max-width:1400px;height:auto;display:block;border:1px solid #1f2937;border-radius:8px'/>"
            "</div>"
        )

    last_day = cast(dict[str, object], evolution.get("last_day", {}))
    last_7_days = cast(dict[str, object], evolution.get("last_7_days", {}))

    html = (
        "<html><head><meta charset='utf-8'><title>Reporte Executivo</title>"
        "<style>"
        "body{margin:0;background:#0b1220;color:#e5e7eb;font-family:Segoe UI,Arial}"
        ".wrap{padding:16px 20px;max-width:1440px;margin:0 auto}"
        ".top{padding:14px 0;border-bottom:1px solid #1f2937;margin-bottom:16px}"
        ".chips{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}"
        ".chip{background:#111827;border:1px solid #1f2937;border-radius:8px;padding:10px 12px;min-width:200px}"
        ".card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:14px;margin-top:14px}"
        "table{width:100%;border-collapse:collapse;margin-top:10px}"
        "th,td{border:1px solid #1f2937;padding:8px 10px;text-align:left;font-size:13px;vertical-align:top}"
        "th{background:#0f172a;color:#cbd5e1}"
        "a{color:#93c5fd}"
        "</style></head><body><div class='wrap'>"
        "<div class='top'>"
        "<strong style='font-size:20px'>Reporte Executivo</strong> | "
        "<a href='/api/reports/executive'>JSON</a> | "
        "<a href='/api/reports/executive/snapshot.svg'>SVG</a> | "
        "<a href='/api/theses/current-monitor/latest'>Monitor Diario JSON</a>"
        f"<div style='color:#94a3b8;margin-top:8px'>Atualizado em {safe_cell(report.get('generated_at'))}</div>"
        "</div>"
        "<div class='chips'>"
        f"<div class='chip'><div>Taxa de sucesso</div><strong>{safe_cell(fmt_pct(kpis.get('success_rate_pct')))}</strong></div>"
        f"<div class='chip'><div>Taxa de descoberta</div><strong>{safe_cell(fmt_pct(kpis.get('discovery_rate_pct')))}</strong></div>"
        f"<div class='chip'><div>Confianca media</div><strong>{safe_cell(fmt_pct(kpis.get('avg_confidence_pct')))}</strong></div>"
        f"<div class='chip'><div>Esperado vs Real</div><strong>{safe_cell(fmt_pct(kpis.get('avg_expected_financial_pct')))} / {safe_cell(fmt_pct(kpis.get('avg_realized_financial_pct')))}</strong></div>"
        f"<div class='chip'><div>Ultimo dia</div><strong>{safe_cell(fmt_pct(last_day.get('success_rate_pct')))}</strong></div>"
        f"<div class='chip'><div>Ultimos 7 dias</div><strong>{safe_cell(fmt_pct(last_7_days.get('success_rate_pct')))}</strong></div>"
        "</div>"
        "<div class='card'><h3 style='margin:0'>Exemplos de Teses Avaliadas</h3>"
        "<table><thead><tr>"
        "<th>Ativo</th><th>Motivo</th><th>Operacao</th><th>Entrada</th><th>Alvo</th><th>Travas (alta/baixa)</th><th>Saida efetiva</th><th>Resultado</th>"
        "</tr></thead><tbody>"
        f"{examples_rows}"
        "</tbody></table></div>"
        "<div class='card'><h3 style='margin:0'>Monitor Diario de Teses Atuais</h3>"
        f"{monitor_summary_html}"
        "<table><thead><tr>"
        "<th>Ativo</th><th>Origem da tese</th><th>Entrada</th><th>Alvo</th><th>Stop</th><th>Preco atual</th><th>Status</th><th>Acao sugerida</th>"
        "</tr></thead><tbody>"
        f"{monitor_rows}"
        "</tbody></table></div>"
        f"{snapshot_block}"
        "</div></body></html>"
    )
    return HTMLResponse(content=html)


@app.post("/api/portfolio/allocate")
def portfolio_allocate(
    payload: PortfolioAllocateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AllocationPlanPayload:
    target_user_id = payload.user_id if payload.user_id is not None else user.id
    assert_user_scope(target_user_id, user)
    universe_override: list[str] | None = None
    if payload.universe == "custom":
        if payload.custom_instruments is None or len(payload.custom_instruments) == 0:
            raise HTTPException(
                status_code=400,
                detail="custom_instruments obrigatorio quando universe=custom",
            )
        universe_override = payload.custom_instruments
    elif payload.custom_instruments:
        universe_override = payload.custom_instruments
    try:
        return allocate_portfolio(
            db,
            user_id=target_user_id,
            capital_brl=payload.capital_brl,
            risk_profile=payload.risk_profile,
            instruments=universe_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/portfolio/allocation/{plan_id:int}")
def portfolio_allocation_by_id(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AllocationPlanPayload:
    try:
        return get_allocation_plan(db, user_id=user.id, plan_id=plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/portfolio/allocation/latest")
def portfolio_allocation_latest(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AllocationPlanPayload:
    try:
        return get_latest_allocation_plan(db, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/portfolio/rebalance")
def portfolio_rebalance(
    payload: PortfolioRebalanceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> RebalancePlanPayload:
    target_user_id = payload.user_id if payload.user_id is not None else user.id
    assert_user_scope(target_user_id, user)
    try:
        return build_rebalance_plan(
            db,
            user_id=target_user_id,
            plan_id=payload.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/theses/case-study")
def thesis_case_study(
    payload: ThesisCaseStudyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CaseStudyPayload:
    assert_user_scope(payload.user_id, user)
    try:
        return run_thesis_case_study(
            db,
            payload.user_id,
            payload.instruments,
            payload.horizon_bars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/theses/skill/learn")
def thesis_skill_learn(
    payload: ThesisSkillLearningRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ThesisLearningPayload:
    assert_user_scope(payload.user_id, user)
    try:
        return run_thesis_skill_learning_cycle(
            db,
            user_id=payload.user_id,
            instruments=payload.instruments,
            horizon_bars=payload.horizon_bars,
            max_candidates=payload.max_candidates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/theses/current-monitor")
def thesis_current_monitor(
    payload: ThesisCurrentMonitorRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CurrentThesisMonitorPayload:
    assert_user_scope(payload.user_id, user)
    try:
        monitor_payload = run_current_thesis_monitor(
            db,
            user_id=payload.user_id,
            instruments=payload.instruments,
            horizon_bars=payload.horizon_bars,
            thesis_count=payload.thesis_count,
            recent_bars_window=payload.recent_bars_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output_path = data_dir / "current_thesis_monitor_latest.json"
    output_path.write_text(
        json.dumps(monitor_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return monitor_payload


@app.get("/api/theses/current-monitor/latest")
def thesis_current_monitor_latest(
    user: User = Depends(current_user),
) -> dict[str, object]:
    _ = user.id
    output_path = data_dir / "current_thesis_monitor_latest.json"
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Monitor diario de teses atuais ainda nao foi gerado.",
        )
    try:
        payload = cast(
            dict[str, object],
            json.loads(output_path.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Falha ao carregar monitor diario de teses atuais.",
        ) from exc
    return payload


@app.post("/api/theses/game-simulation")
def thesis_game_simulation(
    payload: ThesisGameSimulationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> GameSimulationPayload:
    assert_user_scope(payload.user_id, user)
    players_payload: list[PlayerConfigInput] | None = None
    if payload.players is not None:
        players_payload = []
        for player in payload.players:
            decisions_payload: list[PlayerDecisionInput] | None = None
            if player.decisions is not None:
                decisions_payload = [
                    {
                        "thesis_id": decision.thesis_id,
                        "follow": decision.follow,
                        "option_id": cast(OptionId, decision.option_id),
                        "allocation_pct": decision.allocation_pct,
                    }
                    for decision in player.decisions
                ]
            players_payload.append(
                {
                    "name": player.name,
                    "initial_capital": player.initial_capital,
                    "strategy_profile": cast(StrategyProfile, player.strategy_profile),
                    "decisions": decisions_payload,
                }
            )
    try:
        return run_thesis_game_simulation(
            db,
            user_id=payload.user_id,
            instruments=payload.instruments,
            horizon_bars=payload.horizon_bars,
            thesis_count=payload.thesis_count,
            players=players_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/theses/game-playbook")
def thesis_game_playbook(
    payload: ThesisGamePlaybookRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> GamePlaybookPayload:
    assert_user_scope(payload.user_id, user)
    try:
        return build_game_playbook(
            db,
            user_id=payload.user_id,
            instruments=payload.instruments,
            horizon_bars=payload.horizon_bars,
            thesis_count=payload.thesis_count,
            player_initial_capital=payload.player_initial_capital,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/dashboard/summary/{user_id}", response_model=DashboardResponse)
def dashboard_summary(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DashboardResponse:
    assert_user_scope(user_id, user)
    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    positions = list(
        db.scalars(
            select(PortfolioPosition)
            .where(PortfolioPosition.user_id == user_id)
            .order_by(PortfolioPosition.instrument.asc())
        )
    )
    signals = list(
        db.scalars(
            select(Signal)
            .where(Signal.user_id == user_id)
            .order_by(desc(Signal.id))
            .limit(5)
        )
    )
    all_orders = list(
        db.scalars(
            select(PaperOrder)
            .where(PaperOrder.user_id == user_id)
            .order_by(desc(PaperOrder.id))
        )
    )
    orders = all_orders[:5]
    audits = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.user_id == user_id)
            .order_by(desc(AuditEvent.id))
            .limit(10)
        )
    )
    risk_decisions = list(
        db.scalars(
            select(RiskDecision)
            .where(RiskDecision.user_id == user_id)
            .order_by(desc(RiskDecision.id))
            .limit(5)
        )
    )
    news = list(
        db.scalars(select(NewsArticle).order_by(desc(NewsArticle.id)).limit(5))
    )
    alert_events_data = list(
        db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == user_id)
            .order_by(desc(AlertEvent.id))
            .limit(10)
        )
    )
    all_backtests = list(
        db.scalars(
            select(BacktestRun)
            .where(BacktestRun.user_id == user_id)
            .order_by(desc(BacktestRun.id))
        )
    )
    backtests = all_backtests[:5]
    breaker = db.scalar(
        select(CircuitBreakerState)
        .order_by(desc(CircuitBreakerState.id))
        .limit(1)
    )
    kill_switches = list(
        db.scalars(
            select(KillSwitchState)
            .where(
                or_(
                    KillSwitchState.scope_type == "global",
                    and_(
                        KillSwitchState.scope_type == "user",
                        KillSwitchState.scope_id == str(user_id),
                    ),
                )
            )
            .order_by(desc(KillSwitchState.id))
            .limit(10)
        )
    )
    latest_backtests_payload: list[dict[str, object]] = []
    for run in backtests:
        run_validation = build_validation_snapshot_for_run(db, run)
        latest_backtests_payload.append(
            {
                "run_id": run.id,
                "instrument": run.instrument,
                "trade_count": run.trade_count,
                "win_rate": run.win_rate,
                "total_return_pct": run.total_return_pct,
                "max_drawdown_pct": run.max_drawdown_pct,
                "sharpe_ratio": run_validation["performance"]["sharpe_ratio"],
                "profit_factor": run_validation["performance"]["profit_factor"],
                "risk_flags": run_validation["risk_flags"],
            }
        )
    strategy_validation = None
    if backtests:
        latest_validation = build_validation_snapshot_for_run(db, backtests[0])
        strategy_validation = {
            "latest_run_id": backtests[0].id,
            "performance": latest_validation["performance"],
            "robustness": latest_validation["robustness"],
            "risk_flags": latest_validation["risk_flags"],
        }
    alert_events_by_type: dict[str, int] = {}
    for event in alert_events_data:
        alert_events_by_type[event.event_type] = alert_events_by_type.get(
            event.event_type,
            0,
        ) + 1
    dashboard_scope = sorted(
        {
            *(position.instrument.upper() for position in positions),
            *(signal.instrument.upper() for signal in signals),
            *(order.instrument.upper() for order in orders),
            *(run.instrument.upper() for run in backtests),
        }
    )

    now = datetime.now(UTC)
    coverage_rows: list[dict[str, object]] = []
    latest_market_event_time: str | None = None
    latest_ingest_time: str | None = None
    for instrument in dashboard_scope[:20]:
        latest_tick = db.scalar(
            select(MarketTick)
            .where(MarketTick.instrument == instrument)
            .order_by(desc(MarketTick.ingest_time), desc(MarketTick.id))
            .limit(1)
        )
        if latest_tick is None:
            continue
        ingest_at = datetime.fromisoformat(latest_tick.ingest_time)
        if ingest_at.tzinfo is None:
            ingest_at = ingest_at.replace(tzinfo=UTC)
        lag_seconds = round(max(0.0, (now - ingest_at.astimezone(UTC)).total_seconds()), 4)
        if latest_market_event_time is None or latest_tick.event_time > latest_market_event_time:
            latest_market_event_time = latest_tick.event_time
        if latest_ingest_time is None or latest_tick.ingest_time > latest_ingest_time:
            latest_ingest_time = latest_tick.ingest_time
        coverage_rows.append(
            {
                "instrument": latest_tick.instrument,
                "provider": latest_tick.provider,
                "last_price": float(latest_tick.price),
                "last_event_time": latest_tick.event_time,
                "last_ingest_time": latest_tick.ingest_time,
                "lag_seconds": lag_seconds,
            }
        )

    coverage: dict[str, object] = {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "total_instruments_covered": len(coverage_rows),
        "latest_market_event_time": latest_market_event_time,
        "latest_ingest_time": latest_ingest_time,
        "instruments": coverage_rows,
    }

    data_quality_gate_payload: dict[str, object] | None = None
    if dashboard_scope:
        data_quality_gate_payload = build_data_quality_gate_snapshot(
            db,
            instruments=dashboard_scope,
            include_provider_health=False,
        )
    phase_kickoff_date = "2026-04-27"

    def as_day(value: str | None) -> str:
        raw = str(value or "")
        return raw[:10] if len(raw) >= 10 else ""

    def avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    def _safe_number(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _load_json_dict(path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return raw if isinstance(raw, dict) else None

    historical_backtests = [
        run
        for run in all_backtests
        if as_day(run.started_at) and as_day(run.started_at) < phase_kickoff_date
    ]
    historical_orders = [
        order
        for order in all_orders
        if as_day(order.created_at) and as_day(order.created_at) < phase_kickoff_date
    ]
    current_backtests = [
        run
        for run in all_backtests
        if as_day(run.started_at) and as_day(run.started_at) >= phase_kickoff_date
    ]
    current_orders = [
        order
        for order in all_orders
        if as_day(order.created_at) and as_day(order.created_at) >= phase_kickoff_date
    ]

    historical_backtest_days = [as_day(run.started_at) for run in historical_backtests if as_day(run.started_at)]
    historical_analysis_summary: dict[str, object] = {
        "period_label": f"ate {phase_kickoff_date} (base historica)",
        "thesis_count": len(historical_backtests),
        "backtest_runs": len(historical_backtests),
        "operacoes_simuladas": len(historical_orders),
        "total_trades": sum(int(run.trade_count or 0) for run in historical_backtests),
        "avg_expected_pct": avg(
            [float(run.total_return_pct or 0.0) for run in historical_backtests],
        ),
        "avg_win_rate_pct": avg([float(run.win_rate or 0.0) for run in historical_backtests]),
        "avg_return_pct": avg(
            [float(run.total_return_pct or 0.0) for run in historical_backtests],
        ),
        "approved_count": sum(
            1 for run in historical_backtests if float(run.total_return_pct or 0.0) >= 0.0
        ),
        "avg_drawdown_pct": avg(
            [float(run.max_drawdown_pct or 0.0) for run in historical_backtests],
        ),
        "window_start": min(historical_backtest_days) if historical_backtest_days else None,
        "window_end": max(historical_backtest_days) if historical_backtest_days else None,
    }

    current_daily_map: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "paper_orders": 0,
            "accepted_orders": 0,
            "rejected_orders": 0,
            "gross_amount_brl": 0.0,
            "estimated_cost_brl": 0.0,
            "estimated_tax_brl": 0.0,
            "backtest_runs": 0,
            "backtest_trades": 0,
            "backtest_return_total": 0.0,
        },
    )

    for order in current_orders:
        day = as_day(order.created_at)
        if not day:
            continue
        row = current_daily_map[day]
        row["paper_orders"] += 1
        if str(order.risk_status or "").lower() == "accepted":
            row["accepted_orders"] += 1
        else:
            row["rejected_orders"] += 1
        row["gross_amount_brl"] += float(order.gross_amount or 0.0)
        row["estimated_cost_brl"] += float(order.estimated_cost or 0.0)
        row["estimated_tax_brl"] += float(order.estimated_tax or 0.0)

    for run in current_backtests:
        day = as_day(run.finished_at) or as_day(run.started_at)
        if not day:
            continue
        row = current_daily_map[day]
        row["backtest_runs"] += 1
        row["backtest_trades"] += int(run.trade_count or 0)
        row["backtest_return_total"] += float(run.total_return_pct or 0.0)

    current_simulation_daily: list[dict[str, object]] = []
    for day in sorted(current_daily_map.keys()):
        row = current_daily_map[day]
        backtest_runs = int(row["backtest_runs"])
        avg_backtest_return_pct = (
            round(float(row["backtest_return_total"]) / backtest_runs, 4)
            if backtest_runs > 0
            else 0.0
        )
        current_simulation_daily.append(
            {
                "day": day,
                "paper_orders": int(row["paper_orders"]),
                "accepted_orders": int(row["accepted_orders"]),
                "rejected_orders": int(row["rejected_orders"]),
                "gross_amount_brl": round(float(row["gross_amount_brl"]), 2),
                "estimated_cost_brl": round(float(row["estimated_cost_brl"]), 2),
                "estimated_tax_brl": round(float(row["estimated_tax_brl"]), 2),
                "backtest_runs": backtest_runs,
                "backtest_trades": int(row["backtest_trades"]),
                "avg_backtest_return_pct": avg_backtest_return_pct,
            }
        )

    current_simulation_summary: dict[str, object] = {
        "period_label": f"desde {phase_kickoff_date} (simulacao atual)",
        "thesis_count": len(current_orders),
        "paper_orders": len(current_orders),
        "accepted_orders": sum(
            1 for order in current_orders if str(order.risk_status or "").lower() == "accepted"
        ),
        "rejected_orders": sum(
            1 for order in current_orders if str(order.risk_status or "").lower() != "accepted"
        ),
        "gross_amount_brl": round(
            sum(float(order.gross_amount or 0.0) for order in current_orders),
            2,
        ),
        "estimated_cost_brl": round(
            sum(float(order.estimated_cost or 0.0) for order in current_orders),
            2,
        ),
        "estimated_tax_brl": round(
            sum(float(order.estimated_tax or 0.0) for order in current_orders),
            2,
        ),
        "backtest_runs": len(current_backtests),
        "backtest_trades": sum(int(run.trade_count or 0) for run in current_backtests),
        "avg_expected_pct": avg([float(run.total_return_pct or 0.0) for run in current_backtests]),
        "avg_backtest_return_pct": avg(
            [float(run.total_return_pct or 0.0) for run in current_backtests],
        ),
        "approved_count": sum(1 for run in current_backtests if float(run.total_return_pct or 0.0) >= 0.0),
        "monitoring_days": len(current_simulation_daily),
        "last_order_at": current_orders[0].created_at if current_orders else None,
    }

    historical_empty = (
        _safe_int(historical_analysis_summary.get("backtest_runs")) == 0
        and _safe_int(historical_analysis_summary.get("operacoes_simuladas")) == 0
        and _safe_int(historical_analysis_summary.get("total_trades")) == 0
    )
    current_empty = (
        _safe_int(current_simulation_summary.get("paper_orders")) == 0
        and _safe_int(current_simulation_summary.get("backtest_runs")) == 0
        and _safe_int(current_simulation_summary.get("monitoring_days")) == 0
    )

    case_study_latest = _load_json_dict(data_dir / "case_study_latest.json")
    if historical_empty and case_study_latest is not None:
        selected_case = case_study_latest.get("selected_case")
        if isinstance(selected_case, dict):
            thesis = selected_case.get("thesis")
            outcome = selected_case.get("outcome")
            kpis = selected_case.get("kpis")
            thesis_dict = thesis if isinstance(thesis, dict) else {}
            outcome_dict = outcome if isinstance(outcome, dict) else {}
            kpis_dict = kpis if isinstance(kpis, dict) else {}
            thesis_day = as_day(
                str(
                    selected_case.get("thesis_raised_at")
                    or thesis_dict.get("entry_time")
                    or ""
                )
            )
            realized_pct = round(
                _safe_number(
                    kpis_dict.get(
                        "realized_financial_pct",
                        outcome_dict.get("realized_financial_pct"),
                    ),
                ),
                4,
            )
            expected_pct = round(
                _safe_number(
                    kpis_dict.get(
                        "expected_financial_pct",
                        thesis_dict.get("expected_financial_pct"),
                    ),
                ),
                4,
            )
            success = bool(outcome_dict.get("success"))
            historical_analysis_summary = {
                "period_label": f"ate {phase_kickoff_date} (base historica · case study)",
                "thesis_count": 1,
                "backtest_runs": 1,
                "operacoes_simuladas": 1,
                "total_trades": 1,
                "avg_expected_pct": expected_pct,
                "avg_win_rate_pct": 100.0 if success else 0.0,
                "avg_return_pct": realized_pct,
                "approved_count": 1 if success else 0,
                "avg_drawdown_pct": 0.0,
                "window_start": thesis_day or None,
                "window_end": thesis_day or None,
                "instrument": str(thesis_dict.get("instrument") or ""),
                "direction": str(thesis_dict.get("direction") or ""),
            }

    current_monitor_latest = _load_json_dict(data_dir / "current_thesis_monitor_latest.json")
    if current_empty and current_monitor_latest is not None:
        monitor_summary = current_monitor_latest.get("summary")
        monitor_summary_dict = monitor_summary if isinstance(monitor_summary, dict) else {}
        theses_payload = current_monitor_latest.get("theses")
        theses_payload_list = (
            [item for item in theses_payload if isinstance(item, dict)]
            if isinstance(theses_payload, list)
            else []
        )
        generated_at = str(current_monitor_latest.get("generated_at") or "")
        thesis_count = _safe_int(current_monitor_latest.get("thesis_count"), 0)
        target_hits = _safe_int(monitor_summary_dict.get("target_hits"), 0)
        stop_alerts = _safe_int(monitor_summary_dict.get("stop_alerts"), 0)
        monitoring_count = _safe_int(monitor_summary_dict.get("monitoring_count"), 0)
        avg_expected = avg(
            [_safe_number(item.get("expected_financial_pct")) for item in theses_payload_list],
        )
        avg_unrealized = round(
            _safe_number(monitor_summary_dict.get("avg_unrealized_financial_pct"), 0.0),
            4,
        )
        current_simulation_summary = {
            "period_label": f"desde {phase_kickoff_date} (simulacao atual · teses monitoradas)",
            "thesis_count": thesis_count,
            "paper_orders": thesis_count,
            "accepted_orders": monitoring_count + target_hits,
            "rejected_orders": stop_alerts,
            "gross_amount_brl": 0.0,
            "estimated_cost_brl": 0.0,
            "estimated_tax_brl": 0.0,
            "backtest_runs": target_hits,
            "backtest_trades": thesis_count,
            "avg_expected_pct": avg_expected,
            "avg_backtest_return_pct": avg_unrealized,
            "approved_count": target_hits,
            "monitoring_days": 1 if thesis_count > 0 else 0,
            "last_order_at": generated_at or None,
        }
        if not current_simulation_daily and thesis_count > 0:
            current_simulation_daily = [
                {
                    "day": as_day(generated_at) or phase_kickoff_date,
                    "paper_orders": thesis_count,
                    "accepted_orders": monitoring_count + target_hits,
                    "rejected_orders": stop_alerts,
                    "gross_amount_brl": 0.0,
                    "estimated_cost_brl": 0.0,
                    "estimated_tax_brl": 0.0,
                    "backtest_runs": target_hits,
                    "backtest_trades": thesis_count,
                    "avg_backtest_return_pct": avg_unrealized,
                }
            ]

    historical_thesis_count = _safe_int(
        historical_analysis_summary.get("thesis_count"),
        _safe_int(historical_analysis_summary.get("backtest_runs")),
    )
    historical_expected_pct = round(
        _safe_number(
            historical_analysis_summary.get("avg_expected_pct"),
            _safe_number(historical_analysis_summary.get("avg_return_pct"), 0.0),
        ),
        4,
    )
    historical_achieved_pct = round(
        _safe_number(historical_analysis_summary.get("avg_return_pct"), 0.0),
        4,
    )
    historical_approved_count = _safe_int(
        historical_analysis_summary.get("approved_count"),
        (1 if historical_achieved_pct >= 0.0 and historical_thesis_count > 0 else 0),
    )

    current_thesis_count = _safe_int(
        current_simulation_summary.get("thesis_count"),
        _safe_int(current_simulation_summary.get("paper_orders")),
    )
    current_expected_pct = round(
        _safe_number(
            current_simulation_summary.get("avg_expected_pct"),
            _safe_number(current_simulation_summary.get("avg_backtest_return_pct"), 0.0),
        ),
        4,
    )
    current_achieved_pct = round(
        _safe_number(current_simulation_summary.get("avg_backtest_return_pct"), 0.0),
        4,
    )
    current_approved_count = _safe_int(
        current_simulation_summary.get("approved_count"),
        _safe_int(current_simulation_summary.get("accepted_orders")),
    )

    thesis_executive_summary: dict[str, object] = {
        "historical": {
            "period_label": str(historical_analysis_summary.get("period_label") or "historico"),
            "thesis_count": historical_thesis_count,
            "expected_pct": historical_expected_pct,
            "achieved_pct": historical_achieved_pct,
            "approved_count": historical_approved_count,
        },
        "current": {
            "period_label": str(current_simulation_summary.get("period_label") or "pos go-live"),
            "thesis_count": current_thesis_count,
            "expected_pct": current_expected_pct,
            "achieved_pct": current_achieved_pct,
            "approved_count": current_approved_count,
        },
    }

    thesis_open_operations: list[dict[str, object]] = []
    if current_monitor_latest is not None:
        theses_payload = current_monitor_latest.get("theses")
        theses_payload_list = (
            [item for item in theses_payload if isinstance(item, dict)]
            if isinstance(theses_payload, list)
            else []
        )
        for index, item in enumerate(theses_payload_list):
            direction = str(item.get("direction") or "").lower()
            if direction == "bullish":
                operation_side = "Compra"
            elif direction == "bearish":
                operation_side = "Venda"
            else:
                operation_side = "Neutra"

            operation = item.get("suggested_operation")
            operation_dict = operation if isinstance(operation, dict) else {}
            strategy_name = str(operation_dict.get("strategy_name") or operation_dict.get("strategy_id") or "n/d")
            operation_rationale = str(
                operation_dict.get("rationale") or item.get("suggested_action") or "n/d"
            )
            max_gain_pct = round(_safe_number(operation_dict.get("max_gain_pct"), 0.0), 4)
            max_loss_pct = round(_safe_number(operation_dict.get("max_loss_pct"), 0.0), 4)
            target_price = round(_safe_number(item.get("target_price"), 0.0), 4)
            stop_price = round(_safe_number(item.get("stop_price"), 0.0), 4)
            suggested_exit_time = str(item.get("suggested_exit_time") or "")

            why_thesis = item.get("why_thesis")
            why_list = (
                [str(value) for value in why_thesis if isinstance(value, (str, int, float))]
                if isinstance(why_thesis, list)
                else []
            )
            thesis_reason = str(item.get("reason_category") or "")
            if not thesis_reason:
                thesis_reason = " | ".join(why_list[:3]) if why_list else "n/d"

            monitoring_events = item.get("monitoring_events")
            monitoring_events_list = (
                [event for event in monitoring_events if isinstance(event, dict)]
                if isinstance(monitoring_events, list)
                else []
            )
            has_exit_event = any(
                str(event.get("event_type") or "").lower() == "exit_snapshot"
                for event in monitoring_events_list
            )
            monitor_status = str(item.get("monitor_status") or "").lower()
            status_label = (
                "Fechada"
                if has_exit_event or monitor_status in {"closed", "encerrada", "finished", "exited"}
                else "Aberta"
            )
            if status_label != "Aberta":
                continue

            thesis_open_operations.append(
                {
                    "thesis_number": index + 1,
                    "thesis_id": str(item.get("thesis_id") or f"Tese {index + 1}"),
                    "action": str(item.get("instrument") or "n/d"),
                    "thesis_reason": thesis_reason,
                    "expected_result_pct": round(
                        _safe_number(item.get("expected_financial_pct"), 0.0),
                        4,
                    ),
                    "operation_plan": (
                        f"{operation_side} ate {as_day(suggested_exit_time) or suggested_exit_time or '-'} "
                        f"({operation_rationale})"
                    ),
                    "structured_operation": (
                        f"{strategy_name} | ganho max {max_gain_pct:.2f}% | perda max {max_loss_pct:.2f}%"
                    ),
                    "exit_rule": f"Sai acima de {target_price} ou abaixo de {stop_price}",
                    "status": status_label,
                    "moment_result_pct": round(
                        _safe_number(item.get("unrealized_financial_pct"), 0.0),
                        4,
                    ),
                }
            )

    return DashboardResponse(
        user_id=user_id,
        investor_profile=profile.investor_profile if profile is not None else None,
        open_positions=[
            {
                "instrument": position.instrument,
                "quantity": position.quantity,
                "average_price": position.average_price,
                "updated_at": position.updated_at,
            }
            for position in positions
        ],
        latest_signals=[
            {
                "signal_id": signal.id,
                "instrument": signal.instrument,
                "signal_type": signal.signal_type,
                "confidence": signal.confidence,
                "rationale": signal.rationale,
            }
            for signal in signals
        ],
        latest_orders=[
            {
                "order_id": order.id,
                "instrument": order.instrument,
                "quantity": order.quantity,
                "execution_price": order.execution_price,
                "estimated_cost": order.estimated_cost,
                "estimated_tax": order.estimated_tax,
                "risk_status": order.risk_status,
                "risk_notes": order.risk_notes,
            }
            for order in orders
        ],
        latest_audit_events=[
            {
                "event_type": event.event_type,
                "details": event.details,
                "created_at": event.created_at,
            }
            for event in audits
        ],
        risk_decisions=[
            {
                "decision": decision.decision,
                "instrument": decision.instrument,
                "notes": decision.notes,
                "decided_at": decision.decided_at,
                "portfolio_exposure": decision.portfolio_exposure,
                "projected_exposure": decision.projected_exposure,
            }
            for decision in risk_decisions
        ],
        latest_news=[
            {
                "headline": article.headline,
                "instrument": article.instrument,
                "anti_hype_score": article.anti_hype_score,
                "source_name": article.source_name,
            }
            for article in news
        ],
        latest_backtests=latest_backtests_payload,
        circuit_breaker=(
            {
                "instrument": breaker.instrument,
                "status": breaker.status,
                "reason": breaker.reason,
            }
            if breaker is not None
            else None
        ),
        kill_switches=[
            {
                "scope_type": state.scope_type,
                "scope_id": state.scope_id,
                "status": state.status,
                "reason": state.reason,
            }
            for state in kill_switches
        ],
        alert_events=[
            {
                "event_type": event.event_type,
                "instrument": event.instrument,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in alert_events_data
        ],
        strategy_validation=strategy_validation,
        alert_summary={
            "total_events": len(alert_events_data),
            "by_type": alert_events_by_type,
        },
        market_coverage=cast(dict[str, object], coverage),
        data_quality_gate=cast(dict[str, object], data_quality_gate_payload),
        phase_kickoff_date=phase_kickoff_date,
        historical_analysis_summary=historical_analysis_summary,
        current_simulation_summary=current_simulation_summary,
        current_simulation_daily=current_simulation_daily,
        thesis_executive_summary=thesis_executive_summary,
        thesis_open_operations=thesis_open_operations,
        disclaimer=DISCLAIMER,
    )


@app.get("/api/agent/status")
def agent_status(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    _ = user.id
    payload = agent_loop.status(db)
    return dict(payload)


@app.websocket("/ws/agent")
async def websocket_agent(
    websocket: WebSocket,
) -> None:
    await websocket.accept()
    try:
        while True:
            with SessionLocal() as db:
                payload = agent_loop.status(db)
            await websocket.send_json({"type": "worker_status", "payload": dict(payload)})
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/signals")
async def websocket_signals(
    websocket: WebSocket,
) -> None:
    user_id_raw = websocket.query_params.get("user_id")
    try:
        user_id = int(user_id_raw or "")
    except ValueError:
        await websocket.close(code=1008, reason="user_id invalido")
        return
    if user_id <= 0:
        await websocket.close(code=1008, reason="user_id obrigatorio")
        return
    await websocket.accept()
    seen_status: dict[int, str] = {}
    try:
        while True:
            try:
                probe = await asyncio.wait_for(websocket.receive(), timeout=0.01)
                if probe.get("type") == "websocket.disconnect":
                    return
            except TimeoutError:
                pass

            with SessionLocal() as db:
                rows = list(
                    db.scalars(
                        select(Signal)
                        .where(Signal.user_id == user_id)
                        .order_by(desc(Signal.id))
                        .limit(120)
                    )
                )
            current_status = {row.id: row.signal_status for row in rows}
            for row in reversed(rows):
                previous = seen_status.get(row.id)
                if previous is None:
                    event_type = (
                        "new_signal"
                        if row.signal_status == "active"
                        else "signal_expired"
                    )
                    await websocket.send_json(
                        {
                            "type": event_type,
                            "payload": signal_to_payload(row),
                        }
                    )
                    continue
                if previous != row.signal_status:
                    event_type = (
                        "signal_expired"
                        if row.signal_status != "active"
                        else "signal_updated"
                    )
                    await websocket.send_json(
                        {
                            "type": event_type,
                            "payload": signal_to_payload(row),
                        }
                    )
            seen_status = current_status
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        return

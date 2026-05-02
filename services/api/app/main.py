from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, cast

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
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
    Tenant,
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
    WhatsAppNotificationSettingsRequest,
    WhatsAppNotificationTestRequest,
)
from app.services.alerts import create_alert_rule
from app.services.asset_classes import asset_class_label, classify_instrument
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
from app.services.notifications import (
    get_whatsapp_settings_payload,
    process_whatsapp_webhook_payload,
    send_daily_digest_for_all,
    send_test_whatsapp_notification,
    upsert_whatsapp_settings,
    verify_webhook_signature,
)
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
from app.services.thesis_current_monitor import (
    CurrentThesisMonitorPayload,
    run_current_thesis_monitor,
)
from app.services.thesis_gamification import (
    GameSimulationPayload,
    OptionId,
    PlayerConfigInput,
    PlayerDecisionInput,
    StrategyProfile,
    run_thesis_game_simulation,
)
from app.services.thesis_learning import ThesisLearningPayload, run_thesis_skill_learning_cycle
from app.services.utils import (
    DISCLAIMER,
    access_token_ttl_seconds,
    decode_access_token,
    hash_password,
    isoformat,
    utc_now,
)
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
bundled_data_dir = Path(__file__).resolve().parents[3] / "data"
data_dir = Path(os.getenv("DATA_DIR", str(bundled_data_dir)))
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
agent_loop = AgentLoop()
AUTH_DISABLED = os.getenv("DISABLE_AUTH", "1").strip().lower() in {"1", "true", "yes", "on"}
DEFAULT_ANON_USER_ID = int(os.getenv("ANON_USER_ID", "1"))
DEFAULT_ANON_EMAIL = os.getenv("ANON_USER_EMAIL", "anon@graoinvest.local").strip().lower()
DEFAULT_ANON_FULL_NAME = os.getenv("ANON_USER_FULL_NAME", "Convidado")
DEFAULT_ANON_TENANT_NAME = os.getenv("ANON_TENANT_NAME", "Grao Invest")
DEFAULT_ANON_PASSWORD = os.getenv("ANON_USER_PASSWORD", "anon-access-disabled")


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


def _resolve_anonymous_user(db: Session) -> User:
    user = db.get(User, DEFAULT_ANON_USER_ID)
    if user is not None:
        return user
    user_by_email = db.scalar(
        select(User).where(User.email == DEFAULT_ANON_EMAIL).limit(1),
    )
    if user_by_email is not None:
        return user_by_email

    tenant = db.scalar(select(Tenant).order_by(Tenant.id.asc()).limit(1))
    if tenant is None:
        tenant = Tenant(
            name=DEFAULT_ANON_TENANT_NAME,
            created_at=isoformat(utc_now()),
        )
        db.add(tenant)
        db.flush()

    candidate = User(
        id=DEFAULT_ANON_USER_ID,
        tenant_id=tenant.id,
        email=DEFAULT_ANON_EMAIL,
        password_hash=hash_password(DEFAULT_ANON_PASSWORD),
        full_name=DEFAULT_ANON_FULL_NAME,
        created_at=isoformat(utc_now()),
        mfa_enabled=False,
    )
    db.add(candidate)
    try:
        db.commit()
        db.refresh(candidate)
        return candidate
    except IntegrityError:
        db.rollback()
        resolved = db.get(User, DEFAULT_ANON_USER_ID)
        if resolved is not None:
            return resolved
        resolved_by_email = db.scalar(select(User).where(User.email == DEFAULT_ANON_EMAIL).limit(1))
        if resolved_by_email is not None:
            return resolved_by_email

    fallback = db.scalar(select(User).order_by(User.id.asc()).limit(1))
    if fallback is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nenhum usuario disponivel para acesso anonimo",
        )
    return fallback


def current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> User:
    if AUTH_DISABLED and not authorization:
        return _resolve_anonymous_user(db)
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
        **asset_class_payload(signal.instrument),
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


def asset_class_payload(instrument: str) -> dict[str, str]:
    asset_class = classify_instrument(instrument)
    return {
        "asset_class": asset_class,
        "asset_class_label": asset_class_label(asset_class),
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


@app.get("/api/notifications/whatsapp")
def whatsapp_notification_settings(
    user_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(user_id, user)
    return get_whatsapp_settings_payload(db, user_id=user_id)


@app.put("/api/notifications/whatsapp")
def whatsapp_notification_settings_update(
    payload: WhatsAppNotificationSettingsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    try:
        upsert_whatsapp_settings(
            db,
            user_id=payload.user_id,
            phone_number=payload.phone_number,
            display_name=payload.display_name,
            opt_in=payload.opt_in,
            categories=payload.categories.model_dump(),
            thresholds=payload.thresholds.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_whatsapp_settings_payload(db, user_id=payload.user_id)


@app.post("/api/notifications/whatsapp/test")
def whatsapp_notification_test(
    payload: WhatsAppNotificationTestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    assert_user_scope(payload.user_id, user)
    delivery = send_test_whatsapp_notification(db, user_id=payload.user_id)
    return {
        "delivery_id": delivery.id,
        "category": delivery.category,
        "status": delivery.status,
        "failure_reason": delivery.failure_reason,
        "provider_message_id": delivery.provider_message_id,
        "created_at": delivery.created_at,
        "sent_at": delivery.sent_at,
    }


@app.get("/api/webhooks/whatsapp", response_class=PlainTextResponse)
def whatsapp_webhook_verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> str:
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    if hub_mode != "subscribe" or not expected or hub_verify_token != expected:
        raise HTTPException(status_code=403, detail="Webhook WhatsApp nao autorizado.")
    return hub_challenge


@app.post("/api/webhooks/whatsapp")
async def whatsapp_webhook_receive(
    request: Request,
    x_hub_signature_256: Annotated[
        str | None,
        Header(alias="X-Hub-Signature-256"),
    ] = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Assinatura WhatsApp invalida.")
    try:
        payload = cast(dict[str, object], json.loads(raw_body.decode("utf-8") or "{}"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Payload WhatsApp invalido.") from exc
    return process_whatsapp_webhook_payload(db, payload)


def _assert_cron_authorized(authorization: str | None) -> None:
    cron_secret = os.getenv("CRON_SECRET", "").strip()
    if not cron_secret or authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Cron nao autorizado.")


@app.get("/api/cron/whatsapp-digest")
@app.post("/api/cron/whatsapp-digest")
def whatsapp_digest_cron(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _assert_cron_authorized(authorization)
    return send_daily_digest_for_all(db)


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
    learning_evolution = cast(dict[str, object], report.get("learning_evolution", {}))
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

    learning_cases_html = ""
    learning_cases = learning_evolution.get("cases", [])
    if isinstance(learning_cases, list):
        for item in learning_cases[:3]:
            if not isinstance(item, dict):
                continue
            tone = "#86efac" if item.get("success") is True else "#fca5a5"
            learning_cases_html += (
                "<div class='learning-card'>"
                "<div style='display:flex;justify-content:space-between;gap:12px;align-items:flex-start'>"
                f"<strong>{safe_cell(item.get('label'))}</strong>"
                f"<span style='color:{tone};font-weight:700'>{safe_cell(fmt_pct(item.get('realized_financial_pct')))}</span>"
                "</div>"
                f"<p><strong>{safe_cell(item.get('instrument'))}</strong> | "
                f"{safe_cell(item.get('strategy'))} | confianca "
                f"{safe_cell(fmt_pct(item.get('confidence_pct')))}</p>"
                f"<p>{safe_cell(item.get('narrative'))}</p>"
                "<p>"
                f"Entrada {safe_cell(item.get('entry_date'))} @ {safe_cell(fmt_money(item.get('entry_price')))} | "
                f"alvo {safe_cell(fmt_money(item.get('target_price')))} | "
                f"stop {safe_cell(fmt_money(item.get('stop_price')))}"
                "</p>"
                "<p>"
                f"Saida {safe_cell(item.get('exit_date'))} @ {safe_cell(fmt_money(item.get('exit_price')))} | "
                f"esperado {safe_cell(fmt_pct(item.get('expected_financial_pct')))}"
                "</p>"
                f"<p><strong>Por que entrou:</strong> {safe_cell(item.get('why_entered'))}</p>"
                f"<p><strong>Aprendizado:</strong> {safe_cell(item.get('learning'))}</p>"
                "</div>"
            )
    if not learning_cases_html:
        learning_cases_html = (
            "<div class='learning-card'><p>Sem sequencia de aprendizado consolidada ainda.</p></div>"
        )

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
        ".learning-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}"
        ".learning-card{background:#0f172a;border:1px solid #243044;border-radius:8px;padding:12px}"
        ".learning-card p{color:#cbd5e1;font-size:13px;line-height:1.42;margin:8px 0 0}"
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
        "<div class='card'><h3 style='margin:0'>Evolucao do Aprendizado</h3>"
        f"<p style='color:#cbd5e1;margin:8px 0 0'>{safe_cell(learning_evolution.get('headline'))}</p>"
        f"<p style='color:#94a3b8;margin:6px 0 0'>{safe_cell(learning_evolution.get('context'))}</p>"
        f"<div class='learning-grid'>{learning_cases_html}</div>"
        f"<p style='color:#93c5fd;margin:12px 0 0'><strong>Conclusao:</strong> {safe_cell(learning_evolution.get('conclusion'))}</p>"
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
                **asset_class_payload(run.instrument),
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
    coverage_asset_class_counts: dict[str, int] = {}
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
        asset_class = classify_instrument(latest_tick.instrument)
        coverage_asset_class_counts[asset_class] = (
            coverage_asset_class_counts.get(asset_class, 0) + 1
        )
        coverage_rows.append(
            {
                "instrument": latest_tick.instrument,
                "asset_class": asset_class,
                "asset_class_label": asset_class_label(asset_class),
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
        "asset_class_counts": coverage_asset_class_counts,
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

    def _safe_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _extract_exit_datetime(
        events: list[dict[str, object]],
        fallback: object = None,
    ) -> datetime | None:
        exit_times = [
            _safe_datetime(event.get("event_time"))
            for event in events
            if str(event.get("event_type") or "").lower() == "exit_snapshot"
        ]
        valid_exit_times = [value for value in exit_times if value is not None]
        if valid_exit_times:
            return max(valid_exit_times)
        return _safe_datetime(fallback)

    def _duration_days(entry_time: object, exit_time: object) -> int | None:
        start_dt = _safe_datetime(entry_time)
        end_dt = _safe_datetime(exit_time)
        if start_dt is None or end_dt is None:
            return None
        delta_days = (end_dt - start_dt).total_seconds() / 86400.0
        return int(round(max(0.0, delta_days)))

    def _humanize_signal(signal: object) -> str:
        raw = str(signal or "").strip()
        if not raw:
            return ""
        cleaned = raw.replace("_", " ").replace("-", " ").strip()
        return cleaned[:72]

    def _build_thesis_candidate_reason(
        *,
        instrument: str,
        reason_category: str,
        direction: str,
        confidence_pct: float,
        technical_support_pct: float,
        fundamental_support_pct: float,
        news_support_pct: float,
        why_signals: list[str],
    ) -> str:
        def _friendly_direction(raw_direction: str) -> str:
            normalized = raw_direction.strip().lower()
            if normalized == "bullish":
                return "de alta"
            if normalized == "bearish":
                return "de queda"
            if normalized == "range":
                return "de estabilidade"
            return "de movimento misto"

        def _friendly_category(raw_category: str) -> str:
            normalized = raw_category.strip().lower()
            if "case study" in normalized or "historico" in normalized:
                return "comparamos com situações parecidas do histórico e encontramos um padrão semelhante"
            if "grafico" in normalized or "tecnico" in normalized:
                return "o comportamento recente do preço indicou uma oportunidade"
            return "o conjunto de sinais apontou uma oportunidade com boa consistência"

        def _friendly_signal(raw_signal: str) -> str:
            normalized = _humanize_signal(raw_signal).lower()
            if not normalized:
                return ""
            signal_map: list[tuple[str, str]] = [
                ("momento bullish", "preço com sinal de subida"),
                ("momento bearish", "preço com sinal de queda"),
                ("momento range", "preço em faixa estável"),
                ("suporte tecnico", "gráfico confirmou o movimento"),
                ("suporte fundamental", "dados da empresa favoráveis"),
                ("suporte news", "notícias mais positivas"),
                ("suporte historico", "padrão parecido com casos anteriores"),
                ("volatilidade", "oscilações em nível controlado"),
                ("valuation", "preço considerado atrativo"),
                ("rentabilidade", "rentabilidade da empresa consistente"),
                ("crescimento receita", "receita em crescimento"),
                ("dividend yield", "dividendos em nível favorável"),
            ]
            for token, label in signal_map:
                if token in normalized:
                    return label
            return normalized[:56]

        direction_label = _friendly_direction(direction)
        category_label = _friendly_category(reason_category)
        top_signals: list[str] = []
        for item in why_signals:
            friendly = _friendly_signal(item)
            if friendly and friendly not in top_signals:
                top_signals.append(friendly)
            if len(top_signals) >= 3:
                break
        signal_excerpt = (
            ", ".join(top_signals)
            if top_signals
            else "preço, fundamentos e contexto"
        )
        confidence_label = (
            "alto"
            if confidence_pct >= 75.0
            else "médio"
            if confidence_pct >= 60.0
            else "em observação"
        )
        support_score = (technical_support_pct + fundamental_support_pct + news_support_pct) / 3.0
        support_label = (
            "forte"
            if support_score >= 75.0
            else "razoável"
            if support_score >= 55.0
            else "mista"
        )
        instrument_label = instrument.strip().upper() if instrument.strip() else "o ativo"
        direction_label = _friendly_direction(direction)
        return (
            f"Tese {direction_label} para {instrument_label}: {category_label}. "
            f"O que pesou na decisão: {signal_excerpt}. "
            f"Nível de confiança {confidence_label} e sustentação {support_label}."
        )

    def _build_operation_plan_text(
        *,
        direction: str,
        operation_side: str,
        exit_day: str,
        entry_price: float,
        target_price: float,
        stop_price: float,
        expected_result_pct: float,
    ) -> str:
        direction_label = direction.strip().lower()
        prazo = exit_day or "-"
        if direction_label == "bullish":
            return (
                f"{operation_side} até {prazo}. "
                f"Plano: buscar alta de {entry_price:.2f} para perto de {target_price:.2f}. "
                f"Se cair para {stop_price:.2f}, encerramos para proteger a posição. "
                f"Retorno esperado: {expected_result_pct:.2f}%."
            )
        if direction_label == "bearish":
            return (
                f"{operation_side} até {prazo}. "
                f"Plano: capturar queda de {entry_price:.2f} em direção a {target_price:.2f}. "
                f"Se subir para {stop_price:.2f}, encerramos para limitar perda. "
                f"Retorno esperado: {expected_result_pct:.2f}%."
            )
        if direction_label == "range":
            lower_bound = min(stop_price, target_price)
            upper_bound = max(stop_price, target_price)
            return (
                f"{operation_side} até {prazo}. "
                f"Plano: operar em faixa, esperando preço entre {lower_bound:.2f} e {upper_bound:.2f}. "
                f"Se sair dessa faixa, encerramos para proteção. "
                f"Retorno esperado: {expected_result_pct:.2f}%."
            )
        return (
            f"{operation_side} até {prazo}, com saída por alvo ou stop de proteção. "
            f"Retorno esperado: {expected_result_pct:.2f}%."
        )

    def _build_learning_note(
        *,
        direction: str,
        status: str,
        outcome: str,
        expected_result_pct: float,
        realized_result_pct: float,
    ) -> str:
        status_label = status.strip().lower()
        outcome_label = outcome.strip().lower()
        direction_label = direction.strip().lower()
        if "aberta" in status_label or "monitor" in status_label:
            return (
                "Tese ainda em aberto: manter acompanhamento diário e só ajustar a operação "
                "com novo sinal confirmado."
            )
        if "alvo" in outcome_label:
            if expected_result_pct > 0 and realized_result_pct < expected_result_pct:
                return (
                    "A direção estava correta, mas o ganho veio abaixo do esperado. "
                    "Próxima: calibrar melhor alvo e prazo."
                )
            return (
                "A tese funcionou bem. Próxima: repetir os mesmos critérios de entrada, "
                "mantendo proteção de saída."
            )
        if "stop" in outcome_label:
            if direction_label == "range":
                return (
                    "A proteção evitou perda maior. Próxima: só operar faixa lateral quando "
                    "a estabilidade estiver mais clara."
                )
            return (
                "O stop protegeu capital. Próxima: exigir confirmação adicional antes da entrada "
                "e reduzir exposição inicial."
            )
        if "tempo" in outcome_label:
            if realized_result_pct >= 0:
                return (
                    "O movimento foi mais lento que o esperado. Próxima: usar prazo um pouco maior "
                    "ou saída parcial."
                )
            return (
                "O tempo jogou contra a tese. Próxima: janela mais curta e gatilhos de saída antecipados."
            )
        if realized_result_pct >= 0:
            return (
                "Resultado positivo com margem para ajuste. Próxima: manter critérios e refinar alvo."
            )
        return (
            "Resultado abaixo do esperado. Próxima: aumentar filtros de confirmação e reforçar proteção."
        )

    def _load_json_dict(path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return raw if isinstance(raw, dict) else None

    def _load_runtime_or_bundled_json(filename: str) -> dict[str, object] | None:
        runtime_payload = _load_json_dict(data_dir / filename)
        if runtime_payload is not None:
            return runtime_payload
        if bundled_data_dir != data_dir:
            return _load_json_dict(bundled_data_dir / filename)
        return None

    def _dedupe_thesis_cards(cards: list[dict[str, object]]) -> list[dict[str, object]]:
        best_by_key: dict[tuple[str, str, float, float, float, str], tuple[float, float, dict[str, object]]] = {}
        for card in cards:
            instrument = str(card.get("instrument") or "").upper()
            direction = str(card.get("direction") or "").lower()
            entry_key = round(_safe_number(card.get("entry_price"), 0.0), 2)
            target_key = round(_safe_number(card.get("target_price"), 0.0), 2)
            stop_key = round(_safe_number(card.get("stop_price"), 0.0), 2)
            exit_day = as_day(str(card.get("suggested_exit_time") or "")) or str(
                card.get("suggested_exit_time") or ""
            )[:10]
            dedupe_key = (instrument, direction, entry_key, target_key, stop_key, exit_day)
            score_confidence = _safe_number(card.get("confidence_tese_pct"), 0.0)
            score_expected = _safe_number(card.get("expected_financial_pct"), 0.0)
            existing = best_by_key.get(dedupe_key)
            if existing is None or (score_confidence, score_expected) > (existing[0], existing[1]):
                best_by_key[dedupe_key] = (score_confidence, score_expected, card)
        deduped_cards = [entry[2] for entry in best_by_key.values()]
        deduped_cards.sort(
            key=lambda item: (
                _safe_number(item.get("confidence_tese_pct"), 0.0),
                _safe_number(item.get("expected_financial_pct"), 0.0),
            ),
            reverse=True,
        )
        return deduped_cards

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

    historical_cutoff_iso = f"{phase_kickoff_date}T00:00:00+00:00"
    historical_case_study_events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                and_(
                    AuditEvent.event_type == "thesis.case_study.generated",
                    AuditEvent.created_at < historical_cutoff_iso,
                )
            )
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )
    case_study_latest = _load_runtime_or_bundled_json("case_study_latest.json")
    dashboard_seed = _load_runtime_or_bundled_json("dashboard_seed.json")
    if historical_empty and historical_case_study_events:
        expected_values: list[float] = []
        realized_values: list[float] = []
        approved_count = 0
        for event in historical_case_study_events:
            details_dict: dict[str, object] = {}
            try:
                parsed_details = json.loads(event.details) if event.details else {}
                if isinstance(parsed_details, dict):
                    details_dict = parsed_details
            except json.JSONDecodeError:
                details_dict = {}

            selected_case = details_dict.get("selected_case")
            selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
            kpis = selected_case_dict.get("kpis")
            kpis_dict = kpis if isinstance(kpis, dict) else {}
            outcome = selected_case_dict.get("outcome")
            outcome_dict = outcome if isinstance(outcome, dict) else {}
            thesis = selected_case_dict.get("thesis")
            thesis_dict = thesis if isinstance(thesis, dict) else {}

            expected_pct = _safe_number(
                details_dict.get(
                    "expected_financial_pct",
                    kpis_dict.get("expected_financial_pct", thesis_dict.get("expected_financial_pct")),
                ),
                0.0,
            )
            realized_pct = _safe_number(
                details_dict.get(
                    "realized_financial_pct",
                    kpis_dict.get("realized_financial_pct", outcome_dict.get("realized_financial_pct")),
                ),
                0.0,
            )
            expected_values.append(expected_pct)
            realized_values.append(realized_pct)

            success_flag = outcome_dict.get("success")
            if isinstance(success_flag, bool):
                approved_count += 1 if success_flag else 0
            elif realized_pct >= 0.0:
                approved_count += 1

        thesis_count = len(historical_case_study_events)
        historical_analysis_summary = {
            "period_label": f"ate {phase_kickoff_date} (base historica global - case studies consolidados)",
            "thesis_count": thesis_count,
            "backtest_runs": thesis_count,
            "operacoes_simuladas": thesis_count,
            "total_trades": thesis_count,
            "avg_expected_pct": avg(expected_values),
            "avg_win_rate_pct": round((approved_count / thesis_count) * 100, 2) if thesis_count > 0 else 0.0,
            "avg_return_pct": avg(realized_values),
            "approved_count": approved_count,
            "avg_drawdown_pct": 0.0,
            "window_start": as_day(historical_case_study_events[0].created_at),
            "window_end": as_day(historical_case_study_events[-1].created_at),
        }
        historical_empty = False

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
                "period_label": f"ate {phase_kickoff_date} (base historica - case study)",
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

    current_monitor_latest = _load_runtime_or_bundled_json("current_thesis_monitor_latest.json")
    if current_empty and current_monitor_latest is not None:
        theses_payload = current_monitor_latest.get("theses")
        theses_payload_list = (
            [item for item in theses_payload if isinstance(item, dict)]
            if isinstance(theses_payload, list)
            else []
        )
        theses_payload_list = _dedupe_thesis_cards(theses_payload_list)
        generated_at = str(current_monitor_latest.get("generated_at") or "")
        thesis_count = len(theses_payload_list)
        target_hits = sum(
            1 for item in theses_payload_list if str(item.get("monitor_status") or "").lower() == "target_hit"
        )
        stop_alerts = sum(
            1 for item in theses_payload_list if str(item.get("monitor_status") or "").lower() == "stop_alert"
        )
        monitoring_count = sum(
            1 for item in theses_payload_list if str(item.get("monitor_status") or "").lower() == "monitoring"
        )
        avg_expected = avg(
            [_safe_number(item.get("expected_financial_pct")) for item in theses_payload_list],
        )
        avg_unrealized = avg(
            [_safe_number(item.get("unrealized_financial_pct")) for item in theses_payload_list],
        )
        current_simulation_summary = {
            "period_label": f"desde {phase_kickoff_date} (simulacao atual - teses monitoradas)",
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

    thesis_event_types = [
        "thesis.case_study.generated",
        "thesis.current_monitor.generated",
    ]
    thesis_audit_events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                and_(
                    AuditEvent.user_id == user_id,
                    AuditEvent.event_type.in_(thesis_event_types),
                )
            )
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )
    thesis_audit_events_global = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.event_type.in_(thesis_event_types))
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )

    def _maybe_float(value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_audit_details(event: AuditEvent) -> dict[str, object]:
        try:
            parsed = json.loads(event.details) if event.details else {}
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _extract_case_study_expected_pct(details: dict[str, object]) -> float | None:
        expected_pct = _maybe_float(details.get("expected_financial_pct"))
        if expected_pct is not None:
            return expected_pct
        selected_case = details.get("selected_case")
        selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
        kpis = selected_case_dict.get("kpis")
        kpis_dict = kpis if isinstance(kpis, dict) else {}
        thesis = selected_case_dict.get("thesis")
        thesis_dict = thesis if isinstance(thesis, dict) else {}
        return _maybe_float(
            kpis_dict.get("expected_financial_pct"),
        ) or _maybe_float(thesis_dict.get("expected_financial_pct"))

    def _extract_thesis_event_metrics(
        event_type: str,
        details: dict[str, object],
    ) -> tuple[int, int, float | None]:
        theses_payload = details.get("theses")
        theses_payload_list = (
            [item for item in theses_payload if isinstance(item, dict)]
            if isinstance(theses_payload, list)
            else []
        )
        thesis_count = _safe_int(details.get("thesis_count"), 0)
        if thesis_count <= 0 and theses_payload_list:
            thesis_count = len(theses_payload_list)

        success_count = 0
        avg_result_pct: float | None = None

        if event_type == "thesis.case_study.generated":
            thesis_count = max(1, thesis_count)
            avg_result_pct = _maybe_float(details.get("realized_financial_pct"))
            if avg_result_pct is None:
                selected_case = details.get("selected_case")
                if isinstance(selected_case, dict):
                    kpis = selected_case.get("kpis")
                    kpis_dict = kpis if isinstance(kpis, dict) else {}
                    outcome = selected_case.get("outcome")
                    outcome_dict = outcome if isinstance(outcome, dict) else {}
                    avg_result_pct = _maybe_float(
                        kpis_dict.get("realized_financial_pct"),
                    ) or _maybe_float(outcome_dict.get("realized_financial_pct"))
                    success_flag = outcome_dict.get("success")
                    if isinstance(success_flag, bool):
                        success_count = 1 if success_flag else 0
            if success_count == 0:
                success_count = 1 if (avg_result_pct is not None and avg_result_pct >= 0.0) else 0
            return thesis_count, success_count, avg_result_pct

        if event_type == "thesis.current_monitor.generated":
            thesis_count = max(0, thesis_count)
            avg_result_pct = _maybe_float(details.get("avg_unrealized_financial_pct"))
            target_hits = _safe_int(details.get("target_hits"), -1)
            if target_hits >= 0:
                success_count = max(0, min(thesis_count, target_hits))
            elif avg_result_pct is not None and thesis_count > 0:
                success_count = thesis_count if avg_result_pct >= 0.0 else 0
            return thesis_count, success_count, avg_result_pct

        return thesis_count, success_count, avg_result_pct

    def _extract_outcome_counts(
        event_type: str,
        details: dict[str, object],
        tested_count: int,
        avg_result_pct: float | None,
    ) -> tuple[int, int, int, int]:
        if tested_count <= 0:
            return 0, 0, 0, 0

        if event_type == "thesis.case_study.generated":
            selected_case = details.get("selected_case")
            selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
            outcome = selected_case_dict.get("outcome")
            outcome_dict = outcome if isinstance(outcome, dict) else {}
            exit_reason = str(
                details.get("exit_reason")
                or outcome_dict.get("exit_reason")
                or "",
            ).lower()
            if "stop" in exit_reason:
                return 0, tested_count, 0, 0
            if "time" in exit_reason or "window" in exit_reason or "horizon" in exit_reason:
                if avg_result_pct is not None and avg_result_pct < 0.0:
                    return 0, tested_count, 0, 0
                return 0, 0, tested_count, 0
            if "target" in exit_reason:
                if avg_result_pct is not None and avg_result_pct < 0.0:
                    return 0, tested_count, 0, 0
                return tested_count, 0, 0, 0
            if avg_result_pct is None:
                return 0, 0, tested_count, 0
            if avg_result_pct > 0.0:
                return tested_count, 0, 0, 0
            if avg_result_pct < 0.0:
                return 0, tested_count, 0, 0
            return 0, 0, tested_count, 0

        if event_type == "thesis.current_monitor.generated":
            target_hits = max(0, min(tested_count, _safe_int(details.get("target_hits"), 0)))
            stop_alerts = max(0, min(tested_count - target_hits, _safe_int(details.get("stop_alerts"), 0)))
            monitoring_count = max(
                0,
                min(
                    tested_count - target_hits - stop_alerts,
                    _safe_int(details.get("monitoring_count"), 0),
                ),
            )
            time_exit_count = max(0, tested_count - target_hits - stop_alerts - monitoring_count)
            return target_hits, stop_alerts, time_exit_count, monitoring_count

        return 0, 0, tested_count, 0

    thesis_event_counts_by_type: dict[str, int] = defaultdict(int)
    user_total_theses_tested = 0
    for event in thesis_audit_events:
        thesis_event_counts_by_type[event.event_type] += 1
        details_dict = _parse_audit_details(event)
        tested_count, _, _ = _extract_thesis_event_metrics(event.event_type, details_dict)
        user_total_theses_tested += tested_count

    thesis_event_counts_global_by_type: dict[str, int] = defaultdict(int)
    thesis_id_sequence_map: dict[str, list[int]] = defaultdict(list)
    thesis_global_sequence_cursor = 0
    case_study_total_tested = 0
    case_study_success_count = 0
    case_study_expected_weighted_sum = 0.0
    case_study_expected_observations = 0
    case_study_return_weighted_sum = 0.0
    case_study_return_observations = 0
    case_study_window_start: str | None = None
    case_study_window_end: str | None = None
    global_total_theses_tested = 0
    global_success_count = 0
    global_weighted_return_sum = 0.0
    global_return_observations = 0
    global_target_count = 0
    global_stop_count = 0
    global_time_exit_count = 0
    global_open_count = 0
    target_weighted_return_sum = 0.0
    target_return_observations = 0
    stop_weighted_return_sum = 0.0
    stop_return_observations = 0
    time_weighted_return_sum = 0.0
    time_return_observations = 0
    thesis_daily_performance: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "tested": 0,
            "success": 0,
            "return_observations": 0,
            "weighted_return_sum": 0.0,
        },
    )
    for event in thesis_audit_events_global:
        thesis_event_counts_global_by_type[event.event_type] += 1
        details_dict = _parse_audit_details(event)
        tested_count, success_count, avg_result_pct = _extract_thesis_event_metrics(
            event.event_type,
            details_dict,
        )
        if tested_count <= 0:
            continue

        if event.event_type == "thesis.case_study.generated":
            selected_case = details_dict.get("selected_case")
            selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
            thesis = selected_case_dict.get("thesis")
            thesis_dict = thesis if isinstance(thesis, dict) else {}
            thesis_id = str(
                thesis_dict.get("thesis_id")
                or details_dict.get("selected_thesis_id")
                or f"case-study-{event.id}"
            )
            thesis_global_sequence_cursor += 1
            thesis_id_sequence_map[thesis_id].append(thesis_global_sequence_cursor)
            if tested_count > 1:
                thesis_global_sequence_cursor += tested_count - 1
        elif event.event_type == "thesis.current_monitor.generated":
            theses_payload = details_dict.get("theses")
            theses_payload_list = (
                [item for item in theses_payload if isinstance(item, dict)]
                if isinstance(theses_payload, list)
                else []
            )
            if theses_payload_list:
                for thesis_item in theses_payload_list:
                    thesis_global_sequence_cursor += 1
                    thesis_id = str(
                        thesis_item.get("thesis_id") or f"monitor-thesis-{thesis_global_sequence_cursor}"
                    )
                    thesis_id_sequence_map[thesis_id].append(thesis_global_sequence_cursor)
                if tested_count > len(theses_payload_list):
                    thesis_global_sequence_cursor += tested_count - len(theses_payload_list)
            else:
                thesis_global_sequence_cursor += tested_count
        else:
            thesis_global_sequence_cursor += tested_count

        success_count = max(0, min(tested_count, success_count))
        event_day = as_day(event.created_at)
        if event.event_type == "thesis.case_study.generated":
            case_study_total_tested += tested_count
            case_study_success_count += success_count
            expected_pct = _extract_case_study_expected_pct(details_dict)
            if expected_pct is not None:
                case_study_expected_weighted_sum += expected_pct * tested_count
                case_study_expected_observations += tested_count
            if avg_result_pct is not None:
                case_study_return_weighted_sum += avg_result_pct * tested_count
                case_study_return_observations += tested_count
            if event_day:
                if case_study_window_start is None or event_day < case_study_window_start:
                    case_study_window_start = event_day
                if case_study_window_end is None or event_day > case_study_window_end:
                    case_study_window_end = event_day
        global_total_theses_tested += tested_count
        global_success_count += success_count
        target_count, stop_count, time_exit_count, open_count = _extract_outcome_counts(
            event.event_type,
            details_dict,
            tested_count,
            avg_result_pct,
        )
        global_target_count += target_count
        global_stop_count += stop_count
        global_time_exit_count += time_exit_count
        global_open_count += open_count
        if avg_result_pct is not None:
            global_weighted_return_sum += avg_result_pct * tested_count
            global_return_observations += tested_count
            if target_count > 0:
                target_weighted_return_sum += avg_result_pct * target_count
                target_return_observations += target_count
            if stop_count > 0:
                stop_weighted_return_sum += avg_result_pct * stop_count
                stop_return_observations += stop_count
            if time_exit_count > 0:
                time_weighted_return_sum += avg_result_pct * time_exit_count
                time_return_observations += time_exit_count

        if not event_day:
            continue
        day_row = thesis_daily_performance[event_day]
        day_row["tested"] = int(day_row["tested"]) + tested_count
        day_row["success"] = int(day_row["success"]) + success_count
        if avg_result_pct is not None:
            day_row["return_observations"] = int(day_row["return_observations"]) + tested_count
            day_row["weighted_return_sum"] = (
                float(day_row["weighted_return_sum"]) + (avg_result_pct * tested_count)
            )

    sorted_days = sorted(thesis_daily_performance.keys())
    window_start = sorted_days[0] if sorted_days else None
    window_end = sorted_days[-1] if sorted_days else None

    if window_end:
        try:
            last_day: date = datetime.fromisoformat(window_end).date()
        except ValueError:
            last_day = datetime.now(UTC).date()
    else:
        last_day = datetime.now(UTC).date()

    last_3_weeks: list[dict[str, object]] = []
    for index, week_offset in enumerate((2, 1, 0), start=1):
        week_end = last_day - timedelta(days=week_offset * 7)
        week_start = week_end - timedelta(days=6)
        week_series: list[dict[str, object]] = []
        week_tested = 0
        week_success = 0
        week_weighted_return_sum = 0.0
        week_return_observations = 0

        for day_offset in range(7):
            day_value = week_start + timedelta(days=day_offset)
            day_key = day_value.isoformat()
            day_payload = thesis_daily_performance.get(day_key)
            tested = int(day_payload["tested"]) if day_payload is not None else 0
            success = int(day_payload["success"]) if day_payload is not None else 0
            day_return_observations = (
                int(day_payload["return_observations"]) if day_payload is not None else 0
            )
            day_weighted_return_sum = (
                float(day_payload["weighted_return_sum"]) if day_payload is not None else 0.0
            )
            avg_result_pct = (
                round(day_weighted_return_sum / day_return_observations, 4)
                if day_return_observations > 0
                else None
            )

            week_tested += tested
            week_success += success
            week_return_observations += day_return_observations
            week_weighted_return_sum += day_weighted_return_sum
            week_series.append(
                {
                    "day": day_key,
                    "avg_result_pct": avg_result_pct,
                    "tested": tested,
                }
            )

        week_avg_result_pct = (
            round(week_weighted_return_sum / week_return_observations, 4)
            if week_return_observations > 0
            else None
        )
        week_success_rate_pct = (
            round((week_success / week_tested) * 100, 2) if week_tested > 0 else 0.0
        )
        last_3_weeks.append(
            {
                "week_index": index,
                "label": f"Semana {index}",
                "start_day": week_start.isoformat(),
                "end_day": week_end.isoformat(),
                "total_tested": week_tested,
                "success_count": week_success,
                "success_rate_pct": week_success_rate_pct,
                "avg_result_pct": week_avg_result_pct,
                "series": week_series,
            }
        )

    avg_result_pct = (
        round(global_weighted_return_sum / global_return_observations, 4)
        if global_return_observations > 0
        else 0.0
    )
    resolved_theses_count = max(0, global_total_theses_tested - global_open_count)
    target_rate_pct = (
        round((global_target_count / resolved_theses_count) * 100, 2)
        if resolved_theses_count > 0
        else 0.0
    )
    stop_rate_pct = (
        round((global_stop_count / resolved_theses_count) * 100, 2)
        if resolved_theses_count > 0
        else 0.0
    )
    time_exit_rate_pct = (
        round((global_time_exit_count / resolved_theses_count) * 100, 2)
        if resolved_theses_count > 0
        else 0.0
    )
    open_rate_pct = (
        round((global_open_count / global_total_theses_tested) * 100, 2)
        if global_total_theses_tested > 0
        else 0.0
    )

    avg_target_return_pct = (
        round(target_weighted_return_sum / target_return_observations, 4)
        if target_return_observations > 0
        else 0.0
    )
    avg_stop_return_pct = (
        round(stop_weighted_return_sum / stop_return_observations, 4)
        if stop_return_observations > 0
        else 0.0
    )
    avg_time_return_pct = (
        round(time_weighted_return_sum / time_return_observations, 4)
        if time_return_observations > 0
        else 0.0
    )
    expectancy_net_pct = round(
        (target_rate_pct / 100.0) * avg_target_return_pct
        + (stop_rate_pct / 100.0) * avg_stop_return_pct
        + (time_exit_rate_pct / 100.0) * avg_time_return_pct,
        4,
    )
    success_rate_pct = (
        round((global_success_count / global_total_theses_tested) * 100, 2)
        if global_total_theses_tested > 0
        else 0.0
    )

    thesis_history_overview: dict[str, object] = {
        "total_tested": int(global_total_theses_tested),
        "success_count": int(global_success_count),
        "success_rate_pct": success_rate_pct,
        "avg_result_pct": avg_result_pct,
        "expectancy_net_pct": expectancy_net_pct,
        "target_rate_pct": target_rate_pct,
        "stop_rate_pct": stop_rate_pct,
        "time_exit_rate_pct": time_exit_rate_pct,
        "open_rate_pct": open_rate_pct,
        "resolved_count": int(resolved_theses_count),
        "open_count": int(global_open_count),
        "avg_target_return_pct": avg_target_return_pct,
        "avg_stop_return_pct": avg_stop_return_pct,
        "avg_time_return_pct": avg_time_return_pct,
        "window_start": window_start,
        "window_end": window_end,
        "last_3_weeks": last_3_weeks,
        "event_count": len(thesis_audit_events),
        "global_event_count": len(thesis_audit_events_global),
        "global_total_tested": int(global_total_theses_tested),
        "user_total_tested": int(user_total_theses_tested),
        "sources": {
            "case_study_runs": int(thesis_event_counts_global_by_type.get("thesis.case_study.generated", 0)),
            "current_monitor_runs": int(
                thesis_event_counts_global_by_type.get("thesis.current_monitor.generated", 0)
            ),
        },
    }

    if case_study_total_tested > 0:
        case_study_avg_expected_pct = (
            round(case_study_expected_weighted_sum / case_study_expected_observations, 4)
            if case_study_expected_observations > 0
            else 0.0
        )
        case_study_avg_return_pct = (
            round(case_study_return_weighted_sum / case_study_return_observations, 4)
            if case_study_return_observations > 0
            else 0.0
        )
        case_study_win_rate_pct = round(
            (case_study_success_count / case_study_total_tested) * 100,
            2,
        )
        historical_analysis_summary = {
            "period_label": "historico acumulado (exercicio continuo)",
            "thesis_count": int(case_study_total_tested),
            "backtest_runs": int(case_study_total_tested),
            "operacoes_simuladas": int(case_study_total_tested),
            "total_trades": int(case_study_total_tested),
            "avg_expected_pct": case_study_avg_expected_pct,
            "avg_win_rate_pct": case_study_win_rate_pct,
            "avg_return_pct": case_study_avg_return_pct,
            "approved_count": int(case_study_success_count),
            "avg_drawdown_pct": 0.0,
            "window_start": case_study_window_start,
            "window_end": case_study_window_end,
        }

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

    def _append_case_study_operation(
        selected_case_dict: dict[str, object],
        *,
        fallback_raised_at: str = "",
    ) -> int:
        thesis = selected_case_dict.get("thesis")
        thesis_dict = thesis if isinstance(thesis, dict) else {}
        if not thesis_dict:
            return 0
        operation = selected_case_dict.get("structured_operation")
        operation_dict = operation if isinstance(operation, dict) else {}
        outcome = selected_case_dict.get("outcome")
        outcome_dict = outcome if isinstance(outcome, dict) else {}
        monitoring_timeline = selected_case_dict.get("monitoring_timeline")
        monitoring_timeline_list = (
            [event for event in monitoring_timeline if isinstance(event, dict)]
            if isinstance(monitoring_timeline, list)
            else []
        )
        direction = str(thesis_dict.get("direction") or "").lower()
        if direction == "bullish":
            operation_side = "Compra"
        elif direction == "bearish":
            operation_side = "Venda"
        else:
            operation_side = "Neutra"
        exit_reason = str(outcome_dict.get("exit_reason") or "").lower()
        entry_time = (
            selected_case_dict.get("suggested_entry_time")
            or selected_case_dict.get("thesis_raised_at")
            or thesis_dict.get("entry_time")
            or fallback_raised_at
        )
        exit_time = (
            outcome_dict.get("exit_time")
            or _extract_exit_datetime(
                monitoring_timeline_list,
                selected_case_dict.get("suggested_exit_time"),
            )
        )
        duration_days = _duration_days(entry_time, exit_time)
        realized_pct = round(
            _safe_number(
                outcome_dict.get("realized_financial_pct"),
                selected_case_dict.get("kpis", {}).get("realized_financial_pct")
                if isinstance(selected_case_dict.get("kpis"), dict)
                else 0.0,
            ),
            4,
        )
        if "stop" in exit_reason or realized_pct < 0.0:
            outcome_label = "Stop/Protecao"
        elif "time" in exit_reason or "window" in exit_reason:
            outcome_label = "Tempo"
        elif "target" in exit_reason or realized_pct > 0.0:
            outcome_label = "Alvo"
        else:
            outcome_label = "Encerrada"
        strategy_name = str(
            operation_dict.get("strategy_name") or operation_dict.get("strategy_id") or "n/d"
        )
        max_gain_pct = round(_safe_number(operation_dict.get("max_gain_pct"), 0.0), 4)
        max_loss_pct = round(_safe_number(operation_dict.get("max_loss_pct"), 0.0), 4)
        suggested_exit_time = str(selected_case_dict.get("suggested_exit_time") or "")
        expected_result_pct = round(
            _safe_number(
                thesis_dict.get("expected_financial_pct"),
                selected_case_dict.get("kpis", {}).get("expected_financial_pct")
                if isinstance(selected_case_dict.get("kpis"), dict)
                else 0.0,
            ),
            4,
        )
        entry_price = round(_safe_number(thesis_dict.get("entry_price"), 0.0), 4)
        target_price = round(_safe_number(thesis_dict.get("target_price"), 0.0), 4)
        stop_price = round(_safe_number(thesis_dict.get("stop_price"), 0.0), 4)
        supporting_signals = thesis_dict.get("supporting_signals")
        supporting_signals_list = (
            [str(value) for value in supporting_signals if isinstance(value, (str, int, float))]
            if isinstance(supporting_signals, list)
            else []
        )
        thesis_reason = _build_thesis_candidate_reason(
            instrument=str(thesis_dict.get("instrument") or ""),
            reason_category="case study historico",
            direction=str(thesis_dict.get("direction") or ""),
            confidence_pct=round(_safe_number(thesis_dict.get("confidence_tese_pct"), 0.0), 4),
            technical_support_pct=round(_safe_number(thesis_dict.get("technical_support_pct"), 0.0), 4),
            fundamental_support_pct=round(_safe_number(thesis_dict.get("fundamental_support_pct"), 0.0), 4),
            news_support_pct=round(_safe_number(thesis_dict.get("news_support_pct"), 0.0), 4),
            why_signals=supporting_signals_list,
        )
        thesis_id_value = str(thesis_dict.get("thesis_id") or f"case-study-{len(thesis_open_operations) + 1}")
        thesis_open_operations.append(
            {
                "phase": "historico",
                "thesis_number": len(thesis_open_operations) + 1,
                "thesis_id": thesis_id_value,
                "thesis_raised_at": str(
                    selected_case_dict.get("thesis_raised_at")
                    or thesis_dict.get("entry_time")
                    or fallback_raised_at
                    or ""
                ),
                "action": str(thesis_dict.get("instrument") or "n/d"),
                "thesis_reason": thesis_reason,
                "expected_result_pct": expected_result_pct,
                "operation_plan": _build_operation_plan_text(
                    direction=direction,
                    operation_side=operation_side,
                    exit_day=as_day(suggested_exit_time) or suggested_exit_time or "-",
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_price=stop_price,
                    expected_result_pct=expected_result_pct,
                ),
                "structured_operation": (
                    f"{strategy_name} | ganho max {max_gain_pct:.2f}% | perda max {max_loss_pct:.2f}%"
                ),
                "entry_price_brl": entry_price,
                "exit_rule": (
                    f"Sai se subir para R$ {target_price:.2f} ou cair para R$ {stop_price:.2f}"
                ),
                "status": "Fechada",
                "outcome": outcome_label,
                "moment_result_pct": realized_pct,
                "duration_days": duration_days,
                "learning_note": _build_learning_note(
                    direction=direction,
                    status="Fechada",
                    outcome=outcome_label,
                    expected_result_pct=expected_result_pct,
                    realized_result_pct=realized_pct,
                ),
            }
        )
        return 1

    def _append_case_study_operation_from_event(
        details_dict: dict[str, object],
        *,
        fallback_raised_at: str = "",
    ) -> int:
        thesis_id_value = str(details_dict.get("selected_thesis_id") or "").strip()
        if not thesis_id_value:
            return 0

        parts = thesis_id_value.split("-")
        instrument = parts[1] if len(parts) >= 2 else "n/d"
        direction = parts[2].lower() if len(parts) >= 3 else ""
        if direction == "bullish":
            operation_side = "Compra"
        elif direction == "bearish":
            operation_side = "Venda"
        else:
            operation_side = "Neutra"

        expected_result_pct = round(_safe_number(details_dict.get("expected_financial_pct"), 0.0), 4)
        realized_pct = round(_safe_number(details_dict.get("realized_financial_pct"), 0.0), 4)
        confidence_pct = round(_safe_number(details_dict.get("confidence_tese_pct"), 0.0), 4)

        strategy_id = str(details_dict.get("strategy_id") or "n/d")
        strategy_name = strategy_id.replace("_", " ").title() if strategy_id and strategy_id != "n/d" else "n/d"
        if realized_pct < 0.0:
            outcome_label = "Stop/Protecao"
        elif realized_pct > 0.0:
            outcome_label = "Alvo"
        else:
            outcome_label = "Tempo"

        thesis_reason = (
            f"Tese historica {operation_side.lower()} para {instrument} no exercicio continuo. "
            f"Registro legado com confianca {confidence_pct:.2f}% e retorno esperado {expected_result_pct:.2f}%."
        )
        operation_plan = (
            f"{operation_side} ate - (case study historico continuo; "
            "detalhes completos de prazo/preco nao persistidos no evento legado)"
        )

        thesis_open_operations.append(
            {
                "phase": "historico",
                "thesis_number": len(thesis_open_operations) + 1,
                "thesis_id": thesis_id_value,
                "thesis_raised_at": str(fallback_raised_at or ""),
                "action": instrument,
                "thesis_reason": thesis_reason,
                "expected_result_pct": expected_result_pct,
                "operation_plan": operation_plan,
                "structured_operation": f"{strategy_name} | ganho max n/d | perda max n/d",
                "entry_price_brl": None,
                "exit_rule": "Sai por alvo/stop/tempo da estrategia (detalhe de preco indisponivel no legado)",
                "status": "Fechada",
                "outcome": outcome_label,
                "moment_result_pct": realized_pct,
                "duration_days": None,
                "learning_note": _build_learning_note(
                    direction=direction,
                    status="Fechada",
                    outcome=outcome_label,
                    expected_result_pct=expected_result_pct,
                    realized_result_pct=realized_pct,
                ),
            }
        )
        return 1

    historical_rows_added = 0
    case_study_events_global = [
        event
        for event in thesis_audit_events_global
        if event.event_type == "thesis.case_study.generated"
    ]
    for event in case_study_events_global:
        details_dict = _parse_audit_details(event)
        selected_case = details_dict.get("selected_case")
        selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
        if selected_case_dict:
            historical_rows_added += _append_case_study_operation(
                selected_case_dict,
                fallback_raised_at=str(event.created_at),
            )
        else:
            historical_rows_added += _append_case_study_operation_from_event(
                details_dict,
                fallback_raised_at=str(event.created_at),
            )

    if historical_rows_added == 0 and case_study_latest is not None:
        selected_case = case_study_latest.get("selected_case")
        selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
        if selected_case_dict:
            historical_rows_added += _append_case_study_operation(selected_case_dict)

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
            max_gain_pct = round(_safe_number(operation_dict.get("max_gain_pct"), 0.0), 4)
            max_loss_pct = round(_safe_number(operation_dict.get("max_loss_pct"), 0.0), 4)
            target_price = round(_safe_number(item.get("target_price"), 0.0), 4)
            stop_price = round(_safe_number(item.get("stop_price"), 0.0), 4)
            entry_price = round(_safe_number(item.get("entry_price"), 0.0), 4)
            suggested_exit_time = str(item.get("suggested_exit_time") or "")
            expected_result_pct = round(
                _safe_number(item.get("expected_financial_pct"), 0.0),
                4,
            )

            why_thesis = item.get("why_thesis")
            why_list = (
                [str(value) for value in why_thesis if isinstance(value, (str, int, float))]
                if isinstance(why_thesis, list)
                else []
            )
            thesis_reason = str(item.get("reason_category") or "")
            thesis_reason = _build_thesis_candidate_reason(
                instrument=str(item.get("instrument") or ""),
                reason_category=thesis_reason or "monitoramento atual",
                direction=str(item.get("direction") or ""),
                confidence_pct=round(_safe_number(item.get("confidence_tese_pct"), 0.0), 4),
                technical_support_pct=round(_safe_number(item.get("technical_support_pct"), 0.0), 4),
                fundamental_support_pct=round(_safe_number(item.get("fundamental_support_pct"), 0.0), 4),
                news_support_pct=round(_safe_number(item.get("news_support_pct"), 0.0), 4),
                why_signals=why_list,
            )

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
            status_label = "Aberta"
            if monitor_status in {"closed", "encerrada", "finished", "exited"}:
                status_label = "Fechada"
            has_target_event = (
                monitor_status == "target_hit"
                or any(
                    "target" in str(event.get("event_type") or "").lower()
                    for event in monitoring_events_list
                )
            )
            has_stop_event = (
                monitor_status == "stop_alert"
                or any(
                    any(
                        token in str(event.get("event_type") or "").lower()
                        for token in ("stop", "range_break")
                    )
                    for event in monitoring_events_list
                )
            )
            if status_label == "Aberta":
                if monitor_status == "target_hit" or has_target_event:
                    outcome_label = "Alvo atingido (avaliar saida)"
                elif monitor_status == "stop_alert" or has_stop_event:
                    outcome_label = "Alerta de stop"
                else:
                    outcome_label = "Em monitoramento"
            else:
                if has_target_event:
                    outcome_label = "Alvo"
                elif has_stop_event:
                    outcome_label = "Stop/Protecao"
                elif has_exit_event:
                    outcome_label = "Tempo"
                else:
                    outcome_label = "Encerrada"
            entry_time = item.get("suggested_entry_time") or item.get("thesis_raised_at")
            exit_time = (
                _extract_exit_datetime(
                    monitoring_events_list,
                    item.get("latest_event_time"),
                )
                if status_label == "Fechada"
                else None
            )
            duration_days = _duration_days(entry_time, exit_time) if status_label == "Fechada" else None

            thesis_open_operations.append(
                {
                    "phase": "pos_go_live",
                    "thesis_number": len(thesis_open_operations) + 1,
                    "thesis_id": str(item.get("thesis_id") or f"Tese {index + 1}"),
                    "thesis_raised_at": str(
                        item.get("thesis_raised_at")
                        or item.get("suggested_entry_time")
                        or ""
                    ),
                    "action": str(item.get("instrument") or "n/d"),
                    "thesis_reason": thesis_reason,
                    "expected_result_pct": expected_result_pct,
                    "operation_plan": _build_operation_plan_text(
                        direction=direction,
                        operation_side=operation_side,
                        exit_day=as_day(suggested_exit_time) or suggested_exit_time or "-",
                        entry_price=entry_price,
                        target_price=target_price,
                        stop_price=stop_price,
                        expected_result_pct=expected_result_pct,
                    ),
                    "structured_operation": (
                        f"{strategy_name} | ganho max {max_gain_pct:.2f}% | perda max {max_loss_pct:.2f}%"
                    ),
                    "entry_price_brl": entry_price,
                    "exit_rule": f"Sai se subir para R$ {target_price:.2f} ou cair para R$ {stop_price:.2f}",
                    "status": status_label,
                    "outcome": outcome_label,
                    "moment_result_pct": round(
                        _safe_number(item.get("unrealized_financial_pct"), 0.0),
                        4,
                    ),
                    "duration_days": duration_days,
                    "learning_note": _build_learning_note(
                        direction=direction,
                        status=status_label,
                        outcome=outcome_label,
                        expected_result_pct=expected_result_pct,
                        realized_result_pct=round(
                            _safe_number(item.get("unrealized_financial_pct"), 0.0),
                            4,
                        ),
                    ),
                }
            )

    if (
        dashboard_seed is not None
        and _safe_int(historical_analysis_summary.get("thesis_count")) == 0
        and _safe_int(current_simulation_summary.get("thesis_count")) == 0
        and _safe_int(thesis_history_overview.get("total_tested")) == 0
        and not thesis_open_operations
    ):
        seed_historical = dashboard_seed.get("historical_analysis_summary")
        if isinstance(seed_historical, dict):
            historical_analysis_summary = cast(dict[str, object], seed_historical)

        seed_current = dashboard_seed.get("current_simulation_summary")
        if isinstance(seed_current, dict):
            current_simulation_summary = cast(dict[str, object], seed_current)

        seed_current_daily = dashboard_seed.get("current_simulation_daily")
        if isinstance(seed_current_daily, list):
            current_simulation_daily = [item for item in seed_current_daily if isinstance(item, dict)]

        seed_overview = dashboard_seed.get("thesis_history_overview")
        if isinstance(seed_overview, dict):
            thesis_history_overview = cast(dict[str, object], seed_overview)

        seed_exec_summary = dashboard_seed.get("thesis_executive_summary")
        if isinstance(seed_exec_summary, dict):
            thesis_executive_summary = cast(dict[str, object], seed_exec_summary)

        seed_open_operations = dashboard_seed.get("thesis_open_operations")
        if isinstance(seed_open_operations, list):
            thesis_open_operations = [item for item in seed_open_operations if isinstance(item, dict)]

    for row in thesis_open_operations:
        if not str(row.get("phase") or "").strip():
            operation_plan_hint = str(row.get("operation_plan") or "").lower()
            thesis_day_hint = str(row.get("thesis_raised_at") or "")[:10]
            if "case study historico" in operation_plan_hint:
                row["phase"] = "historico"
            elif thesis_day_hint and thesis_day_hint < phase_kickoff_date:
                row["phase"] = "historico"
            else:
                row["phase"] = "pos_go_live"

        if not str(row.get("learning_note") or "").strip():
            direction_hint = str(row.get("direction") or "").lower()
            operation_plan_hint = str(row.get("operation_plan") or "").lower()
            if not direction_hint:
                if "neutra" in operation_plan_hint or "faixa" in operation_plan_hint:
                    direction_hint = "range"
                elif "compra" in operation_plan_hint:
                    direction_hint = "bullish"
                elif "venda" in operation_plan_hint:
                    direction_hint = "bearish"
                else:
                    direction_hint = "mixed"
            row["learning_note"] = _build_learning_note(
                direction=direction_hint,
                status=str(row.get("status") or ""),
                outcome=str(row.get("outcome") or ""),
                expected_result_pct=_safe_number(row.get("expected_result_pct"), 0.0),
                realized_result_pct=_safe_number(row.get("moment_result_pct"), 0.0),
            )

    total_tested_for_numbering = _safe_int(
        thesis_history_overview.get("total_tested"),
        len(thesis_open_operations),
    )
    fallback_start_number = max(1, total_tested_for_numbering - len(thesis_open_operations) + 1)
    for index, row in enumerate(thesis_open_operations):
        row["thesis_number"] = fallback_start_number + index

    resolved_durations = [
        float(row["duration_days"])
        for row in thesis_open_operations
        if row.get("status") == "Fechada" and isinstance(row.get("duration_days"), (int, float))
    ]
    avg_resolution_days = (
        round(sum(resolved_durations) / len(resolved_durations), 2) if resolved_durations else None
    )
    thesis_history_overview["avg_resolution_days"] = avg_resolution_days
    thesis_history_overview["resolution_sample_count"] = len(resolved_durations)

    return DashboardResponse(
        user_id=user_id,
        investor_profile=profile.investor_profile if profile is not None else None,
        open_positions=[
            {
                "instrument": position.instrument,
                **asset_class_payload(position.instrument),
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
                **asset_class_payload(signal.instrument),
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
                **asset_class_payload(order.instrument),
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
                **asset_class_payload(article.instrument),
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
        market_coverage=coverage,
        data_quality_gate=cast(dict[str, object], data_quality_gate_payload),
        phase_kickoff_date=phase_kickoff_date,
        historical_analysis_summary=historical_analysis_summary,
        current_simulation_summary=current_simulation_summary,
        current_simulation_daily=current_simulation_daily,
        thesis_history_overview=thesis_history_overview,
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

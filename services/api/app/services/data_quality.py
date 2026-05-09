from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict

from app.models import FundamentalSnapshot, MarketTick, NewsArticle
from app.services.asset_classes import classify_instrument
from app.services.feed_health import provider_feed_health
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class DataQualityThresholds(TypedDict):
    market_max_lag_seconds: int
    market_min_fresh_coverage_pct: float
    fundamentals_min_coverage_pct: float
    fundamentals_max_staleness_days: int
    fundamentals_min_fresh_coverage_pct: float
    news_lookback_days: int
    news_min_coverage_pct: float
    max_critical_providers: int
    max_no_data_providers: int


class DataQualityCheck(TypedDict):
    check_id: str
    label: str
    status: Literal["pass", "fail"]
    comparator: Literal[">=", "<="]
    actual_value: float
    target_value: float
    details: str


class DataQualitySummary(TypedDict):
    gate_status: Literal["pass", "fail"]
    passed_checks: int
    failed_checks: int
    total_checks: int
    quality_score_pct: float


class DataQualityScope(TypedDict):
    target_instrument_count: int
    target_instruments_sample: list[str]
    sample_truncated: bool


class DataQualityMarketStats(TypedDict):
    covered_instrument_count: int
    missing_instrument_count: int
    fresh_instrument_count: int
    stale_instrument_count: int
    coverage_pct: float
    fresh_coverage_pct: float
    max_lag_seconds: float
    missing_instruments_sample: list[str]


class DataQualityFundamentalStats(TypedDict):
    covered_instrument_count: int
    missing_instrument_count: int
    fresh_instrument_count: int
    stale_instrument_count: int
    coverage_pct: float
    fresh_coverage_pct: float
    missing_instruments_sample: list[str]
    stale_instruments_sample: list[str]


class DataQualityNewsStats(TypedDict):
    lookback_days: int
    instruments_with_recent_news: int
    recent_news_coverage_pct: float
    articles_in_window: int
    source_count: int
    missing_instruments_sample: list[str]


class DataQualityProviderHealth(TypedDict):
    provider_count: int
    critical_count: int
    warning_count: int
    no_data_count: int


class DataQualityGateSnapshot(TypedDict):
    generated_at: str
    scope: DataQualityScope
    thresholds: DataQualityThresholds
    summary: DataQualitySummary
    checks: list[DataQualityCheck]
    market: DataQualityMarketStats
    fundamentals: DataQualityFundamentalStats
    news: DataQualityNewsStats
    provider_health: DataQualityProviderHealth
    recommended_actions: list[str]


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _pct(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 4)


def _sample(values: set[str], *, limit: int = 20) -> list[str]:
    return sorted(values)[:limit]


def _fundamental_scope(scope: list[str]) -> list[str]:
    return [
        instrument
        for instrument in scope
        if classify_instrument(instrument) in {"stock", "fii", "etf", "bdr"}
    ]


def _market_fresh_limit_seconds(instrument: str, default_limit_seconds: int) -> int:
    if classify_instrument(instrument) in {"stock", "fii", "etf", "bdr"}:
        return max(default_limit_seconds, 4 * 24 * 60 * 60)
    return default_limit_seconds


def _as_scope(
    db: Session,
    instruments: list[str] | None,
    *,
    max_default_scope_size: int,
) -> tuple[list[str], bool]:
    if instruments is not None:
        normalized = list(
            dict.fromkeys(item.upper().strip() for item in instruments if item.strip())
        )
        if not normalized:
            raise ValueError("instruments informado, mas sem tickers validos.")
        return normalized, False
    if max_default_scope_size <= 0:
        raise ValueError("max_default_scope_size deve ser maior que zero.")
    rows = list(
        db.scalars(
            select(MarketTick.instrument)
            .distinct()
            .order_by(MarketTick.instrument.asc())
            .limit(max_default_scope_size + 1)
        )
    )
    truncated = len(rows) > max_default_scope_size
    selected = rows[:max_default_scope_size] if truncated else rows
    return [item.upper() for item in selected], truncated


def _check(
    *,
    check_id: str,
    label: str,
    comparator: Literal[">=", "<="],
    actual_value: float,
    target_value: float,
    details: str,
) -> DataQualityCheck:
    if comparator == ">=":
        passed = actual_value >= target_value
    else:
        passed = actual_value <= target_value
    return {
        "check_id": check_id,
        "label": label,
        "status": "pass" if passed else "fail",
        "comparator": comparator,
        "actual_value": round(actual_value, 4),
        "target_value": round(target_value, 4),
        "details": details,
    }


def _recommended_actions(failed_check_ids: set[str]) -> list[str]:
    recommendations: list[str] = []
    if "market_fresh_coverage_pct" in failed_check_ids:
        recommendations.append(
            "Executar ingestao intraday por lote para o universo alvo e validar latencia."
        )
    if "provider_critical_count" in failed_check_ids:
        recommendations.append(
            "Investigar provider critico e revisar failover/token antes do proximo ciclo."
        )
    if "provider_no_data_count" in failed_check_ids:
        recommendations.append(
            "Corrigir provider sem dados e confirmar ultimo tick por ativo alvo."
        )
    if "fundamentals_coverage_pct" in failed_check_ids:
        recommendations.append(
            "Sincronizar fundamentos externos para ativos sem snapshot (modo only-missing)."
        )
    if "fundamentals_fresh_coverage_pct" in failed_check_ids:
        recommendations.append(
            "Atualizar snapshots fundamentalistas vencidos e revisar janela de staleness."
        )
    if "news_recent_coverage_pct" in failed_check_ids:
        recommendations.append(
            "Reprocessar noticias no periodo e ampliar cobertura de ativos sem eventos recentes."
        )
    return recommendations


def build_data_quality_gate_snapshot(
    db: Session,
    *,
    instruments: list[str] | None = None,
    max_default_scope_size: int = 2000,
    market_max_lag_seconds: int = 1800,
    market_min_fresh_coverage_pct: float = 95.0,
    fundamentals_min_coverage_pct: float = 90.0,
    fundamentals_max_staleness_days: int = 1,
    fundamentals_min_fresh_coverage_pct: float = 90.0,
    news_lookback_days: int = 7,
    news_min_coverage_pct: float = 60.0,
    max_critical_providers: int = 0,
    max_no_data_providers: int = 0,
    include_provider_health: bool = True,
) -> DataQualityGateSnapshot:
    if market_max_lag_seconds <= 0:
        raise ValueError("market_max_lag_seconds deve ser maior que zero.")
    if fundamentals_max_staleness_days < 0:
        raise ValueError("fundamentals_max_staleness_days nao pode ser negativo.")
    if news_lookback_days <= 0:
        raise ValueError("news_lookback_days deve ser maior que zero.")

    scope, default_scope_truncated = _as_scope(
        db,
        instruments,
        max_default_scope_size=max_default_scope_size,
    )
    scope_set = set(scope)
    fundamental_scope = _fundamental_scope(scope)
    fundamental_scope_set = set(fundamental_scope)
    now = datetime.now(UTC)
    sample_limit = 20

    latest_market_rows = {
        str(row[0]).upper(): str(row[1])
        for row in db.execute(
            select(MarketTick.instrument, func.max(MarketTick.ingest_time))
            .where(MarketTick.instrument.in_(scope_set))
            .group_by(MarketTick.instrument)
        ).all()
    }
    covered_market_set = set(latest_market_rows.keys())
    missing_market_set = scope_set - covered_market_set
    max_lag_seconds = 0.0
    fresh_market_count = 0
    for instrument, ingest_time in latest_market_rows.items():
        lag_seconds = max(0.0, (now - _parse_iso_datetime(ingest_time)).total_seconds())
        fresh_limit_seconds = _market_fresh_limit_seconds(
            instrument,
            market_max_lag_seconds,
        )
        if lag_seconds <= float(fresh_limit_seconds):
            fresh_market_count += 1
        if lag_seconds > max_lag_seconds:
            max_lag_seconds = lag_seconds
    market_coverage_pct = _pct(len(covered_market_set), len(scope_set))
    market_fresh_coverage_pct = _pct(fresh_market_count, len(scope_set))

    latest_fundamental_rows = {
        str(row[0]).upper(): str(row[1])
        for row in db.execute(
            select(FundamentalSnapshot.instrument, func.max(FundamentalSnapshot.availability_time))
            .where(FundamentalSnapshot.instrument.in_(fundamental_scope_set))
            .group_by(FundamentalSnapshot.instrument)
        ).all()
    }
    covered_fundamental_set = set(latest_fundamental_rows.keys())
    missing_fundamental_set = fundamental_scope_set - covered_fundamental_set
    stale_fundamental_set: set[str] = set()
    fresh_fundamental_count = 0
    for instrument, availability_time in latest_fundamental_rows.items():
        staleness_days = max(0, (now - _parse_iso_datetime(availability_time)).days)
        if staleness_days <= fundamentals_max_staleness_days:
            fresh_fundamental_count += 1
        else:
            stale_fundamental_set.add(instrument)
    fundamentals_coverage_pct = (
        _pct(len(covered_fundamental_set), len(fundamental_scope_set))
        if fundamental_scope_set
        else 100.0
    )
    fundamentals_fresh_coverage_pct = (
        _pct(fresh_fundamental_count, len(fundamental_scope_set))
        if fundamental_scope_set
        else 100.0
    )

    lookback_start = now - timedelta(days=news_lookback_days)
    lookback_start_iso = lookback_start.replace(microsecond=0).isoformat()
    recent_news_rows = list(
        db.execute(
            select(NewsArticle.instrument, func.max(NewsArticle.published_at))
            .where(NewsArticle.instrument.in_(scope_set))
            .where(NewsArticle.published_at >= lookback_start_iso)
            .group_by(NewsArticle.instrument)
        ).all()
    )
    recent_news_instruments = {str(row[0]).upper() for row in recent_news_rows}
    missing_news_set = scope_set - recent_news_instruments
    news_coverage_pct = _pct(len(recent_news_instruments), len(scope_set))
    news_articles_in_window = int(
        db.scalar(
            select(func.count())
            .select_from(NewsArticle)
            .where(NewsArticle.instrument.in_(scope_set))
            .where(NewsArticle.published_at >= lookback_start_iso)
        )
        or 0
    )
    news_source_count = int(
        db.scalar(
            select(func.count(func.distinct(NewsArticle.source_name)))
            .where(NewsArticle.instrument.in_(scope_set))
            .where(NewsArticle.published_at >= lookback_start_iso)
        )
        or 0
    )

    providers = []
    critical_provider_count = 0
    warning_provider_count = 0
    no_data_provider_count = 0
    if include_provider_health:
        providers = provider_feed_health(
            db,
            stale_threshold_seconds=market_max_lag_seconds,
            latency_threshold_seconds=max(1, min(3600, market_max_lag_seconds)),
        )
        critical_provider_count = sum(
            1 for row in providers if row["health_status"] == "critical"
        )
        warning_provider_count = sum(1 for row in providers if row["health_status"] == "warning")
        no_data_provider_count = sum(1 for row in providers if row["health_status"] == "no_data")

    checks: list[DataQualityCheck] = [
        _check(
            check_id="market_fresh_coverage_pct",
            label="Market fresh coverage",
            comparator=">=",
            actual_value=market_fresh_coverage_pct,
            target_value=market_min_fresh_coverage_pct,
            details=(
                f"fresh={fresh_market_count}/{len(scope_set)} "
                "com janela por frente (B3 diario, cripto intraday)"
            ),
        ),
        _check(
            check_id="provider_critical_count",
            label="Provider critical count",
            comparator="<=",
            actual_value=float(critical_provider_count),
            target_value=float(max_critical_providers),
            details=f"providers_criticos={critical_provider_count}",
        ),
        _check(
            check_id="provider_no_data_count",
            label="Provider no-data count",
            comparator="<=",
            actual_value=float(no_data_provider_count),
            target_value=float(max_no_data_providers),
            details=f"providers_sem_dados={no_data_provider_count}",
        ),
        _check(
            check_id="fundamentals_coverage_pct",
            label="Fundamentals coverage",
            comparator=">=",
            actual_value=fundamentals_coverage_pct,
            target_value=fundamentals_min_coverage_pct,
            details=(
                f"com_snapshot={len(covered_fundamental_set)}/{len(fundamental_scope_set)} "
                "no universo com fundamentos aplicaveis"
            ),
        ),
        _check(
            check_id="fundamentals_fresh_coverage_pct",
            label="Fundamentals fresh coverage",
            comparator=">=",
            actual_value=fundamentals_fresh_coverage_pct,
            target_value=fundamentals_min_fresh_coverage_pct,
            details=(
                f"frescos={fresh_fundamental_count}/{len(fundamental_scope_set)} "
                f"com staleness <= {fundamentals_max_staleness_days} dia(s)"
            ),
        ),
        _check(
            check_id="news_recent_coverage_pct",
            label="News recent coverage",
            comparator=">=",
            actual_value=news_coverage_pct,
            target_value=news_min_coverage_pct,
            details=(
                f"ativos_com_noticia={len(recent_news_instruments)}/{len(scope_set)} "
                f"na janela de {news_lookback_days} dia(s)"
            ),
        ),
    ]
    passed_checks = sum(1 for check in checks if check["status"] == "pass")
    failed_checks = len(checks) - passed_checks
    quality_score_pct = _pct(passed_checks, len(checks))
    gate_status: Literal["pass", "fail"] = "pass" if failed_checks == 0 else "fail"
    failed_check_ids = {check["check_id"] for check in checks if check["status"] == "fail"}

    return {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "scope": {
            "target_instrument_count": len(scope_set),
            "target_instruments_sample": scope[:sample_limit],
            "sample_truncated": default_scope_truncated or len(scope) > sample_limit,
        },
        "thresholds": {
            "market_max_lag_seconds": market_max_lag_seconds,
            "market_min_fresh_coverage_pct": market_min_fresh_coverage_pct,
            "fundamentals_min_coverage_pct": fundamentals_min_coverage_pct,
            "fundamentals_max_staleness_days": fundamentals_max_staleness_days,
            "fundamentals_min_fresh_coverage_pct": fundamentals_min_fresh_coverage_pct,
            "news_lookback_days": news_lookback_days,
            "news_min_coverage_pct": news_min_coverage_pct,
            "max_critical_providers": max_critical_providers,
            "max_no_data_providers": max_no_data_providers,
        },
        "summary": {
            "gate_status": gate_status,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_checks": len(checks),
            "quality_score_pct": quality_score_pct,
        },
        "checks": checks,
        "market": {
            "covered_instrument_count": len(covered_market_set),
            "missing_instrument_count": len(missing_market_set),
            "fresh_instrument_count": fresh_market_count,
            "stale_instrument_count": max(0, len(covered_market_set) - fresh_market_count),
            "coverage_pct": market_coverage_pct,
            "fresh_coverage_pct": market_fresh_coverage_pct,
            "max_lag_seconds": round(max_lag_seconds, 4),
            "missing_instruments_sample": _sample(missing_market_set, limit=sample_limit),
        },
        "fundamentals": {
            "covered_instrument_count": len(covered_fundamental_set),
            "missing_instrument_count": len(missing_fundamental_set),
            "fresh_instrument_count": fresh_fundamental_count,
            "stale_instrument_count": max(
                0,
                len(covered_fundamental_set) - fresh_fundamental_count,
            ),
            "coverage_pct": fundamentals_coverage_pct,
            "fresh_coverage_pct": fundamentals_fresh_coverage_pct,
            "missing_instruments_sample": _sample(missing_fundamental_set, limit=sample_limit),
            "stale_instruments_sample": _sample(stale_fundamental_set, limit=sample_limit),
        },
        "news": {
            "lookback_days": news_lookback_days,
            "instruments_with_recent_news": len(recent_news_instruments),
            "recent_news_coverage_pct": news_coverage_pct,
            "articles_in_window": news_articles_in_window,
            "source_count": news_source_count,
            "missing_instruments_sample": _sample(missing_news_set, limit=sample_limit),
        },
        "provider_health": {
            "provider_count": len(providers),
            "critical_count": critical_provider_count,
            "warning_count": warning_provider_count,
            "no_data_count": no_data_provider_count,
        },
        "recommended_actions": _recommended_actions(failed_check_ids),
    }

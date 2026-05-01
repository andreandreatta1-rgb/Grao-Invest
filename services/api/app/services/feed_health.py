from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from app.models import MarketProviderState, MarketTick
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class ProviderFeedHealth(TypedDict):
    provider_name: str
    provider_role: str | None
    provider_status: str | None
    is_active: bool
    health_status: str
    health_issues: list[str]
    instruments_covered: int
    total_ticks: int
    last_event_time: str | None
    last_ingest_time: str | None
    tick_lag_seconds: float | None
    ingestion_staleness_seconds: float | None


class UniverseCoverageRow(TypedDict):
    instrument: str
    provider: str
    last_price: float
    last_event_time: str
    last_ingest_time: str
    lag_seconds: float


class UniverseCoverageSnapshot(TypedDict):
    generated_at: str
    total_instruments_covered: int
    latest_market_event_time: str | None
    latest_ingest_time: str | None
    instruments: list[UniverseCoverageRow]


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _health_status_for_provider(
    *,
    provider_status: str | None,
    ingestion_staleness_seconds: float | None,
    tick_lag_seconds: float | None,
    stale_threshold_seconds: int,
    latency_threshold_seconds: int,
) -> tuple[str, list[str]]:
    issues: list[str] = []
    if provider_status == "failed":
        issues.append("provider_failed")
    elif provider_status == "degraded":
        issues.append("provider_degraded")

    if ingestion_staleness_seconds is None:
        issues.append("no_data")
    elif ingestion_staleness_seconds > float(stale_threshold_seconds):
        issues.append("stale_ingestion")

    if tick_lag_seconds is not None and tick_lag_seconds > float(latency_threshold_seconds):
        issues.append("high_market_lag")

    if not issues:
        return "healthy", []
    if "provider_failed" in issues:
        return "critical", issues
    if "no_data" in issues:
        return "no_data", issues
    return "warning", issues


def provider_feed_health(
    db: Session,
    *,
    stale_threshold_seconds: int = 1800,
    latency_threshold_seconds: int = 120,
    include_counts: bool = False,
) -> list[ProviderFeedHealth]:
    states = list(db.scalars(select(MarketProviderState)))
    now = datetime.now(UTC)
    rows: list[ProviderFeedHealth] = []

    state_map = {state.provider_name: state for state in states}
    counts_by_provider: dict[str, dict[str, int]] = {}
    if include_counts:
        counts_by_provider = {
            str(row[0]): {
                "instruments_covered": int(row[1] or 0),
                "total_ticks": int(row[2] or 0),
            }
            for row in db.execute(
                select(
                    MarketTick.provider,
                    func.count(func.distinct(MarketTick.instrument)),
                    func.count(),
                ).group_by(MarketTick.provider)
            ).all()
        }

    tick_providers = [str(item) for item in db.scalars(select(MarketTick.provider).distinct())]

    provider_names = sorted(
        set(state_map.keys())
        .union(set(tick_providers))
        .union(set(counts_by_provider.keys()))
    )

    for provider_name in provider_names:
        state = state_map.get(provider_name)
        latest_tick = db.execute(
            select(MarketTick.event_time, MarketTick.ingest_time)
            .where(MarketTick.provider == provider_name)
            .order_by(MarketTick.ingest_time.desc(), MarketTick.id.desc())
            .limit(1)
        ).first()
        provider_counts = counts_by_provider.get(
            provider_name,
            {"instruments_covered": 0, "total_ticks": 0},
        )
        instruments_covered = int(provider_counts["instruments_covered"])
        total_ticks = int(provider_counts["total_ticks"])
        if latest_tick is None:
            tick_lag_seconds = None
            ingestion_staleness_seconds = None
            last_event_time = None
            last_ingest_time = None
        else:
            event_time = str(latest_tick[0])
            ingest_time = str(latest_tick[1])
            event_at = _parse_iso_datetime(event_time)
            ingest_at = _parse_iso_datetime(ingest_time)
            tick_lag_seconds = round(max(0.0, (ingest_at - event_at).total_seconds()), 4)
            ingestion_staleness_seconds = round(max(0.0, (now - ingest_at).total_seconds()), 4)
            last_event_time = event_time
            last_ingest_time = ingest_time

        health_status, issues = _health_status_for_provider(
            provider_status=state.status if state is not None else None,
            ingestion_staleness_seconds=ingestion_staleness_seconds,
            tick_lag_seconds=tick_lag_seconds,
            stale_threshold_seconds=stale_threshold_seconds,
            latency_threshold_seconds=latency_threshold_seconds,
        )
        rows.append(
            {
                "provider_name": provider_name,
                "provider_role": state.role if state is not None else None,
                "provider_status": state.status if state is not None else None,
                "is_active": state.is_active if state is not None else False,
                "health_status": health_status,
                "health_issues": issues,
                "instruments_covered": instruments_covered,
                "total_ticks": total_ticks,
                "last_event_time": last_event_time,
                "last_ingest_time": last_ingest_time,
                "tick_lag_seconds": tick_lag_seconds,
                "ingestion_staleness_seconds": ingestion_staleness_seconds,
            }
        )
    return sorted(rows, key=lambda item: (item["provider_name"], item["health_status"]))


def universe_coverage_snapshot(
    db: Session,
    *,
    max_rows: int = 100,
) -> UniverseCoverageSnapshot:
    if max_rows <= 0:
        raise ValueError("max_rows deve ser maior que zero.")

    latest_ingest_subquery = (
        select(
            MarketTick.instrument.label("instrument"),
            func.max(MarketTick.ingest_time).label("max_ingest_time"),
        )
        .group_by(MarketTick.instrument)
        .subquery()
    )
    total_instruments_covered = int(
        db.scalar(select(func.count()).select_from(latest_ingest_subquery)) or 0
    )
    latest_id_subquery = (
        select(
            MarketTick.instrument.label("instrument"),
            func.max(MarketTick.id).label("max_id"),
        )
        .join(
            latest_ingest_subquery,
            (MarketTick.instrument == latest_ingest_subquery.c.instrument)
            & (MarketTick.ingest_time == latest_ingest_subquery.c.max_ingest_time),
        )
        .group_by(MarketTick.instrument)
        .subquery()
    )
    latest_ticks = list(
        db.execute(
            select(
                MarketTick.instrument,
                MarketTick.provider,
                MarketTick.price,
                MarketTick.event_time,
                MarketTick.ingest_time,
            )
            .join(latest_id_subquery, MarketTick.id == latest_id_subquery.c.max_id)
            .order_by(MarketTick.instrument.asc())
            .limit(max_rows)
        ).all()
    )

    now = datetime.now(UTC)
    rows: list[UniverseCoverageRow] = []
    latest_market_event_time: str | None = None
    latest_ingest_time: str | None = None
    for tick in latest_ticks:
        instrument = str(tick[0])
        provider = str(tick[1])
        price = float(tick[2])
        event_time = str(tick[3])
        ingest_time = str(tick[4])
        ingest_at = _parse_iso_datetime(ingest_time)
        lag_seconds = round(max(0.0, (now - ingest_at).total_seconds()), 4)
        if latest_market_event_time is None or event_time > latest_market_event_time:
            latest_market_event_time = event_time
        if latest_ingest_time is None or ingest_time > latest_ingest_time:
            latest_ingest_time = ingest_time
        rows.append(
            {
                "instrument": instrument,
                "provider": provider,
                "last_price": price,
                "last_event_time": event_time,
                "last_ingest_time": ingest_time,
                "lag_seconds": lag_seconds,
            }
        )

    return {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "total_instruments_covered": total_instruments_covered,
        "latest_market_event_time": latest_market_event_time,
        "latest_ingest_time": latest_ingest_time,
        "instruments": rows,
    }

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LLMCostLog, WorkerHeartbeat
from app.services.feed_health import provider_feed_health, universe_coverage_snapshot
from app.services.utils import isoformat, utc_now

WORKER_INTERVAL_MINUTES: dict[str, int] = {
    "intraday_price_worker": 1,
    "news_poll_worker": 5,
    "macro_sync_worker": 24 * 60,
    "signal_generator_worker": 30,
    "thesis_validator_worker": 24 * 60,
    "microtrades_autopilot_worker": 30,
    "portfolio_monitor_worker": 5,
    "rebalance_worker": 7 * 24 * 60,
    "feed_health_worker": 1,
}

_AGENT_RUNNING = False
_AGENT_STARTED_AT: str | None = None


class WorkerStatusPayload(TypedDict):
    worker_name: str
    status: str
    last_run_at: str
    next_run_at: str
    last_error: str | None
    cycles_today: int


class AgentStatusPayload(TypedDict):
    generated_at: str
    runtime: dict[str, object]
    summary: dict[str, int]
    workers: list[WorkerStatusPayload]
    llm_cost_today_usd: float
    data_coverage: dict[str, object]
    feed_health: dict[str, int]


def _next_run(worker_name: str, from_iso: str | None = None) -> str:
    if from_iso is None:
        base = utc_now()
    else:
        parsed = datetime.fromisoformat(from_iso)
        if parsed.tzinfo is None:
            base = parsed.replace(tzinfo=UTC)
        else:
            base = parsed.astimezone(UTC)
    interval = WORKER_INTERVAL_MINUTES.get(worker_name, 5)
    return isoformat(base + timedelta(minutes=interval))


def ensure_worker_heartbeats(db: Session) -> None:
    now = isoformat(utc_now())
    existing_rows = list(db.scalars(select(WorkerHeartbeat)))
    existing_names = {row.worker_name for row in existing_rows}
    created = False
    for worker_name in WORKER_INTERVAL_MINUTES:
        if worker_name in existing_names:
            continue
        db.add(
            WorkerHeartbeat(
                worker_name=worker_name,
                last_run_at=now,
                next_run_at=_next_run(worker_name, now),
                status="idle",
                last_error=None,
                cycles_today=0,
            )
        )
        created = True
    if created:
        db.commit()


def update_worker_heartbeat(
    db: Session,
    *,
    worker_name: str,
    status: str,
    last_error: str | None = None,
    increment_cycle: bool = False,
) -> WorkerHeartbeat:
    row = db.scalar(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name))
    now_iso = isoformat(utc_now())
    if row is None:
        row = WorkerHeartbeat(
            worker_name=worker_name,
            last_run_at=now_iso,
            next_run_at=_next_run(worker_name, now_iso),
            status=status,
            last_error=last_error,
            cycles_today=1 if increment_cycle else 0,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    row.status = status
    row.last_error = last_error
    row.last_run_at = now_iso
    row.next_run_at = _next_run(worker_name, now_iso)
    if increment_cycle:
        row.cycles_today = row.cycles_today + 1
    db.commit()
    db.refresh(row)
    return row


def _llm_cost_today_usd(db: Session) -> float:
    today = utc_now().date().isoformat()
    total = db.scalar(
        select(func.sum(LLMCostLog.cost_usd)).where(LLMCostLog.date == today)
    )
    if total is None:
        return 0.0
    return round(float(total), 4)


def get_agent_status(db: Session) -> AgentStatusPayload:
    ensure_worker_heartbeats(db)
    rows = list(
        db.scalars(select(WorkerHeartbeat).order_by(WorkerHeartbeat.worker_name.asc()))
    )
    workers: list[WorkerStatusPayload] = [
        {
            "worker_name": row.worker_name,
            "status": row.status,
            "last_run_at": row.last_run_at,
            "next_run_at": row.next_run_at,
            "last_error": row.last_error,
            "cycles_today": row.cycles_today,
        }
        for row in rows
    ]
    running_count = sum(1 for row in workers if row["status"] == "running")
    idle_count = sum(1 for row in workers if row["status"] == "idle")
    error_count = sum(1 for row in workers if row["status"] == "error")

    coverage = universe_coverage_snapshot(db, max_rows=20)
    provider_health = provider_feed_health(db)
    critical_feeds = sum(1 for item in provider_health if item["health_status"] == "critical")
    warning_feeds = sum(1 for item in provider_health if item["health_status"] == "warning")
    no_data_feeds = sum(1 for item in provider_health if item["health_status"] == "no_data")

    return {
        "generated_at": isoformat(utc_now()),
        "runtime": {
            "running": _AGENT_RUNNING,
            "started_at": _AGENT_STARTED_AT,
        },
        "summary": {
            "total_workers": len(workers),
            "running_workers": running_count,
            "idle_workers": idle_count,
            "error_workers": error_count,
        },
        "workers": workers,
        "llm_cost_today_usd": _llm_cost_today_usd(db),
        "data_coverage": {
            "instruments_covered": int(coverage["total_instruments_covered"]),
            "latest_ingest_time": coverage["latest_ingest_time"],
            "latest_market_event_time": coverage["latest_market_event_time"],
        },
        "feed_health": {
            "provider_count": len(provider_health),
            "critical_count": critical_feeds,
            "warning_count": warning_feeds,
            "no_data_count": no_data_feeds,
        },
    }


class AgentLoop:
    def start(self) -> dict[str, object]:
        global _AGENT_RUNNING, _AGENT_STARTED_AT
        _AGENT_RUNNING = True
        _AGENT_STARTED_AT = isoformat(utc_now())
        return {"running": _AGENT_RUNNING, "started_at": _AGENT_STARTED_AT}

    def stop(self) -> dict[str, object]:
        global _AGENT_RUNNING
        _AGENT_RUNNING = False
        return {"running": _AGENT_RUNNING, "started_at": _AGENT_STARTED_AT}

    def status(self, db: Session) -> AgentStatusPayload:
        return get_agent_status(db)

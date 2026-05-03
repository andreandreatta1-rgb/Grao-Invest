from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.services import thesis_current_monitor
from app.services.thesis_current_monitor import (
    _is_latest_tick_fresh,
    _monitor_status_and_action,
    _select_current_candidates,
    load_latest_current_thesis_monitor,
    persist_current_thesis_monitor_snapshot,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class _Tick:
    def __init__(self, event_time: str) -> None:
        self.event_time = event_time


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def test_load_latest_current_monitor_falls_back_to_audit_snapshot(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(thesis_current_monitor, "DATA_DIR", tmp_path)
    payload = {
        "generated_at": "2026-05-02T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 0,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 0},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 0,
            "avg_unrealized_financial_pct": 0.0,
            "executive_status_counts": {},
            "needs_attention_count": 0,
        },
        "theses": [],
        "disclaimer": "simulado",
    }

    persist_current_thesis_monitor_snapshot(db_session, payload, user_id=1)
    latest_file = tmp_path / "current_thesis_monitor_latest.json"
    assert latest_file.exists()
    latest_file.unlink()

    loaded = load_latest_current_thesis_monitor(db_session, user_id=1)

    assert loaded == payload


def test_select_current_candidates_can_prioritize_distinct_instruments() -> None:
    candidates = [
        {
            "instrument": "PETR4",
            "confidence_tese_pct": 90.0,
            "expected_financial_pct": 5.0,
        },
        {
            "instrument": "PETR4",
            "confidence_tese_pct": 89.0,
            "expected_financial_pct": 5.0,
        },
        {
            "instrument": "VALE3",
            "confidence_tese_pct": 80.0,
            "expected_financial_pct": 4.0,
        },
        {
            "instrument": "ITUB4",
            "confidence_tese_pct": 70.0,
            "expected_financial_pct": 3.0,
        },
    ]

    selected = _select_current_candidates(
        candidates,  # type: ignore[arg-type]
        thesis_count=3,
        distinct_instruments=True,
    )

    assert [item["instrument"] for item in selected] == ["PETR4", "VALE3", "ITUB4"]


def test_select_current_candidates_can_prioritize_recency_for_current_operations() -> None:
    candidates = [
        {
            "instrument": "GGBR4",
            "entry_index": 10,
            "entry_time": "2019-12-13T00:00:00+00:00",
            "confidence_tese_pct": 95.0,
            "expected_financial_pct": 5.0,
        },
        {
            "instrument": "GGBR4",
            "entry_index": 200,
            "entry_time": "2026-04-14T00:00:00+00:00",
            "confidence_tese_pct": 65.0,
            "expected_financial_pct": 3.0,
        },
    ]

    selected = _select_current_candidates(
        candidates,  # type: ignore[arg-type]
        thesis_count=1,
        distinct_instruments=True,
        prefer_recent=True,
    )

    assert selected[0]["entry_time"] == "2026-04-14T00:00:00+00:00"


def test_latest_tick_freshness_rejects_stale_current_operations() -> None:
    reference = datetime.fromisoformat("2026-05-02T20:00:00+00:00")

    assert _is_latest_tick_fresh([_Tick("2026-04-20T00:00:00+00:00")], 45, reference)
    assert not _is_latest_tick_fresh([_Tick("2025-06-02T00:00:00+00:00")], 45, reference)


def test_monitor_status_marks_range_break_as_stop_alert() -> None:
    thesis = {
        "direction": "range",
        "entry_price": 41.03,
        "target_price": 41.03,
        "stop_price": 40.4145,
    }

    monitor_status, suggested_action = _monitor_status_and_action(  # type: ignore[arg-type]
        thesis,
        latest_price=47.02,
    )

    assert monitor_status == "stop_alert"
    assert suggested_action == "reduzir_risco_ou_encerrar"


def test_load_latest_current_monitor_falls_back_to_bundled_bootstrap(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    bundled_dir = tmp_path / "data"
    bundled_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(thesis_current_monitor, "DATA_DIR", runtime_dir)
    monkeypatch.setattr(thesis_current_monitor, "BASE_DIR", tmp_path)

    payload = {
        "generated_at": "2026-05-02T16:43:23+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 20,
        "thesis_count": 8,
        "scan_scope": {"instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "summary": {"target_hits": 0, "stop_alerts": 0, "monitoring_count": 8},
        "theses": [{"instrument": "BTCUSDT"}],
        "disclaimer": "simulado",
    }
    (bundled_dir / "current_thesis_monitor_bootstrap.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    loaded = load_latest_current_thesis_monitor(db_session, user_id=1)

    assert loaded == payload

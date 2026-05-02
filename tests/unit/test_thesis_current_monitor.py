from __future__ import annotations

from collections.abc import Generator

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.services import thesis_current_monitor
from app.services.thesis_current_monitor import (
    load_latest_current_thesis_monitor,
    persist_current_thesis_monitor_snapshot,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


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

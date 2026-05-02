from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.models import MarketTick
from app.services.microtrades_autopilot import (
    _run_backfill,
    build_microtrades_autopilot_config,
    create_decision_with_cooldown,
    run_microtrades_autopilot_cycle,
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


def test_build_microtrades_autopilot_config_normalizes_inputs() -> None:
    config = build_microtrades_autopilot_config(
        user_id=5,
        instruments=["btcusdt", "ETHUSDT", "BTCUSDT", "  "],
        lookback_hours=99999,
        max_candles_per_instrument=1,
        horizon_bars=200,
    )
    assert config["user_id"] == 5
    assert config["instruments"] == ["BTCUSDT", "ETHUSDT"]
    assert config["lookback_hours"] == 24 * 365
    assert config["max_candles_per_instrument"] == 50
    assert config["horizon_bars"] == 60


def test_create_decision_with_cooldown_reuses_pending_decision(db_session: Session) -> None:
    first = create_decision_with_cooldown(
        db_session,
        user_id=1,
        title="Microtrades: resumo do ciclo automatico",
        context="Resumo do ciclo.",
        question="Qual ajuste voce prefere para o proximo ciclo?",
        options=[
            {"option_id": "A", "label": "Continuar ciclo automatico no escopo atual"},
            {"option_id": "B", "label": "Focar nas criptos de maior confianca"},
        ],
        priority="normal",
        cooldown_minutes=60,
    )
    second = create_decision_with_cooldown(
        db_session,
        user_id=1,
        title="Microtrades: resumo do ciclo automatico",
        context="Resumo do ciclo.",
        question="Qual ajuste voce prefere para o proximo ciclo?",
        options=[
            {"option_id": "A", "label": "Continuar ciclo automatico no escopo atual"},
            {"option_id": "B", "label": "Focar nas criptos de maior confianca"},
        ],
        priority="normal",
        cooldown_minutes=60,
    )
    assert first["status"] == "created"
    assert second["status"] == "cooldown"
    assert second["decision_id"] == first["decision_id"]


def test_run_backfill_skips_fetch_when_recent_history_is_already_available(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_time = datetime(2026, 5, 2, 20, 0, tzinfo=UTC)
    for instrument in ["BTCUSDT", "ETHUSDT"]:
        for index in range(90):
            db_session.add(
                MarketTick(
                    instrument=instrument,
                    provider="crypto-binance-5m",
                    event_time=(base_time - timedelta(minutes=5 * (89 - index))).isoformat(),
                    ingest_time=(base_time - timedelta(minutes=5 * (89 - index))).isoformat(),
                    price=60000.0 + index,
                    volume=10 + index,
                    currency="USD",
                    source_payload_id=f"{instrument}-{index}",
                )
            )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.microtrades_autopilot.utc_now",
        lambda: base_time,
    )

    called = {"fetch": False}

    def _unexpected_fetch(*args: object, **kwargs: object) -> list[dict[str, object]]:
        called["fetch"] = True
        raise AssertionError("fetch_historical_crypto_candles nao deveria ser chamado")

    monkeypatch.setattr(
        "app.services.microtrades_autopilot.fetch_historical_crypto_candles",
        _unexpected_fetch,
    )

    config = build_microtrades_autopilot_config(
        user_id=1,
        instruments=["BTCUSDT", "ETHUSDT"],
        interval="5m",
        lookback_hours=2,
        max_candles_per_instrument=90,
        horizon_bars=8,
    )

    payload = _run_backfill(db_session, config=config)

    assert payload["skipped"] is True
    assert payload["skip_reason"] == "historico_recente_ja_disponivel"
    assert called["fetch"] is False


def test_autopilot_keeps_monitoring_when_case_study_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_microtrades_autopilot_config(
        user_id=1,
        instruments=["BTCUSDT", "ETHUSDT"],
        interval="5m",
        lookback_hours=72,
        max_candles_per_instrument=900,
        horizon_bars=8,
        thesis_count=4,
        recent_bars_window=7,
        publish_decisions=False,
    )
    monitor_payload = {
        "generated_at": "2026-05-02T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 1,
        "scan_scope": {"instruments": ["BTCUSDT", "ETHUSDT"], "candidate_count": 1},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 1,
            "avg_unrealized_financial_pct": 0.8,
            "executive_status_counts": {"mantida": 1},
            "needs_attention_count": 0,
        },
        "theses": [
            {
                "instrument": "BTCUSDT",
                "confidence_now_pct": 61.5,
                "confidence_tese_pct": 60.0,
                "expected_financial_pct": 1.2,
                "executive_status_label": "Mantida",
            }
        ],
        "disclaimer": "simulado",
    }

    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_backfill",
        lambda db, config: {"processed_count": 0, "failed_count": 0},
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_live_ingestion",
        lambda db, config: {"processed_count": 0, "failed_count": 0},
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_signal_generation",
        lambda db, config: {
            "skipped": False,
            "signal_id": 99,
            "instrument": "BTCUSDT",
            "signal_type": "swing",
            "confidence": 0.61,
        },
    )

    def _case_study_failure(*args: object, **kwargs: object) -> tuple[dict[str, object], bool]:
        raise ValueError("Historico insuficiente para validar teses no horizonte solicitado.")

    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_case_study_with_auto_suitability",
        _case_study_failure,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_monitor_with_auto_suitability",
        lambda db, config: (monitor_payload, False, False),
    )

    payload = run_microtrades_autopilot_cycle(db_session, config=config)

    assert payload["status"] == "partial"
    assert payload["monitor"]["thesis_count"] == 1
    assert any(
        step["title"] == "comprovacao" and step["status"] == "warning"
        for step in payload["steps"]
    )
    assert any(
        step["title"] == "monitoramento" and step["status"] == "ok"
        for step in payload["steps"]
    )

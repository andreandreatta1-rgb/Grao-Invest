from __future__ import annotations

import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.models import MarketTick
from app.services import microtrades_autopilot
from app.services.microtrades_autopilot import (
    _run_backfill,
    build_microtrades_autopilot_config,
    create_decision_with_cooldown,
    load_latest_microtrades_autopilot_snapshot,
    persist_microtrades_autopilot_snapshot,
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
    assert config["allow_external_fetches"] is True


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


def test_load_latest_microtrades_autopilot_falls_back_to_audit_snapshot(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(microtrades_autopilot, "DATA_DIR", tmp_path)
    payload = {
        "status": "partial",
        "error": None,
        "run_started_at": "2026-05-04T10:00:00+00:00",
        "run_finished_at": "2026-05-04T10:01:00+00:00",
        "user_id": 1,
        "config": {"interval": "5m", "instruments": ["BTCUSDT", "ETHUSDT"]},
        "steps": [{"title": "monitoramento", "status": "ok", "meta": "2 teses monitoradas."}],
        "backfill": {"status": "ok"},
        "live_ingestion": {"status": "warning"},
        "signal": {"status": "ok"},
        "case_study": {"status": "warning"},
        "monitor": {"thesis_count": 2, "summary": {"monitoring_count": 2, "needs_attention_count": 1}},
        "decision": {"status": "created", "decision_id": "dec-1"},
    }

    persist_microtrades_autopilot_snapshot(db_session, payload, user_id=1)
    latest_file = tmp_path / "microtrades_autopilot_latest.json"
    assert latest_file.exists()
    latest_file.unlink()

    loaded = load_latest_microtrades_autopilot_snapshot(db_session, user_id=1)

    assert loaded == payload


def test_load_latest_microtrades_autopilot_falls_back_to_bundled_bootstrap(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(microtrades_autopilot, "DATA_DIR", tmp_path / "runtime-data")
    monkeypatch.setattr(microtrades_autopilot, "BASE_DIR", tmp_path)
    payload = {
        "status": "partial",
        "error": None,
        "run_started_at": "2026-05-04T10:00:00+00:00",
        "run_finished_at": "2026-05-04T10:01:00+00:00",
        "user_id": 1,
        "config": {"interval": "5m", "instruments": ["BTCUSDT", "ETHUSDT"]},
        "steps": [{"title": "historico", "status": "ok", "meta": "100 candles processados."}],
        "backfill": {"status": "ok", "processed_count": 100},
        "live_ingestion": {"status": "warning", "processed_count": 0},
        "signal": {"status": "ok", "instrument": "BTCUSDT"},
        "case_study": {"status": "warning"},
        "monitor": {"thesis_count": 2, "summary": {"monitoring_count": 2, "needs_attention_count": 1}},
        "decision": {"status": "created", "decision_id": "dec-42"},
    }
    bootstrap_path = tmp_path / "data" / "microtrades_autopilot_latest.json"
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_latest_microtrades_autopilot_snapshot(db_session, user_id=1)

    assert loaded == payload


def test_load_latest_microtrades_autopilot_can_skip_bundled_bootstrap(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(microtrades_autopilot, "DATA_DIR", tmp_path / "runtime-data")
    monkeypatch.setattr(microtrades_autopilot, "BASE_DIR", tmp_path)
    payload = {
        "status": "partial",
        "error": None,
        "run_started_at": "2026-05-04T10:00:00+00:00",
        "run_finished_at": "2026-05-04T10:01:00+00:00",
        "user_id": 1,
        "config": {"interval": "5m", "instruments": ["BTCUSDT", "ETHUSDT"]},
        "steps": [{"title": "historico", "status": "ok", "meta": "100 candles processados."}],
        "backfill": {"status": "ok", "processed_count": 100},
        "live_ingestion": {"status": "warning", "processed_count": 0},
        "signal": {"status": "ok", "instrument": "BTCUSDT"},
        "case_study": {"status": "warning"},
        "monitor": {"thesis_count": 2, "summary": {"monitoring_count": 2, "needs_attention_count": 1}},
        "decision": {"status": "created", "decision_id": "dec-42"},
    }
    bootstrap_path = tmp_path / "data" / "microtrades_autopilot_latest.json"
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_latest_microtrades_autopilot_snapshot(
        db_session,
        user_id=1,
        include_bundled_bootstrap=False,
    )

    assert loaded is None


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


def test_run_backfill_skips_fetch_when_external_fetches_are_disabled(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        lookback_hours=72,
        max_candles_per_instrument=900,
        horizon_bars=8,
        allow_external_fetches=False,
    )

    payload = _run_backfill(db_session, config=config)

    assert payload["skipped"] is True
    assert payload["skip_reason"] == "external_fetches_disabled"
    assert called["fetch"] is False


def test_run_live_ingestion_skips_provider_when_external_fetches_are_disabled(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"quotes": False}

    def _unexpected_quotes(*args: object, **kwargs: object) -> list[dict[str, object]]:
        called["quotes"] = True
        raise AssertionError("fetch_intraday_quotes nao deveria ser chamado")

    monkeypatch.setattr(
        "app.services.microtrades_autopilot.fetch_intraday_quotes",
        _unexpected_quotes,
    )

    config = build_microtrades_autopilot_config(
        user_id=1,
        instruments=["BTCUSDT"],
        allow_external_fetches=False,
    )

    payload = microtrades_autopilot._run_live_ingestion(db_session, config=config)

    assert payload["skipped"] is True
    assert payload["processed_count"] == 0
    assert payload["skip_reason"] == "external_fetches_disabled"
    assert called["quotes"] is False


def test_run_data_refresh_runs_only_ingestion_steps(
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
        allow_external_fetches=True,
        publish_decisions=False,
    )
    captured: dict[str, object] = {}

    def fake_backfill(
        _db,
        *,
        config,
        lookback_hours=None,
        max_candles_per_instrument=None,
    ):  # noqa: ANN001, ANN202
        captured["backfill_config"] = dict(config)
        captured["lookback_hours"] = lookback_hours
        captured["max_candles_per_instrument"] = max_candles_per_instrument
        return {"processed_count": 42, "failed_count": 0}

    def fake_live(_db, *, config):  # noqa: ANN001, ANN202
        captured["live_config"] = dict(config)
        return {"processed_count": 2, "failed_count": 0}

    def forbidden_step(*args: object, **kwargs: object) -> None:
        raise AssertionError("data refresh nao deve recalcular teses nem publicar decisoes")

    monkeypatch.setattr("app.services.microtrades_autopilot._run_backfill", fake_backfill)
    monkeypatch.setattr("app.services.microtrades_autopilot._run_live_ingestion", fake_live)
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_monitor_with_auto_suitability",
        forbidden_step,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._publish_cycle_decision",
        forbidden_step,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.build_data_quality_gate_snapshot",
        lambda _db, *, instruments, include_provider_health=False: {
            "scope": {"target_instruments_sample": instruments},
            "summary": {"gate_status": "pass"},
        },
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.record_audit_event",
        lambda _db, event_type, details, user_id: captured.update(
            {
                "event_type": event_type,
                "event_user_id": user_id,
                "audit_payload": details["payload"],
            }
        ),
    )

    payload = microtrades_autopilot.run_microtrades_data_refresh(
        db_session,
        config=config,
        lookback_hours=2,
        max_candles_per_instrument=75,
        run_backfill=True,
        run_live_ingestion=True,
    )

    assert payload["status"] == "success"
    assert payload["mode"] == "data_refresh"
    assert payload["backfill"]["processed_count"] == 42
    assert payload["live_ingestion"]["processed_count"] == 2
    assert payload["data_quality"]["summary"]["gate_status"] == "pass"
    assert captured["lookback_hours"] == 2
    assert captured["max_candles_per_instrument"] == 75
    assert captured["event_type"] == "microtrades.data_refresh"
    assert captured["event_user_id"] == 1
    assert captured["audit_payload"]["mode"] == "data_refresh"


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


def test_autopilot_local_only_skips_case_study_for_fast_latest_refresh(
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
        allow_external_fetches=False,
        publish_decisions=False,
    )

    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_case_study_with_auto_suitability",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("case-study nao deveria ser chamado em modo local_only")
        ),
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot._run_monitor_with_auto_suitability",
        lambda db, config: (
            {
                "generated_at": "2026-05-04T19:40:00+00:00",
                "user_id": 1,
                "horizon_bars": 8,
                "recent_bars_window": 7,
                "thesis_count": 0,
                "scan_scope": {"instruments": ["BTCUSDT", "ETHUSDT"], "candidate_count": 0},
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
            },
            False,
            True,
        ),
    )

    payload = run_microtrades_autopilot_cycle(db_session, config=config)

    assert payload["status"] == "partial"
    assert payload["case_study"]["skipped"] is True
    assert payload["case_study"]["reason"] == "local_only_fast_refresh"
    assert any(
        step["title"] == "comprovacao" and step["status"] == "warning"
        for step in payload["steps"]
    )


def test_run_monitor_returns_empty_payload_when_intraday_data_is_stale(
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
        allow_external_fetches=False,
        publish_decisions=False,
    )
    captured: dict[str, object] = {}

    def _stale_monitor(*args: object, **kwargs: object) -> dict[str, object]:
        raise ValueError("Nao ha dados de mercado frescos para monitorar teses atuais.")

    def _capture_snapshot(db: Session, payload: dict[str, object], *, user_id: int) -> None:
        captured["payload"] = payload
        captured["user_id"] = user_id

    monkeypatch.setattr(
        "app.services.microtrades_autopilot.run_current_thesis_monitor",
        _stale_monitor,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.persist_current_thesis_monitor_snapshot",
        _capture_snapshot,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.load_latest_current_thesis_monitor",
        lambda db, user_id, include_bundled_bootstrap=False: None,
    )

    (
        payload,
        suitability_created,
        empty_payload,
    ) = microtrades_autopilot._run_monitor_with_auto_suitability(db_session, config=config)

    assert suitability_created is False
    assert empty_payload is True
    assert payload["thesis_count"] == 0
    assert payload["summary"]["notes"] == ["Nao ha dados de mercado frescos para monitorar teses atuais."]
    assert captured["user_id"] == 1


def test_run_monitor_reuses_previous_valid_snapshot_when_local_refresh_has_no_fresh_data(
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
        allow_external_fetches=False,
        publish_decisions=False,
    )
    previous_monitor = {
        "generated_at": "2026-05-05T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 2000,
        "thesis_count": 2,
        "scan_scope": {"instruments": ["PETR4", "BTCUSDT"], "candidate_count": 20},
        "summary": {"monitoring_count": 2, "notes": []},
        "theses": [{"thesis_id": "TH-PETR4-1"}, {"thesis_id": "TH-BTCUSDT-1"}],
        "disclaimer": "simulado",
    }
    persisted: list[dict[str, object]] = []

    def _stale_monitor(*args: object, **kwargs: object) -> dict[str, object]:
        raise ValueError("Nao ha dados de mercado frescos para monitorar teses atuais.")

    monkeypatch.setattr(
        "app.services.microtrades_autopilot.run_current_thesis_monitor",
        _stale_monitor,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.load_latest_current_thesis_monitor",
        lambda db, user_id, include_bundled_bootstrap=False: previous_monitor,
    )
    monkeypatch.setattr(
        "app.services.microtrades_autopilot.persist_current_thesis_monitor_snapshot",
        lambda db, payload, *, user_id: persisted.append(payload),
    )

    (
        payload,
        suitability_created,
        empty_payload,
    ) = microtrades_autopilot._run_monitor_with_auto_suitability(db_session, config=config)

    assert suitability_created is False
    assert empty_payload is False
    assert payload["thesis_count"] == 2
    assert payload["data_quality"]["status"] == "stale_reused"
    assert payload["summary"]["notes"] == [
        "Dados de mercado sem frescor; mantendo ultimo monitor valido."
    ]
    assert persisted == []

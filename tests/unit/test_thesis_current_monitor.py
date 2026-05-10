from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime, timedelta

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.models import SuitabilityProfile
from app.services import thesis_current_monitor
from app.services.thesis_current_monitor import (
    _is_latest_tick_fresh,
    _monitor_status_and_action,
    _select_current_candidates,
    current_monitor_contract_issues,
    load_latest_current_thesis_monitor,
    persist_current_thesis_monitor_snapshot,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class _Tick:
    def __init__(self, event_time: str) -> None:
        self.event_time = event_time


class _MarketTickStub:
    def __init__(self, event_time: str, price: float, volume: int) -> None:
        self.event_time = event_time
        self.price = price
        self.volume = volume


def _contract_payload(thesis: dict[str, object]) -> dict[str, object]:
    return {
        "generated_at": "2026-05-06T23:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 1,
        "scan_scope": {"instruments": [thesis.get("instrument", "PETR4")]},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 1,
            "avg_unrealized_financial_pct": 0.0,
            "executive_status_counts": {"mantida": 1},
            "needs_attention_count": 0,
        },
        "theses": [
            {
                "thesis_id": "TH-1",
                "instrument": "PETR4",
                "direction": "bullish",
                "thesis_raised_at": "2026-05-06T20:00:00+00:00",
                "latest_event_time": "2026-05-06T22:55:00+00:00",
                "entry_price": 40.0,
                "target_price": 42.0,
                "stop_price": 38.8,
                "monitor_status": "monitoring",
                **thesis,
            }
        ],
        "disclaimer": "simulado",
    }


def _fake_revaluation(**_: object) -> dict[str, object]:
    return {
        "confidence_now_pct": 73.0,
        "confidence_delta_pct": -1.0,
        "executive_status": "mantida",
        "executive_status_label": "Mantida",
        "suggested_action": "manter_monitoramento",
        "thesis_validity": "valida",
        "revaluation_reason": "teste",
        "next_trigger": "acompanhar",
        "learning_signal": "neutro",
    }


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


def test_load_latest_current_monitor_skips_no_fresh_empty_snapshot(
    db_session: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(thesis_current_monitor, "DATA_DIR", tmp_path)
    valid_payload = {
        "generated_at": "2026-05-05T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 2000,
        "thesis_count": 2,
        "scan_scope": {"instruments": ["PETR4", "BTCUSDT"], "candidate_count": 20},
        "summary": {"target_hits": 0, "stop_alerts": 0, "monitoring_count": 2},
        "theses": [{"thesis_id": "TH-PETR4-1"}, {"thesis_id": "TH-BTCUSDT-1"}],
        "disclaimer": "simulado",
    }
    empty_no_fresh_payload = {
        "generated_at": "2026-05-05T21:26:19+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 7,
        "thesis_count": 0,
        "scan_scope": {"instruments": ["BTCUSDT"], "candidate_count": 0},
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 0,
            "notes": ["Nao ha dados de mercado frescos para monitorar teses atuais."],
        },
        "theses": [],
        "disclaimer": "simulado",
    }
    persist_current_thesis_monitor_snapshot(db_session, valid_payload, user_id=1)
    persist_current_thesis_monitor_snapshot(db_session, empty_no_fresh_payload, user_id=1)

    loaded = load_latest_current_thesis_monitor(
        db_session,
        user_id=1,
        include_bundled_bootstrap=False,
    )

    assert loaded == valid_payload


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


def test_latest_tick_freshness_infers_intraday_threshold_when_limit_is_not_provided() -> None:
    reference = datetime.fromisoformat("2026-05-04T21:42:00+00:00")
    ticks = [
        _Tick(f"2026-05-04T19:{minute:02d}:00+00:00")
        for minute in (0, 5, 10, 15, 20)
    ]

    assert not _is_latest_tick_fresh(ticks, None, reference)


def test_monitor_status_marks_range_break_as_stop_alert() -> None:
    thesis = {
        "direction": "range",
        "entry_price": 41.03,
        "target_price": 41.03,
        "stop_price": 40.4145,
        "range_lower_price": 40.4145,
        "range_upper_price": 41.6455,
    }

    monitor_status, suggested_action = _monitor_status_and_action(  # type: ignore[arg-type]
        thesis,
        latest_price=47.02,
    )

    assert monitor_status == "stop_alert"
    assert suggested_action == "reduzir_risco_ou_encerrar"


def test_monitor_status_keeps_range_alive_above_center_when_inside_band() -> None:
    thesis = {
        "direction": "range",
        "entry_price": 41.03,
        "target_price": 41.03,
        "stop_price": 40.4145,
        "range_lower_price": 40.4145,
        "range_upper_price": 41.6455,
    }

    monitor_status, suggested_action = _monitor_status_and_action(  # type: ignore[arg-type]
        thesis,
        latest_price=41.4,
    )

    assert monitor_status == "monitoring"
    assert suggested_action == "manter_monitoramento"


def test_current_monitor_contract_rejects_directional_target_equal_to_entry() -> None:
    issues = current_monitor_contract_issues(
        _contract_payload({"entry_price": 40.0, "target_price": 40.0}),
        reference_time=datetime.fromisoformat("2026-05-06T23:00:00+00:00"),
    )

    assert "theses.0.target.same_as_entry" in {issue["code"] for issue in issues}


def test_current_monitor_contract_rejects_range_without_explicit_bounds() -> None:
    issues = current_monitor_contract_issues(
        _contract_payload(
            {
                "instrument": "BTCUSDT",
                "direction": "range",
                "entry_price": 81212.04,
                "target_price": 81212.04,
                "stop_price": 79993.86,
            }
        ),
        reference_time=datetime.fromisoformat("2026-05-06T23:00:00+00:00"),
    )

    assert "theses.0.range.bounds" in {issue["code"] for issue in issues}


def test_current_monitor_contract_rejects_future_timestamps() -> None:
    issues = current_monitor_contract_issues(
        _contract_payload({"thesis_raised_at": "2026-05-07T00:05:00+00:00"}),
        reference_time=datetime.fromisoformat("2026-05-06T23:00:00+00:00"),
    )

    assert "theses.0.thesis_raised_at.future" in {issue["code"] for issue in issues}


def test_current_monitor_contract_rejects_stale_b3_when_enforced() -> None:
    issues = current_monitor_contract_issues(
        _contract_payload({"latest_event_time": "2026-04-22T20:46:19+00:00"}),
        reference_time=datetime.fromisoformat("2026-05-06T23:00:00+00:00"),
        enforce_fresh_b3=True,
    )

    assert "theses.0.b3.stale_current" in {issue["code"] for issue in issues}


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


def test_load_latest_current_monitor_can_skip_bundled_bootstrap(
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

    loaded = load_latest_current_thesis_monitor(
        db_session,
        user_id=1,
        include_bundled_bootstrap=False,
    )

    assert loaded is None


def test_run_current_monitor_uses_bounded_default_scope_when_instruments_are_missing(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_session.add(
        SuitabilityProfile(
            user_id=1,
            investor_profile="moderado",
            time_horizon="medio",
            risk_tolerance="media",
            liquidity_need="media",
            created_at="2026-05-03T10:00:00+00:00",
        )
    )
    db_session.commit()

    captured: dict[str, object] = {}

    def _capture_available_instruments(
        db: Session,
        instruments: list[str] | None,
    ) -> list[str]:
        captured["instruments"] = instruments
        return []

    monkeypatch.setattr(
        thesis_current_monitor,
        "_available_instruments",
        _capture_available_instruments,
    )

    with pytest.raises(ValueError, match="Nao ha historico de mercado"):
        thesis_current_monitor.run_current_thesis_monitor(
            db_session,
            user_id=1,
            instruments=None,
        )

    assert captured["instruments"] == [
        "PETR4",
        "VALE3",
        "ITUB4",
        "BBDC4",
        "BBAS3",
        "ABEV3",
        "WEGE3",
        "B3SA3",
        "RENT3",
        "SUZB3",
        "JBSS3",
        "PRIO3",
        "RADL3",
        "GGBR4",
        "VBBR3",
        "LREN3",
        "HAPV3",
        "BPAC11",
        "RAIL3",
        "CMIG4",
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "LINKUSDT",
        "LTCUSDT",
    ]


def test_run_current_monitor_only_enriches_candidates_inside_current_window(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_session.add(
        SuitabilityProfile(
            user_id=1,
            investor_profile="moderado",
            time_horizon="medio",
            risk_tolerance="media",
            liquidity_need="media",
            created_at="2026-05-03T10:00:00+00:00",
        )
    )
    db_session.commit()

    ticks = [
        _MarketTickStub(
            event_time=f"2026-05-03T00:{index:02d}:00+00:00",
            price=100.0 + index,
            volume=1000 + index,
        )
        for index in range(40)
    ]
    raw_candidates = [
        {
            "instrument": "BTCUSDT",
            "direction": "bullish",
            "entry_index": 20,
            "entry_time": ticks[20].event_time,
            "horizon_bars": 8,
            "entry_price": 120.0,
            "target_price": 126.0,
            "stop_price": 116.4,
            "target_move_pct": 5.0,
            "volatility_pct": 1.2,
            "momentum_pct": 2.4,
            "confidence_base_pct": 62.0,
            "success_realized": True,
            "realized_move_pct": 3.2,
        },
        {
            "instrument": "BTCUSDT",
            "direction": "bullish",
            "entry_index": 35,
            "entry_time": ticks[35].event_time,
            "horizon_bars": 8,
            "entry_price": 135.0,
            "target_price": 141.75,
            "stop_price": 130.95,
            "target_move_pct": 5.0,
            "volatility_pct": 1.1,
            "momentum_pct": 2.8,
            "confidence_base_pct": 68.0,
            "success_realized": True,
            "realized_move_pct": 4.1,
        },
    ]
    captured: dict[str, object] = {}

    def _fake_enriched(
        db: Session,
        candidates: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        captured["candidates"] = list(candidates)
        theses = []
        for index, candidate in enumerate(candidates, start=1):
            theses.append(
                {
                    "thesis_id": f"TH-BTCUSDT-{index:04d}",
                    "instrument": candidate["instrument"],
                    "direction": candidate["direction"],
                    "entry_index": candidate["entry_index"],
                    "entry_time": candidate["entry_time"],
                    "entry_price": candidate["entry_price"],
                    "target_price": candidate["target_price"],
                    "stop_price": candidate["stop_price"],
                    "target_move_pct": candidate["target_move_pct"],
                    "horizon_bars": candidate["horizon_bars"],
                    "confidence_tese_pct": 72.0,
                    "success_probability_pct": 72.0,
                    "expected_financial_pct": 1.8,
                    "support_rate_pct": 60.0,
                    "technical_support_pct": candidate["confidence_base_pct"],
                    "fundamental_support_pct": 55.0,
                    "news_support_pct": 52.0,
                    "geo_oil_support_pct": 50.0,
                    "news_available": True,
                    "geo_oil_available": False,
                    "fundamental_available": True,
                    "fundamental_context": {
                        "available": True,
                        "support_pct": 55.0,
                        "rationale": [],
                        "snapshot": None,
                    },
                    "supporting_signals": ["momento_bullish_2.80pct"],
                }
            )
        return theses

    monkeypatch.setattr(
        thesis_current_monitor,
        "_resolve_monitor_instruments",
        lambda db, instruments: ["BTCUSDT"],
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_ticks_for_instrument",
        lambda db, instrument: ticks,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_is_latest_tick_fresh",
        lambda tick_items, max_age, reference_time: True,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_raw_candidates_from_ticks",
        lambda instrument, tick_items, horizon_bars: list(raw_candidates),
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_enriched_thesis_candidates",
        _fake_enriched,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "apply_active_policy",
        lambda enriched: (enriched, {"policy_name": "stub"}),
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_strategy_for_thesis",
        lambda thesis, investor_profile: {
            "strategy_id": "SIM",
            "strategy_name": "Simulada",
            "rationale": "teste",
            "max_gain_pct": 5.0,
            "max_loss_pct": 3.0,
            "breakeven_price": 100.0,
            "legs": [],
        },
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_realized_financial_pct",
        lambda operation, thesis, latest_price: 0.75,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "build_operation_revaluation",
        lambda thesis, **kwargs: _fake_revaluation(**kwargs),
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_monitoring_timeline",
        lambda ticks, thesis, operation, entry_index, latest_index: [],
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "persist_current_thesis_monitor_snapshot",
        lambda db, payload, user_id: None,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "notify_current_thesis_monitor",
        lambda db, payload: None,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "record_audit_event",
        lambda db, event_type, details, user_id: None,
    )

    payload = thesis_current_monitor.run_current_thesis_monitor(
        db_session,
        user_id=1,
        instruments=None,
        recent_bars_window=7,
        thesis_count=4,
    )

    assert [item["entry_index"] for item in captured["candidates"]] == [35]
    assert payload["scan_scope"]["candidate_count"] == 1
    assert payload["scan_scope"]["current_candidate_count"] == 1
    assert payload["thesis_count"] == 1


def test_run_current_monitor_builds_live_open_candidate_from_latest_bars(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_session.add(
        SuitabilityProfile(
            user_id=1,
            investor_profile="moderado",
            time_horizon="medio",
            risk_tolerance="media",
            liquidity_need="media",
            created_at="2026-05-03T10:00:00+00:00",
        )
    )
    db_session.commit()

    start = datetime.fromisoformat("2026-05-03T00:00:00+00:00")
    ticks = [
        _MarketTickStub(
            event_time=(start + timedelta(minutes=5 * index)).isoformat(),
            price=100.0 + (index * 0.9),
            volume=1_000 + (index * 25),
        )
        for index in range(40)
    ]

    def _fake_enriched(
        db: Session,
        candidates: list[dict[str, object]],
        *,
        support_candidates: list[dict[str, object]] | None = None,
        use_skill_profile: bool = True,
    ) -> list[dict[str, object]]:
        theses = []
        for index, candidate in enumerate(candidates, start=1):
            theses.append(
                {
                    "thesis_id": f"TH-BTCUSDT-LIVE-{index:04d}",
                    "instrument": candidate["instrument"],
                    "direction": candidate["direction"],
                    "entry_index": candidate["entry_index"],
                    "entry_time": candidate["entry_time"],
                    "entry_price": candidate["entry_price"],
                    "target_price": candidate["target_price"],
                    "stop_price": candidate["stop_price"],
                    "target_move_pct": candidate["target_move_pct"],
                    "horizon_bars": candidate["horizon_bars"],
                    "confidence_tese_pct": 74.0,
                    "success_probability_pct": 74.0,
                    "expected_financial_pct": 1.9,
                    "support_rate_pct": 61.0,
                    "technical_support_pct": candidate["confidence_base_pct"],
                    "fundamental_support_pct": 55.0,
                    "news_support_pct": 52.0,
                    "geo_oil_support_pct": 50.0,
                    "news_available": True,
                    "geo_oil_available": False,
                    "fundamental_available": True,
                    "fundamental_context": {
                        "available": True,
                        "support_pct": 55.0,
                        "rationale": [],
                        "snapshot": None,
                    },
                    "supporting_signals": ["momento_bullish_2.80pct"],
                }
            )
        return theses

    monkeypatch.setattr(
        thesis_current_monitor,
        "_resolve_monitor_instruments",
        lambda db, instruments: ["BTCUSDT"],
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_ticks_for_instrument",
        lambda db, instrument: ticks,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_is_latest_tick_fresh",
        lambda tick_items, max_age, reference_time: True,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_enriched_thesis_candidates",
        _fake_enriched,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "apply_active_policy",
        lambda enriched: (enriched, {"policy_name": "stub"}),
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_strategy_for_thesis",
        lambda thesis, investor_profile: {
            "strategy_id": "SIM",
            "strategy_name": "Simulada",
            "rationale": "teste",
            "max_gain_pct": 5.0,
            "max_loss_pct": 3.0,
            "breakeven_price": 100.0,
            "legs": [],
        },
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "_realized_financial_pct",
        lambda operation, thesis, latest_price: 0.0,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "build_operation_revaluation",
        lambda thesis, **kwargs: _fake_revaluation(**kwargs),
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "persist_current_thesis_monitor_snapshot",
        lambda db, payload, user_id: None,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "notify_current_thesis_monitor",
        lambda db, payload: None,
    )
    monkeypatch.setattr(
        thesis_current_monitor,
        "record_audit_event",
        lambda db, event_type, details, user_id: None,
    )

    payload = thesis_current_monitor.run_current_thesis_monitor(
        db_session,
        user_id=1,
        instruments=None,
        horizon_bars=8,
        recent_bars_window=7,
        thesis_count=1,
        prefer_recent=True,
    )

    assert payload["thesis_count"] == 1
    thesis = payload["theses"][0]
    assert thesis["monitor_status"] == "monitoring"
    assert datetime.fromisoformat(thesis["suggested_exit_time"]) > datetime.fromisoformat(
        thesis["latest_event_time"]
    )
    assert all(event["event_type"] != "exit_snapshot" for event in thesis["monitoring_events"])

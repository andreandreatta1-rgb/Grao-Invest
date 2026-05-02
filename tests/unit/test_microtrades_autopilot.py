from __future__ import annotations

from collections.abc import Generator

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.services.microtrades_autopilot import (
    build_microtrades_autopilot_config,
    create_decision_with_cooldown,
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

from __future__ import annotations

from collections.abc import Generator

import app.models  # noqa: F401
import pytest
from app.db import Base
from app.services.assistant_decisions import (
    answer_decision,
    create_decision,
    decision_inbox_payload,
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


def test_decision_inbox_creates_and_answers_decision(db_session: Session) -> None:
    created = create_decision(
        db=db_session,
        user_id=1,
        title="Plano de acompanhamento",
        context="Usuario ficara fora por 5 horas.",
        question="Podemos rodar o monitor intensivo?",
        options=[
            {"option_id": "A", "label": "Rodar monitor intensivo"},
            {"option_id": "B", "label": "Apenas observar"},
        ],
        priority="high",
    )

    inbox = decision_inbox_payload(db=db_session, user_id=1)
    assert inbox["summary"]["pending_count"] == 1
    assert inbox["decisions"][0]["decision_id"] == created["decision_id"]
    assert inbox["decisions"][0]["status"] == "pending"

    answered = answer_decision(
        db=db_session,
        user_id=1,
        decision_id=created["decision_id"],
        option_id="A",
        free_text="Pode seguir.",
    )

    refreshed = decision_inbox_payload(db=db_session, user_id=1)
    assert answered["status"] == "answered"
    assert answered["answer"]["option_id"] == "A"
    assert answered["answer"]["option_label"] == "Rodar monitor intensivo"
    assert refreshed["summary"]["pending_count"] == 0
    assert refreshed["summary"]["answered_count"] == 1


def test_seed_away_plan_reuses_pending_decision(db_session: Session) -> None:
    from app.services.assistant_decisions import seed_away_plan_decision

    first = seed_away_plan_decision(db=db_session, user_id=1)
    second = seed_away_plan_decision(db=db_session, user_id=1)

    assert first["decision_id"] == second["decision_id"]

    answer_decision(
        db=db_session,
        user_id=1,
        decision_id=first["decision_id"],
        option_id="A",
        free_text="Pode seguir.",
    )

    third = seed_away_plan_decision(db=db_session, user_id=1)

    assert third["decision_id"] != first["decision_id"]

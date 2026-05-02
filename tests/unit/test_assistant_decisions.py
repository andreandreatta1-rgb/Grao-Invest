from __future__ import annotations

from pathlib import Path

from app.services.assistant_decisions import (
    answer_decision,
    create_decision,
    decision_inbox_payload,
)


def test_decision_inbox_creates_and_answers_decision(tmp_path: Path) -> None:
    store_path = tmp_path / "assistant_decisions.json"

    created = create_decision(
        store_path=store_path,
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

    inbox = decision_inbox_payload(store_path=store_path, user_id=1)
    assert inbox["summary"]["pending_count"] == 1
    assert inbox["decisions"][0]["decision_id"] == created["decision_id"]
    assert inbox["decisions"][0]["status"] == "pending"

    answered = answer_decision(
        store_path=store_path,
        user_id=1,
        decision_id=created["decision_id"],
        option_id="A",
        free_text="Pode seguir.",
    )

    refreshed = decision_inbox_payload(store_path=store_path, user_id=1)
    assert answered["status"] == "answered"
    assert answered["answer"]["option_id"] == "A"
    assert answered["answer"]["option_label"] == "Rodar monitor intensivo"
    assert refreshed["summary"]["pending_count"] == 0
    assert refreshed["summary"]["answered_count"] == 1

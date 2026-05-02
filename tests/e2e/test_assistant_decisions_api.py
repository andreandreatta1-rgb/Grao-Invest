from __future__ import annotations


def test_assistant_decision_api_roundtrip(client) -> None:
    before_response = client.get("/api/assistant/decisions")
    assert before_response.status_code == 200
    before_pending = before_response.json()["summary"]["pending_count"]

    create_response = client.post(
        "/api/assistant/decisions",
        json={
            "title": "Decisao remota",
            "context": "Usuario esta fora do notebook.",
            "question": "Pode seguir com o monitor intensivo?",
            "options": [
                {"option_id": "A", "label": "Pode seguir"},
                {"option_id": "B", "label": "Aguardar"},
            ],
            "priority": "high",
        },
    )
    assert create_response.status_code == 200
    decision = create_response.json()
    assert decision["status"] == "pending"

    inbox_response = client.get("/api/assistant/decisions")
    assert inbox_response.status_code == 200
    inbox = inbox_response.json()
    assert inbox["summary"]["pending_count"] == before_pending + 1

    answer_response = client.post(
        f"/api/assistant/decisions/{decision['decision_id']}/answer",
        json={"option_id": "A", "free_text": "Aprovado pelo celular."},
    )
    assert answer_response.status_code == 200
    answered = answer_response.json()
    assert answered["status"] == "answered"
    assert answered["answer"]["option_label"] == "Pode seguir"

    refreshed_response = client.get("/api/assistant/decisions")
    assert refreshed_response.status_code == 200
    assert refreshed_response.json()["summary"]["pending_count"] == before_pending

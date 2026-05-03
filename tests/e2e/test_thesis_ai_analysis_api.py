from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_thesis_ai_analysis_endpoint_returns_payload(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_build_thesis_ai_analysis(
        db: object,
        *,
        user_id: int,
        instrument: str,
        question: str | None = None,
        horizon_days: int = 20,
    ) -> dict[str, Any]:
        return {
            "instrument": instrument,
            "asset_class": "stock",
            "summary": f"Analise de {instrument}",
            "thesis": question or "Tese padrao",
            "evidence": ["Sinal interno"],
            "risks": ["Risco de mercado"],
            "triggers": ["Mudanca de tendencia"],
            "exit_conditions": ["Stop tecnico"],
            "macro_context": {"status": "available"},
            "confidence_score": 0.7,
            "education_disclaimer": "Conteudo educacional; nao e recomendacao de investimento.",
            "sources": ["fixture"],
            "provider": "local_fallback",
            "horizon_days": horizon_days,
        }

    monkeypatch.setattr(
        "app.main.build_thesis_ai_analysis",
        fake_build_thesis_ai_analysis,
        raising=False,
    )

    response = client.post(
        "/api/theses/ai-analysis",
        json={
            "user_id": 1,
            "instrument": "PETR4",
            "question": "Quais pontos observar?",
            "horizon_days": 15,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["instrument"] == "PETR4"
    assert payload["horizon_days"] == 15
    assert "nao e recomendacao de investimento" in payload["education_disclaimer"]

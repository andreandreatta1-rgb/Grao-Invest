from __future__ import annotations

from app.services.thesis_operation_revaluation import build_operation_revaluation


def _thesis(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "thesis_id": "TH-PETR4-1",
        "instrument": "PETR4",
        "direction": "bullish",
        "entry_price": 40.0,
        "target_price": 44.0,
        "stop_price": 38.0,
        "confidence_tese_pct": 72.0,
        "expected_financial_pct": 4.0,
        "support_rate_pct": 62.0,
        "technical_support_pct": 78.0,
        "fundamental_support_pct": 82.0,
        "news_support_pct": 74.0,
        "fundamental_available": True,
        "news_available": True,
        "geo_oil_available": True,
    }
    payload.update(overrides)
    return payload


def test_revaluation_keeps_confirmed_operation_under_control() -> None:
    result = build_operation_revaluation(
        _thesis(),
        latest_price=41.2,
        monitor_status="monitoring",
        unrealized_financial_pct=2.1,
        progress_to_target_pct=30.0,
        distance_to_stop_pct=8.0,
    )

    assert result["executive_status"] == "mantida"
    assert result["executive_status_label"] == "Mantida"
    assert result["suggested_action"] == "manter_monitoramento"
    assert result["confidence_now_pct"] >= 72.0


def test_revaluation_flags_exit_review_when_target_is_near() -> None:
    result = build_operation_revaluation(
        _thesis(),
        latest_price=43.7,
        monitor_status="monitoring",
        unrealized_financial_pct=4.4,
        progress_to_target_pct=92.5,
        distance_to_stop_pct=14.2,
    )

    assert result["executive_status"] == "revisar_saida"
    assert result["executive_status_label"] == "Revisar saida"
    assert result["suggested_action"] == "avaliar_realizacao_parcial_ou_total"
    assert "alvo" in result["next_trigger"].lower()


def test_revaluation_invalidates_low_support_negative_operation() -> None:
    result = build_operation_revaluation(
        _thesis(
            instrument="BPAC11",
            support_rate_pct=30.0,
            technical_support_pct=95.0,
            fundamental_available=False,
            news_available=False,
        ),
        latest_price=37.6,
        monitor_status="stop_alert",
        unrealized_financial_pct=-2.4,
        progress_to_target_pct=-60.0,
        distance_to_stop_pct=-0.8,
    )

    assert result["executive_status"] == "invalidada"
    assert result["executive_status_label"] == "Invalidada"
    assert result["suggested_action"] == "encerrar_ou_reduzir_risco"
    assert result["confidence_now_pct"] < 72.0
    assert "missing_confirmation_inputs" in result["risk_flags"]

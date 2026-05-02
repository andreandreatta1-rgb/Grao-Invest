from __future__ import annotations

import json
from pathlib import Path

from app.services.thesis_postmortem import persist_case_study_postmortem


def _case_payload(*, thesis_id: str) -> dict[str, object]:
    return {
        "pipeline": {
            "policy": {
                "active_policy": "anti_blindspot_v3_soft",
            }
        },
        "selected_case": {
            "thesis": {
                "thesis_id": thesis_id,
                "instrument": "BPAC11",
                "direction": "bullish",
                "entry_price": 58.55,
                "confidence_tese_pct": 71.3538,
                "expected_financial_pct": 3.7916,
                "support_rate_pct": 30.2632,
                "technical_support_pct": 95.0,
                "fundamental_support_pct": 50.0,
                "news_support_pct": 50.0,
                "fundamental_available": False,
                "news_available": False,
                "geo_oil_available": False,
            },
            "structured_operation": {
                "strategy_id": "BULL_CALL_SPREAD",
                "strategy_name": "Bull Call Spread",
                "max_gain_pct": 5.4,
                "max_loss_pct": 2.2,
                "breakeven_price": 60.07,
            },
            "outcome": {
                "exit_price": 53.7,
                "success": False,
                "realized_financial_pct": -2.2,
                "exit_reason": "target_or_window_close",
            },
            "kpis": {
                "confidence_tese_pct": 71.3538,
                "expected_financial_pct": 3.7916,
                "realized_financial_pct": -2.2,
            },
            "effective_result_reason": (
                "Resultado efetivo abaixo do esperado para a tese no horizonte analisado. "
                "Foram observados 6 eventos de risco alto no monitoramento."
            ),
            "monitoring_timeline": [
                {
                    "event_time": "2019-09-30T00:00:00+00:00",
                    "event_type": "entry_snapshot",
                    "severity": "info",
                    "message": "Operacao estruturada iniciada em simulacao.",
                    "market_price": 58.55,
                },
                {
                    "event_time": "2019-10-03T00:00:00+00:00",
                    "event_type": "stop_risk_warning",
                    "severity": "high",
                    "message": "Preco entrou na zona de invalidacao da tese bullish.",
                    "market_price": 54.15,
                },
                {
                    "event_time": "2019-10-04T00:00:00+00:00",
                    "event_type": "stop_risk_warning",
                    "severity": "high",
                    "message": "Preco entrou na zona de invalidacao da tese bullish.",
                    "market_price": 51.75,
                },
                {
                    "event_time": "2019-10-07T00:00:00+00:00",
                    "event_type": "stop_risk_warning",
                    "severity": "high",
                    "message": "Preco entrou na zona de invalidacao da tese bullish.",
                    "market_price": 50.62,
                },
                {
                    "event_time": "2019-10-10T00:00:00+00:00",
                    "event_type": "exit_snapshot",
                    "severity": "info",
                    "message": "Encerramento da simulacao da estrutura BULL_CALL_SPREAD.",
                    "market_price": 53.7,
                },
            ],
        },
        "knowledge_skill": {
            "skill_name": "SSE_BPAC11_bullish_BULL_CALL_SPREAD",
        },
        "disclaimer": "educacional",
    }


def test_persist_case_study_postmortem_generates_shadow_profile(tmp_path: Path) -> None:
    latest_path = tmp_path / "thesis_postmortem_latest.json"
    log_path = tmp_path / "thesis_postmortem_log.jsonl"
    shadow_profile_path = tmp_path / "thesis_postmortem_shadow_profile.json"

    first = persist_case_study_postmortem(
        _case_payload(thesis_id="TH-BPAC11-1"),
        latest_path=latest_path,
        log_path=log_path,
        shadow_profile_path=shadow_profile_path,
    )
    second = persist_case_study_postmortem(
        _case_payload(thesis_id="TH-BPAC11-2"),
        latest_path=latest_path,
        log_path=log_path,
        shadow_profile_path=shadow_profile_path,
    )

    assert latest_path.exists()
    assert log_path.exists()
    assert shadow_profile_path.exists()
    assert "early_invalidation" in first["analysis_tags"]
    assert "missing_confirmation_inputs" in first["analysis_tags"]
    assert "confidence_overweighted_by_technical" in first["analysis_tags"]
    assert "repeat_failure_signature" in second["analysis_tags"]

    shadow_profile = json.loads(shadow_profile_path.read_text(encoding="utf-8"))
    assert shadow_profile["sample_size"] == 2
    assert any(
        rule["condition"] == "confidence_overweighted_by_technical"
        for rule in shadow_profile["condition_rules"]
    )
    assert any(
        item["signature"] == second["signature"] for item in shadow_profile["blocked_signatures"]
    )

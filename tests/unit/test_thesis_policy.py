from __future__ import annotations

from pathlib import Path

from app.services.thesis_policy import (
    apply_active_policy,
    default_policy_state,
    load_policy_state,
    save_policy_state,
)


def _thesis(
    *,
    thesis_id: str,
    confidence: float,
    expected: float,
    direction: str = "bullish",
    support_rate: float,
    news_support: float = 60.0,
    technical_support: float = 65.0,
    fundamental_support: float = 60.0,
    fundamental_available: bool = True,
    news_available: bool = True,
    geo_oil_available: bool = True,
    instrument: str = "PETR4",
) -> dict[str, object]:
    return {
        "thesis_id": thesis_id,
        "instrument": instrument,
        "direction": direction,
        "confidence_tese_pct": confidence,
        "expected_financial_pct": expected,
        "support_rate_pct": support_rate,
        "news_support_pct": news_support,
        "technical_support_pct": technical_support,
        "fundamental_support_pct": fundamental_support,
        "fundamental_available": fundamental_available,
        "news_available": news_available,
        "geo_oil_available": geo_oil_available,
    }


def test_apply_active_policy_uses_v3_soft_and_filters_risky_cases(tmp_path: Path) -> None:
    state = default_policy_state()
    state["active_policy"] = "anti_blindspot_v3_soft"
    state_path = tmp_path / "thesis_policy_state.json"
    save_policy_state(state, state_path)

    theses = [
        _thesis(
            thesis_id="TH-GOOD",
            confidence=72.0,
            expected=2.1,
            support_rate=62.0,
            geo_oil_available=True,
        ),
        _thesis(
            thesis_id="TH-SUPPORT-LOW",
            confidence=72.0,
            expected=2.1,
            support_rate=22.0,
            geo_oil_available=True,
        ),
        _thesis(
            thesis_id="TH-CONF-ADJ-LOW",
            confidence=55.5,
            expected=1.4,
            support_rate=44.0,
            news_support=40.0,
            fundamental_support=44.0,
            fundamental_available=False,
            news_available=False,
            geo_oil_available=False,
        ),
    ]

    selected, metadata = apply_active_policy(theses, state_path)

    assert len(selected) == 1
    assert selected[0]["thesis_id"] == "TH-GOOD"
    assert metadata["active_policy"] == "anti_blindspot_v3_soft"
    assert metadata["selected_count"] == 1
    assert metadata["fallback_used"] is False
    assert metadata["top_rejection_reasons"] != []


def test_apply_active_policy_falls_back_to_baseline_when_needed(tmp_path: Path) -> None:
    state = default_policy_state()
    state["active_policy"] = "anti_blindspot_v3_soft"
    state_path = tmp_path / "thesis_policy_state.json"
    save_policy_state(state, state_path)

    theses = [
        _thesis(
            thesis_id="TH-FALLBACK",
            confidence=62.0,
            expected=1.2,
            support_rate=20.0,
            geo_oil_available=False,
        )
    ]

    selected, metadata = apply_active_policy(theses, state_path)

    assert len(selected) == 1
    assert selected[0]["thesis_id"] == "TH-FALLBACK"
    assert metadata["active_policy"] == "anti_blindspot_v3_soft"
    assert metadata["fallback_used"] is True


def test_apply_active_policy_uses_postmortem_shadow_v1_and_blocks_bad_signature(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state = default_policy_state()
    state["active_policy"] = "postmortem_shadow_v1"
    state_path = tmp_path / "thesis_policy_state.json"
    save_policy_state(state, state_path)

    shadow_profile_path = tmp_path / "thesis_postmortem_shadow_profile.json"
    shadow_profile_path.write_text(
        """
        {
          "generated_at": "2026-05-02T00:00:00+00:00",
          "sample_size": 4,
          "overall_failure_rate_pct": 75.0,
          "overall_avg_expected_vs_real_gap_pct": 3.4,
          "condition_rules": [
            {
              "condition": "confidence_overweighted_by_technical",
              "sample_count": 4,
              "failure_rate_pct": 100.0,
              "avg_expected_vs_real_gap_pct": 4.5,
              "penalty_points": 4.0,
              "rationale": "Condicao degradada no shadow de postmortem."
            }
          ],
          "blocked_signatures": [
            {
              "signature": "BPAC11|bullish|support_lt35|confirm_missing_both|tech_ge90",
              "sample_count": 2,
              "failure_count": 2,
              "success_rate_pct": 0.0,
              "avg_expected_vs_real_gap_pct": 5.0,
              "rationale": "Assinatura repetiu falha e deve ser bloqueada no shadow."
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.thesis_postmortem._DEFAULT_POSTMORTEM_SHADOW_PROFILE_PATH",
        shadow_profile_path,
    )

    theses = [
        _thesis(
            thesis_id="TH-BLOCKED",
            confidence=72.0,
            expected=3.8,
            support_rate=30.0,
            technical_support=95.0,
            fundamental_support=50.0,
            news_support=50.0,
            fundamental_available=False,
            news_available=False,
            geo_oil_available=False,
            instrument="BPAC11",
        ),
        _thesis(
            thesis_id="TH-GOOD",
            confidence=72.0,
            expected=2.1,
            support_rate=62.0,
            technical_support=70.0,
            fundamental_support=60.0,
            news_support=61.0,
            fundamental_available=True,
            news_available=True,
            geo_oil_available=True,
            instrument="PETR4",
        ),
    ]

    selected, metadata = apply_active_policy(theses, state_path)

    assert len(selected) == 1
    assert selected[0]["thesis_id"] == "TH-GOOD"
    assert metadata["active_policy"] == "postmortem_shadow_v1"
    assert any(reason == "postmortem_blocked_signature" for reason, _ in metadata["top_rejection_reasons"])


def test_load_policy_state_returns_default_when_file_is_invalid(tmp_path: Path) -> None:
    state_path = tmp_path / "invalid_policy.json"
    state_path.write_text("{invalid-json", encoding="utf-8")

    loaded = load_policy_state(state_path)

    assert loaded["active_policy"] == "baseline"
    assert loaded["shadow_policy"] == "anti_blindspot_v3_soft"

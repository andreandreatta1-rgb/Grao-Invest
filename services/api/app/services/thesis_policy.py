from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

from app.services.thesis_postmortem import (
    is_postmortem_signature_blocked,
    load_postmortem_shadow_profile,
    postmortem_shadow_penalty_points,
)

_OIL_SENSITIVE_INSTRUMENTS = {
    "PETR4",
    "PRIO3",
    "RECV3",
    "VBBR3",
    "UGPA3",
}

_DEFAULT_POLICY_STATE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_policy_state.json"
)

PolicyName = Literal[
    "baseline",
    "anti_blindspot_v1",
    "anti_blindspot_v2_balanced",
    "anti_blindspot_v3_soft",
    "postmortem_shadow_v1",
]


class PromotionCriteria(TypedDict):
    min_discovery_pct: float
    min_success_uplift_pp: float
    min_selected_count: int
    required_stable_cycles: int


class ShadowCycleRecord(TypedDict):
    run_at: str
    shadow_policy: str
    evaluated_candidates: int
    selected_count: int
    success_rate_pct: float
    discovery_rate_pct: float
    success_uplift_pp: float
    discovery_delta_pp: float
    passed: bool


class ThesisPolicyState(TypedDict):
    updated_at: str
    active_policy: str
    shadow_policy: str | None
    shadow_status: str
    stable_pass_count: int
    promotion_criteria: PromotionCriteria
    cycle_history: list[ShadowCycleRecord]


class AppliedPolicyMetadata(TypedDict):
    active_policy: str
    source: str
    input_count: int
    selected_count: int
    rejected_count: int
    fallback_used: bool
    top_rejection_reasons: list[tuple[str, int]]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def default_policy_state() -> ThesisPolicyState:
    return {
        "updated_at": _utc_now_iso(),
        "active_policy": "baseline",
        "shadow_policy": "anti_blindspot_v3_soft",
        "shadow_status": "running",
        "stable_pass_count": 0,
        "promotion_criteria": {
            "min_discovery_pct": 50.0,
            "min_success_uplift_pp": 10.0,
            "min_selected_count": 50,
            "required_stable_cycles": 2,
        },
        "cycle_history": [],
    }


def load_policy_state(state_path: Path | None = None) -> ThesisPolicyState:
    path = state_path or _DEFAULT_POLICY_STATE_PATH
    if not path.exists():
        return default_policy_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_policy_state()
    if not isinstance(payload, dict):
        return default_policy_state()
    state = default_policy_state()
    state["updated_at"] = str(payload.get("updated_at", state["updated_at"]))
    state["active_policy"] = str(payload.get("active_policy", state["active_policy"]))
    shadow_policy_raw = payload.get("shadow_policy")
    if shadow_policy_raw is None:
        state["shadow_policy"] = None
    else:
        state["shadow_policy"] = str(shadow_policy_raw)
    state["shadow_status"] = str(payload.get("shadow_status", state["shadow_status"]))
    stable_pass_count_raw = payload.get("stable_pass_count", state["stable_pass_count"])
    if isinstance(stable_pass_count_raw, int):
        state["stable_pass_count"] = max(stable_pass_count_raw, 0)
    criteria_raw = payload.get("promotion_criteria")
    if isinstance(criteria_raw, dict):
        criteria = state["promotion_criteria"]
        min_discovery = criteria_raw.get("min_discovery_pct", criteria["min_discovery_pct"])
        min_success = criteria_raw.get("min_success_uplift_pp", criteria["min_success_uplift_pp"])
        min_selected = criteria_raw.get("min_selected_count", criteria["min_selected_count"])
        required_cycles = criteria_raw.get(
            "required_stable_cycles",
            criteria["required_stable_cycles"],
        )
        if isinstance(min_discovery, (int, float)):
            criteria["min_discovery_pct"] = float(min_discovery)
        if isinstance(min_success, (int, float)):
            criteria["min_success_uplift_pp"] = float(min_success)
        if isinstance(min_selected, int):
            criteria["min_selected_count"] = max(min_selected, 1)
        if isinstance(required_cycles, int):
            criteria["required_stable_cycles"] = max(required_cycles, 1)
    history_raw = payload.get("cycle_history")
    if isinstance(history_raw, list):
        normalized_history: list[ShadowCycleRecord] = []
        for item in history_raw:
            if not isinstance(item, dict):
                continue
            run_at = item.get("run_at")
            shadow_policy = item.get("shadow_policy")
            evaluated = item.get("evaluated_candidates")
            selected = item.get("selected_count")
            success_rate = item.get("success_rate_pct")
            discovery_rate = item.get("discovery_rate_pct")
            success_uplift = item.get("success_uplift_pp")
            discovery_delta = item.get("discovery_delta_pp")
            passed = item.get("passed")
            if not isinstance(run_at, str):
                continue
            if not isinstance(shadow_policy, str):
                continue
            if not isinstance(evaluated, int) or not isinstance(selected, int):
                continue
            if not isinstance(success_rate, (int, float)):
                continue
            if not isinstance(discovery_rate, (int, float)):
                continue
            if not isinstance(success_uplift, (int, float)):
                continue
            if not isinstance(discovery_delta, (int, float)):
                continue
            if not isinstance(passed, bool):
                continue
            normalized_history.append(
                {
                    "run_at": run_at,
                    "shadow_policy": shadow_policy,
                    "evaluated_candidates": evaluated,
                    "selected_count": selected,
                    "success_rate_pct": float(success_rate),
                    "discovery_rate_pct": float(discovery_rate),
                    "success_uplift_pp": float(success_uplift),
                    "discovery_delta_pp": float(discovery_delta),
                    "passed": passed,
                }
            )
        state["cycle_history"] = normalized_history[-50:]
    return state


def save_policy_state(
    state: ThesisPolicyState,
    state_path: Path | None = None,
) -> Path:
    path = state_path or _DEFAULT_POLICY_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def _float_value(thesis: Mapping[str, object], key: str, fallback: float = 0.0) -> float:
    value = thesis.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def _bool_value(thesis: Mapping[str, object], key: str, fallback: bool = False) -> bool:
    value = thesis.get(key)
    if isinstance(value, bool):
        return value
    return fallback


def _str_value(thesis: Mapping[str, object], key: str, fallback: str = "") -> str:
    value = thesis.get(key)
    if isinstance(value, str):
        return value
    return fallback


def _baseline_policy(thesis: Mapping[str, object]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _float_value(thesis, "confidence_tese_pct") < 55.0:
        reasons.append("confidence_below_baseline")
    if _float_value(thesis, "expected_financial_pct") <= 0.0:
        reasons.append("expected_non_positive")
    return len(reasons) == 0, reasons


def _anti_blindspot_v1_policy(thesis: Mapping[str, object]) -> tuple[bool, list[str]]:
    baseline_ok, baseline_reasons = _baseline_policy(thesis)
    if not baseline_ok:
        return False, baseline_reasons
    reasons: list[str] = []
    if _float_value(thesis, "support_rate_pct") < 50.0:
        reasons.append("low_support_rate")
    if _float_value(thesis, "news_support_pct") < 52.0:
        reasons.append("low_news_support")
    if _float_value(thesis, "expected_financial_pct") > 3.5:
        reasons.append("expected_overstretch")
    if _bool_value(thesis, "fundamental_available"):
        if _float_value(thesis, "fundamental_support_pct") < 55.0:
            reasons.append("low_fundamental_support")
    elif _float_value(thesis, "confidence_tese_pct") < 68.0:
        reasons.append("confidence_too_low_without_fundamental")
    instrument = _str_value(thesis, "instrument").upper()
    if instrument in _OIL_SENSITIVE_INSTRUMENTS and not _bool_value(thesis, "geo_oil_available"):
        reasons.append("geo_oil_missing_for_oil_asset")
    return len(reasons) == 0, reasons


def _anti_blindspot_v2_balanced_policy(thesis: Mapping[str, object]) -> tuple[bool, list[str]]:
    baseline_ok, baseline_reasons = _baseline_policy(thesis)
    if not baseline_ok:
        return False, baseline_reasons
    reasons: list[str] = []
    confidence = _float_value(thesis, "confidence_tese_pct")
    if _float_value(thesis, "support_rate_pct") < 45.0:
        reasons.append("low_support_rate_hard")
    if _bool_value(thesis, "news_available") and _float_value(thesis, "news_support_pct") < 45.0:
        reasons.append("low_news_support_hard")
    if _bool_value(thesis, "fundamental_available"):
        if _float_value(thesis, "fundamental_support_pct") < 50.0:
            reasons.append("low_fundamental_support_hard")
    elif confidence < 62.0 and _float_value(thesis, "technical_support_pct") < 57.0:
        reasons.append("confidence_and_technical_low_without_fundamental")
    if _float_value(thesis, "expected_financial_pct") > 5.0 and confidence < 70.0:
        reasons.append("expected_overstretch_low_confidence")
    instrument = _str_value(thesis, "instrument").upper()
    if (
        instrument in _OIL_SENSITIVE_INSTRUMENTS
        and not _bool_value(thesis, "geo_oil_available")
        and confidence < 74.0
    ):
        reasons.append("geo_oil_missing_low_confidence")
    return len(reasons) == 0, reasons


def _soft_penalty_points(thesis: Mapping[str, object]) -> float:
    points = 0.0
    if _float_value(thesis, "support_rate_pct") < 50.0:
        points += 3.0
    if _bool_value(thesis, "news_available"):
        if _float_value(thesis, "news_support_pct") < 50.0:
            points += 2.5
    else:
        points += 1.5
    if _bool_value(thesis, "fundamental_available"):
        if _float_value(thesis, "fundamental_support_pct") < 52.0:
            points += 3.5
    else:
        points += 2.0
    if _float_value(thesis, "expected_financial_pct") > 4.5:
        points += 3.5
    instrument = _str_value(thesis, "instrument").upper()
    if instrument in _OIL_SENSITIVE_INSTRUMENTS and not _bool_value(thesis, "geo_oil_available"):
        points += 4.0
    if (
        not _bool_value(thesis, "fundamental_available")
        and _float_value(thesis, "confidence_tese_pct") < 65.0
    ):
        points += 1.5
    return points


def _anti_blindspot_v3_soft_policy(thesis: Mapping[str, object]) -> tuple[bool, list[str]]:
    baseline_ok, baseline_reasons = _baseline_policy(thesis)
    if not baseline_ok:
        return False, baseline_reasons
    reasons: list[str] = []
    if _float_value(thesis, "support_rate_pct") < 25.0:
        reasons.append("support_rate_critical_low")
    if (
        _float_value(thesis, "expected_financial_pct") > 8.0
        and _float_value(thesis, "technical_support_pct") < 55.0
    ):
        reasons.append("expected_overstretch_critical")
    adjusted_confidence = _float_value(thesis, "confidence_tese_pct") - _soft_penalty_points(thesis)
    if adjusted_confidence < 48.0:
        reasons.append("adjusted_confidence_too_low")
    return len(reasons) == 0, reasons


def _postmortem_shadow_v1_policy(thesis: Mapping[str, object]) -> tuple[bool, list[str]]:
    baseline_ok, baseline_reasons = _baseline_policy(thesis)
    if not baseline_ok:
        return False, baseline_reasons

    reasons: list[str] = []
    if _float_value(thesis, "support_rate_pct") < 25.0:
        reasons.append("support_rate_critical_low")

    profile = load_postmortem_shadow_profile()
    if is_postmortem_signature_blocked(thesis, profile):
        reasons.append("postmortem_blocked_signature")
        return False, reasons

    adjusted_confidence = _float_value(thesis, "confidence_tese_pct") - _soft_penalty_points(thesis)
    postmortem_penalty, matched_conditions = postmortem_shadow_penalty_points(thesis, profile)
    adjusted_confidence -= postmortem_penalty
    if adjusted_confidence < 50.0:
        reasons.extend(matched_conditions)
        reasons.append("postmortem_adjusted_confidence_too_low")

    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)
    return len(deduped_reasons) == 0, deduped_reasons


def evaluate_policy(
    thesis: Mapping[str, object],
    policy_name: str,
) -> tuple[bool, list[str]]:
    if policy_name == "baseline":
        return _baseline_policy(thesis)
    if policy_name == "anti_blindspot_v1":
        return _anti_blindspot_v1_policy(thesis)
    if policy_name == "anti_blindspot_v2_balanced":
        return _anti_blindspot_v2_balanced_policy(thesis)
    if policy_name == "anti_blindspot_v3_soft":
        return _anti_blindspot_v3_soft_policy(thesis)
    if policy_name == "postmortem_shadow_v1":
        return _postmortem_shadow_v1_policy(thesis)
    return _baseline_policy(thesis)


def apply_active_policy[TThesis: Mapping[str, object]](
    theses: list[TThesis],
    state_path: Path | None = None,
) -> tuple[list[TThesis], AppliedPolicyMetadata]:
    state = load_policy_state(state_path)
    active_policy = state["active_policy"]
    selected: list[TThesis] = []
    rejections = Counter[str]()
    for thesis in theses:
        accepted, reasons = evaluate_policy(thesis, active_policy)
        if accepted:
            selected.append(thesis)
            continue
        for reason in reasons:
            rejections[reason] += 1
    fallback_used = False
    if not selected and active_policy != "baseline":
        fallback_used = True
        for thesis in theses:
            accepted, _ = evaluate_policy(thesis, "baseline")
            if accepted:
                selected.append(thesis)
        if not selected:
            selected = list(theses)

    source = (
        "state_file"
        if (state_path or _DEFAULT_POLICY_STATE_PATH).exists()
        else "default"
    )
    metadata: AppliedPolicyMetadata = {
        "active_policy": active_policy,
        "source": source,
        "input_count": len(theses),
        "selected_count": len(selected),
        "rejected_count": max(len(theses) - len(selected), 0),
        "fallback_used": fallback_used,
        "top_rejection_reasons": rejections.most_common(8),
    }
    return selected, metadata

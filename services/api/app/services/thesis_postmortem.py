from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, TypedDict


_DEFAULT_POSTMORTEM_LATEST_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_postmortem_latest.json"
)
_DEFAULT_POSTMORTEM_LOG_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_postmortem_log.jsonl"
)
_DEFAULT_POSTMORTEM_SHADOW_PROFILE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_postmortem_shadow_profile.json"
)


class PostmortemConditionRule(TypedDict):
    condition: str
    sample_count: int
    failure_rate_pct: float
    avg_expected_vs_real_gap_pct: float
    penalty_points: float
    rationale: str


class PostmortemBlockedSignature(TypedDict):
    signature: str
    sample_count: int
    failure_count: int
    success_rate_pct: float
    avg_expected_vs_real_gap_pct: float
    rationale: str


class PostmortemShadowProfile(TypedDict):
    generated_at: str
    sample_size: int
    overall_failure_rate_pct: float
    overall_avg_expected_vs_real_gap_pct: float
    condition_rules: list[PostmortemConditionRule]
    blocked_signatures: list[PostmortemBlockedSignature]


class CaseStudyPostmortem(TypedDict):
    generated_at: str
    thesis_id: str
    instrument: str
    direction: str
    strategy_id: str
    policy_name: str
    signature: str
    success: bool
    confidence_tese_pct: float
    expected_financial_pct: float
    realized_financial_pct: float
    expected_vs_real_gap_pct: float
    market_move_pct: float
    structure_cushion_pct: float
    stop_risk_event_count: int
    high_risk_event_count: int
    early_invalidation: bool
    analysis_tags: list[str]
    learning_actions: list[str]
    shadow_profile_snapshot: dict[str, object]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _float_value(item: Mapping[str, object], key: str, fallback: float = 0.0) -> float:
    value = item.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def _bool_value(item: Mapping[str, object], key: str, fallback: bool = False) -> bool:
    value = item.get(key)
    if isinstance(value, bool):
        return value
    return fallback


def _str_value(item: Mapping[str, object], key: str, fallback: str = "") -> str:
    value = item.get(key)
    if isinstance(value, str):
        return value
    return fallback


def _support_rate_band(support_rate_pct: float) -> str:
    if support_rate_pct < 35.0:
        return "support_lt35"
    if support_rate_pct < 45.0:
        return "support_35_45"
    return "support_ge45"


def _confirmation_band(*, fundamental_available: bool, news_available: bool) -> str:
    if not fundamental_available and not news_available:
        return "confirm_missing_both"
    if fundamental_available and news_available:
        return "confirm_present"
    return "confirm_partial"


def thesis_signature_from_mapping(thesis: Mapping[str, object]) -> str:
    instrument = _str_value(thesis, "instrument").upper()
    direction = _str_value(thesis, "direction").lower()
    support_rate_pct = _float_value(thesis, "support_rate_pct")
    technical_support_pct = _float_value(thesis, "technical_support_pct")
    fundamental_available = _bool_value(thesis, "fundamental_available")
    news_available = _bool_value(thesis, "news_available")
    technical_band = "tech_ge90" if technical_support_pct >= 90.0 else "tech_lt90"
    return "|".join(
        [
            instrument or "UNKNOWN",
            direction or "unknown",
            _support_rate_band(support_rate_pct),
            _confirmation_band(
                fundamental_available=fundamental_available,
                news_available=news_available,
            ),
            technical_band,
        ]
    )


def candidate_postmortem_conditions(thesis: Mapping[str, object]) -> set[str]:
    confidence = _float_value(thesis, "confidence_tese_pct")
    support_rate_pct = _float_value(thesis, "support_rate_pct")
    technical_support_pct = _float_value(thesis, "technical_support_pct")
    expected_financial_pct = _float_value(thesis, "expected_financial_pct")
    fundamental_available = _bool_value(thesis, "fundamental_available")
    news_available = _bool_value(thesis, "news_available")

    conditions: set[str] = set()
    if not fundamental_available and not news_available:
        conditions.add("missing_confirmation_inputs")
    if support_rate_pct < 35.0:
        conditions.add("low_support_rate_band")
    if (
        confidence >= 70.0
        and technical_support_pct >= 90.0
        and support_rate_pct < 35.0
        and not fundamental_available
        and not news_available
    ):
        conditions.add("confidence_overweighted_by_technical")
    if expected_financial_pct > 3.5 and support_rate_pct < 35.0:
        conditions.add("expected_overstretch_without_confirmation")
    return conditions


def default_postmortem_shadow_profile() -> PostmortemShadowProfile:
    return {
        "generated_at": _utc_now_iso(),
        "sample_size": 0,
        "overall_failure_rate_pct": 0.0,
        "overall_avg_expected_vs_real_gap_pct": 0.0,
        "condition_rules": [],
        "blocked_signatures": [],
    }


def load_postmortem_shadow_profile(
    profile_path: Path | None = None,
) -> PostmortemShadowProfile:
    path = profile_path or _DEFAULT_POSTMORTEM_SHADOW_PROFILE_PATH
    if not path.exists():
        return default_postmortem_shadow_profile()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_postmortem_shadow_profile()
    if not isinstance(payload, dict):
        return default_postmortem_shadow_profile()
    profile = default_postmortem_shadow_profile()
    generated_at = payload.get("generated_at")
    sample_size = payload.get("sample_size")
    failure_rate = payload.get("overall_failure_rate_pct")
    avg_gap = payload.get("overall_avg_expected_vs_real_gap_pct")
    if isinstance(generated_at, str):
        profile["generated_at"] = generated_at
    if isinstance(sample_size, int):
        profile["sample_size"] = max(sample_size, 0)
    if isinstance(failure_rate, (int, float)):
        profile["overall_failure_rate_pct"] = float(failure_rate)
    if isinstance(avg_gap, (int, float)):
        profile["overall_avg_expected_vs_real_gap_pct"] = float(avg_gap)

    condition_rules_raw = payload.get("condition_rules")
    if isinstance(condition_rules_raw, list):
        rules: list[PostmortemConditionRule] = []
        for item in condition_rules_raw:
            if not isinstance(item, dict):
                continue
            condition = item.get("condition")
            sample_count = item.get("sample_count")
            failure_rate_pct = item.get("failure_rate_pct")
            avg_expected_vs_real_gap_pct = item.get("avg_expected_vs_real_gap_pct")
            penalty_points = item.get("penalty_points")
            rationale = item.get("rationale")
            if not isinstance(condition, str):
                continue
            if not isinstance(sample_count, int):
                continue
            if not isinstance(failure_rate_pct, (int, float)):
                continue
            if not isinstance(avg_expected_vs_real_gap_pct, (int, float)):
                continue
            if not isinstance(penalty_points, (int, float)):
                continue
            if not isinstance(rationale, str):
                continue
            rules.append(
                {
                    "condition": condition,
                    "sample_count": sample_count,
                    "failure_rate_pct": float(failure_rate_pct),
                    "avg_expected_vs_real_gap_pct": float(avg_expected_vs_real_gap_pct),
                    "penalty_points": float(penalty_points),
                    "rationale": rationale,
                }
            )
        profile["condition_rules"] = rules

    blocked_raw = payload.get("blocked_signatures")
    if isinstance(blocked_raw, list):
        blocked: list[PostmortemBlockedSignature] = []
        for item in blocked_raw:
            if not isinstance(item, dict):
                continue
            signature = item.get("signature")
            sample_count = item.get("sample_count")
            failure_count = item.get("failure_count")
            success_rate_pct = item.get("success_rate_pct")
            avg_expected_vs_real_gap_pct = item.get("avg_expected_vs_real_gap_pct")
            rationale = item.get("rationale")
            if not isinstance(signature, str):
                continue
            if not isinstance(sample_count, int):
                continue
            if not isinstance(failure_count, int):
                continue
            if not isinstance(success_rate_pct, (int, float)):
                continue
            if not isinstance(avg_expected_vs_real_gap_pct, (int, float)):
                continue
            if not isinstance(rationale, str):
                continue
            blocked.append(
                {
                    "signature": signature,
                    "sample_count": sample_count,
                    "failure_count": failure_count,
                    "success_rate_pct": float(success_rate_pct),
                    "avg_expected_vs_real_gap_pct": float(avg_expected_vs_real_gap_pct),
                    "rationale": rationale,
                }
            )
        profile["blocked_signatures"] = blocked

    return profile


def _load_postmortem_records(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean:
            continue
        try:
            payload = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _save_shadow_profile(
    records: list[dict[str, Any]],
    *,
    profile_path: Path,
) -> PostmortemShadowProfile:
    profile = default_postmortem_shadow_profile()
    if not records:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile, ensure_ascii=True, indent=2), encoding="utf-8")
        return profile

    failure_rates = [1.0 if not bool(item.get("success")) else 0.0 for item in records]
    gap_values = [float(item.get("expected_vs_real_gap_pct") or 0.0) for item in records]
    overall_failure_rate = mean(failure_rates) * 100.0
    overall_avg_gap = mean(gap_values)

    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        signature = str(item.get("signature") or "")
        if signature:
            by_signature[signature].append(item)
        for tag in item.get("analysis_tags", []):
            if isinstance(tag, str):
                by_condition[tag].append(item)

    condition_rules: list[PostmortemConditionRule] = []
    for condition, scoped in by_condition.items():
        sample_count = len(scoped)
        if sample_count < 2:
            continue
        failure_rate_pct = (
            sum(1 for item in scoped if not bool(item.get("success"))) / sample_count
        ) * 100.0
        avg_gap = mean(float(item.get("expected_vs_real_gap_pct") or 0.0) for item in scoped)
        if failure_rate_pct < overall_failure_rate:
            continue
        penalty_points = min(
            max(((failure_rate_pct - overall_failure_rate) * 0.08) + (avg_gap * 0.45), 1.0),
            6.0,
        )
        condition_rules.append(
            {
                "condition": condition,
                "sample_count": sample_count,
                "failure_rate_pct": round(failure_rate_pct, 4),
                "avg_expected_vs_real_gap_pct": round(avg_gap, 4),
                "penalty_points": round(penalty_points, 4),
                "rationale": "Condicao degradada pelo postmortem shadow.",
            }
        )

    blocked_signatures: list[PostmortemBlockedSignature] = []
    for signature, scoped in by_signature.items():
        sample_count = len(scoped)
        if sample_count < 2:
            continue
        failure_count = sum(1 for item in scoped if not bool(item.get("success")))
        success_rate_pct = ((sample_count - failure_count) / sample_count) * 100.0
        avg_gap = mean(float(item.get("expected_vs_real_gap_pct") or 0.0) for item in scoped)
        if failure_count < sample_count:
            continue
        if avg_gap < 1.0:
            continue
        blocked_signatures.append(
            {
                "signature": signature,
                "sample_count": sample_count,
                "failure_count": failure_count,
                "success_rate_pct": round(success_rate_pct, 4),
                "avg_expected_vs_real_gap_pct": round(avg_gap, 4),
                "rationale": "Assinatura repetiu falha e deve ser bloqueada no shadow.",
            }
        )

    profile = {
        "generated_at": _utc_now_iso(),
        "sample_size": len(records),
        "overall_failure_rate_pct": round(overall_failure_rate, 4),
        "overall_avg_expected_vs_real_gap_pct": round(overall_avg_gap, 4),
        "condition_rules": sorted(
            condition_rules,
            key=lambda item: (item["penalty_points"], item["sample_count"]),
            reverse=True,
        ),
        "blocked_signatures": sorted(
            blocked_signatures,
            key=lambda item: (item["failure_count"], item["sample_count"]),
            reverse=True,
        ),
    }
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, ensure_ascii=True, indent=2), encoding="utf-8")
    return profile


def _analysis_tags(
    thesis: Mapping[str, object],
    *,
    expected_vs_real_gap_pct: float,
    early_invalidation: bool,
    high_risk_event_count: int,
    structure_cushion_pct: float,
) -> list[str]:
    tags = sorted(candidate_postmortem_conditions(thesis))
    if early_invalidation:
        tags.append("early_invalidation")
    if high_risk_event_count >= 3:
        tags.append("risk_cluster_high")
    if expected_vs_real_gap_pct > 2.0:
        tags.append("expected_real_gap_negative")
    if structure_cushion_pct >= 2.0:
        tags.append("structure_limited_loss")
    return tags


def postmortem_shadow_penalty_points(
    thesis: Mapping[str, object],
    profile: PostmortemShadowProfile | None = None,
) -> tuple[float, list[str]]:
    active_profile = profile or load_postmortem_shadow_profile()
    candidate_conditions = candidate_postmortem_conditions(thesis)
    penalty_points = 0.0
    matched_conditions: list[str] = []
    for rule in active_profile["condition_rules"]:
        if rule["condition"] not in candidate_conditions:
            continue
        penalty_points += float(rule["penalty_points"])
        matched_conditions.append(rule["condition"])
    return round(min(penalty_points, 8.0), 4), matched_conditions


def is_postmortem_signature_blocked(
    thesis: Mapping[str, object],
    profile: PostmortemShadowProfile | None = None,
) -> bool:
    active_profile = profile or load_postmortem_shadow_profile()
    signature = thesis_signature_from_mapping(thesis)
    return any(item["signature"] == signature for item in active_profile["blocked_signatures"])


def persist_case_study_postmortem(
    payload: Mapping[str, object],
    *,
    latest_path: Path | None = None,
    log_path: Path | None = None,
    shadow_profile_path: Path | None = None,
) -> CaseStudyPostmortem:
    selected_case = payload.get("selected_case")
    selected_case_dict = selected_case if isinstance(selected_case, dict) else {}
    thesis = selected_case_dict.get("thesis")
    thesis_dict = thesis if isinstance(thesis, dict) else {}
    operation = selected_case_dict.get("structured_operation")
    operation_dict = operation if isinstance(operation, dict) else {}
    outcome = selected_case_dict.get("outcome")
    outcome_dict = outcome if isinstance(outcome, dict) else {}
    pipeline = payload.get("pipeline")
    pipeline_dict = pipeline if isinstance(pipeline, dict) else {}
    policy = pipeline_dict.get("policy")
    policy_dict = policy if isinstance(policy, dict) else {}

    entry_price = _float_value(thesis_dict, "entry_price")
    exit_price = _float_value(outcome_dict, "exit_price")
    expected_financial_pct = _float_value(
        selected_case_dict.get("kpis", {}) if isinstance(selected_case_dict.get("kpis"), dict) else {},
        "expected_financial_pct",
        _float_value(thesis_dict, "expected_financial_pct"),
    )
    realized_financial_pct = _float_value(
        selected_case_dict.get("kpis", {}) if isinstance(selected_case_dict.get("kpis"), dict) else {},
        "realized_financial_pct",
        _float_value(outcome_dict, "realized_financial_pct"),
    )
    confidence_tese_pct = _float_value(
        selected_case_dict.get("kpis", {}) if isinstance(selected_case_dict.get("kpis"), dict) else {},
        "confidence_tese_pct",
        _float_value(thesis_dict, "confidence_tese_pct"),
    )
    expected_vs_real_gap_pct = round(expected_financial_pct - realized_financial_pct, 4)
    market_move_pct = 0.0
    if entry_price > 0:
        market_move_pct = round(((exit_price - entry_price) / entry_price) * 100.0, 4)

    direction = _str_value(thesis_dict, "direction").lower()
    structure_cushion_pct = 0.0
    if direction == "bullish" and market_move_pct < 0.0:
        structure_cushion_pct = round(abs(market_move_pct) - abs(realized_financial_pct), 4)
    elif direction == "bearish" and market_move_pct > 0.0:
        structure_cushion_pct = round(abs(market_move_pct) - abs(realized_financial_pct), 4)

    monitoring_timeline = selected_case_dict.get("monitoring_timeline")
    monitoring_events = (
        [item for item in monitoring_timeline if isinstance(item, dict)]
        if isinstance(monitoring_timeline, list)
        else []
    )
    high_risk_event_count = sum(1 for event in monitoring_events if event.get("severity") == "high")
    stop_risk_event_count = sum(
        1 for event in monitoring_events if event.get("event_type") == "stop_risk_warning"
    )
    stop_indexes = [
        index
        for index, event in enumerate(monitoring_events)
        if event.get("event_type") == "stop_risk_warning"
    ]
    threshold_index = max(2, int(max(len(monitoring_events) - 1, 1) * 0.4))
    early_invalidation = bool(stop_indexes and stop_indexes[0] <= threshold_index)

    signature = thesis_signature_from_mapping(thesis_dict)
    success = _bool_value(outcome_dict, "success")
    analysis_tags = _analysis_tags(
        thesis_dict,
        expected_vs_real_gap_pct=expected_vs_real_gap_pct,
        early_invalidation=early_invalidation,
        high_risk_event_count=high_risk_event_count,
        structure_cushion_pct=structure_cushion_pct,
    )

    latest_output_path = latest_path or _DEFAULT_POSTMORTEM_LATEST_PATH
    log_output_path = log_path or _DEFAULT_POSTMORTEM_LOG_PATH
    shadow_output_path = shadow_profile_path or _DEFAULT_POSTMORTEM_SHADOW_PROFILE_PATH
    latest_output_path.parent.mkdir(parents=True, exist_ok=True)
    log_output_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_records = _load_postmortem_records(log_output_path)
    prior_signature_failures = sum(
        1
        for item in existing_records
        if item.get("signature") == signature and not bool(item.get("success"))
    )
    if not success and prior_signature_failures >= 1:
        analysis_tags.append("repeat_failure_signature")

    learning_actions = [
        f"shadow_rule::{tag}"
        for tag in analysis_tags
        if tag in {
            "missing_confirmation_inputs",
            "confidence_overweighted_by_technical",
            "early_invalidation",
            "repeat_failure_signature",
            "expected_real_gap_negative",
        }
    ]

    postmortem: CaseStudyPostmortem = {
        "generated_at": _utc_now_iso(),
        "thesis_id": _str_value(thesis_dict, "thesis_id"),
        "instrument": _str_value(thesis_dict, "instrument").upper(),
        "direction": direction,
        "strategy_id": _str_value(operation_dict, "strategy_id"),
        "policy_name": _str_value(policy_dict, "active_policy", "baseline"),
        "signature": signature,
        "success": success,
        "confidence_tese_pct": confidence_tese_pct,
        "expected_financial_pct": expected_financial_pct,
        "realized_financial_pct": realized_financial_pct,
        "expected_vs_real_gap_pct": expected_vs_real_gap_pct,
        "market_move_pct": market_move_pct,
        "structure_cushion_pct": structure_cushion_pct,
        "stop_risk_event_count": stop_risk_event_count,
        "high_risk_event_count": high_risk_event_count,
        "early_invalidation": early_invalidation,
        "analysis_tags": sorted(set(analysis_tags)),
        "learning_actions": sorted(set(learning_actions)),
        "shadow_profile_snapshot": {},
    }

    with log_output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(postmortem, ensure_ascii=True) + "\n")

    latest_output_path.write_text(
        json.dumps(postmortem, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    records = existing_records + [postmortem]
    shadow_profile = _save_shadow_profile(records, profile_path=shadow_output_path)
    postmortem["shadow_profile_snapshot"] = {
        "sample_size": shadow_profile["sample_size"],
        "condition_rule_count": len(shadow_profile["condition_rules"]),
        "blocked_signature_count": len(shadow_profile["blocked_signatures"]),
    }
    latest_output_path.write_text(
        json.dumps(postmortem, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return postmortem

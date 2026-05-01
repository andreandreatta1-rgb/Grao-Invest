from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from statistics import mean
from typing import TypedDict

from app.db import SessionLocal
from app.services.thesis_case_study import (
    RawCandidate,
    ThesisSummary,
    _available_instruments,
    _enriched_thesis_candidates,
    _raw_candidates_from_ticks,
    _ticks_for_instrument,
)

_OIL_SENSITIVE_INSTRUMENTS = {
    "PETR4",
    "PRIO3",
    "RECV3",
    "VBBR3",
    "UGPA3",
}


class CandidateEval(TypedDict):
    thesis_id: str
    instrument: str
    direction: str
    success_realized: bool
    realized_move_pct: float
    confidence_tese_pct: float
    expected_financial_pct: float
    support_rate_pct: float
    technical_support_pct: float
    fundamental_support_pct: float
    news_support_pct: float
    fundamental_available: bool
    news_available: bool
    geo_oil_available: bool


PolicyResult = tuple[bool, list[str]]
PolicyFn = Callable[[CandidateEval], PolicyResult]
_MIN_DISCOVERY_FOR_PROMOTION = 50.0
_MIN_SUCCESS_UPLIFT_FOR_PROMOTION = 10.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa experimento A/B para selecao de teses: baseline vs anti-blindspot, "
            "usando historico local point-in-time."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--instruments",
        type=str,
        default=None,
        help="Lista de ativos separados por virgula. Se omitido, usa universo da base.",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=12,
        help="Janela de barras para avaliacao historica.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=1500,
        help="Numero maximo de teses candidatas no experimento.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/thesis_ab_experiment_latest.json"),
        help="Arquivo JSON de saida do experimento.",
    )
    return parser.parse_args()


def _parse_instruments(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not values:
        raise SystemExit("Parametro --instruments informado sem ativos validos.")
    return values


def _baseline_policy(item: CandidateEval) -> bool:
    return item["confidence_tese_pct"] >= 55.0 and item["expected_financial_pct"] > 0.0


def _blindspot_rejection_reasons(item: CandidateEval) -> list[str]:
    reasons: list[str] = []
    if item["support_rate_pct"] < 50.0:
        reasons.append("low_support_rate")
    if item["news_support_pct"] < 52.0:
        reasons.append("low_news_support")
    if item["expected_financial_pct"] > 3.5:
        reasons.append("expected_overstretch")
    if item["fundamental_available"]:
        if item["fundamental_support_pct"] < 55.0:
            reasons.append("low_fundamental_support")
    else:
        if item["confidence_tese_pct"] < 68.0:
            reasons.append("confidence_too_low_without_fundamental")
    if item["instrument"] in _OIL_SENSITIVE_INSTRUMENTS and not item["geo_oil_available"]:
        reasons.append("geo_oil_missing_for_oil_asset")
    return reasons


def _anti_blindspot_v1_policy(item: CandidateEval) -> PolicyResult:
    if not _baseline_policy(item):
        return False, ["not_in_baseline"]
    reasons = _blindspot_rejection_reasons(item)
    return len(reasons) == 0, reasons


def _balanced_blindspot_rejection_reasons(item: CandidateEval) -> list[str]:
    reasons: list[str] = []
    if item["support_rate_pct"] < 45.0:
        reasons.append("low_support_rate_hard")
    if item["news_available"] and item["news_support_pct"] < 45.0:
        reasons.append("low_news_support_hard")
    if item["fundamental_available"]:
        if item["fundamental_support_pct"] < 50.0:
            reasons.append("low_fundamental_support_hard")
    elif item["confidence_tese_pct"] < 62.0 and item["technical_support_pct"] < 57.0:
        reasons.append("confidence_and_technical_low_without_fundamental")
    if item["expected_financial_pct"] > 5.0 and item["confidence_tese_pct"] < 70.0:
        reasons.append("expected_overstretch_low_confidence")
    if (
        item["instrument"] in _OIL_SENSITIVE_INSTRUMENTS
        and not item["geo_oil_available"]
        and item["confidence_tese_pct"] < 74.0
    ):
        reasons.append("geo_oil_missing_low_confidence")
    return reasons


def _anti_blindspot_v2_balanced_policy(item: CandidateEval) -> PolicyResult:
    if not _baseline_policy(item):
        return False, ["not_in_baseline"]
    reasons = _balanced_blindspot_rejection_reasons(item)
    return len(reasons) == 0, reasons


def _soft_penalty_points(item: CandidateEval) -> float:
    points = 0.0
    if item["support_rate_pct"] < 50.0:
        points += 3.0
    if item["news_available"]:
        if item["news_support_pct"] < 50.0:
            points += 2.5
    else:
        points += 1.5
    if item["fundamental_available"]:
        if item["fundamental_support_pct"] < 52.0:
            points += 3.5
    else:
        points += 2.0
    if item["expected_financial_pct"] > 4.5:
        points += 3.5
    if item["instrument"] in _OIL_SENSITIVE_INSTRUMENTS and not item["geo_oil_available"]:
        points += 4.0
    if not item["fundamental_available"] and item["confidence_tese_pct"] < 65.0:
        points += 1.5
    return points


def _anti_blindspot_v3_soft_policy(item: CandidateEval) -> PolicyResult:
    if not _baseline_policy(item):
        return False, ["not_in_baseline"]
    reasons: list[str] = []
    if item["support_rate_pct"] < 25.0:
        reasons.append("support_rate_critical_low")
    if item["expected_financial_pct"] > 8.0 and item["technical_support_pct"] < 55.0:
        reasons.append("expected_overstretch_critical")
    adjusted_confidence = item["confidence_tese_pct"] - _soft_penalty_points(item)
    if adjusted_confidence < 48.0:
        reasons.append("adjusted_confidence_too_low")
    return len(reasons) == 0, reasons


def _evaluate_policy(
    evaluated: list[CandidateEval],
    policy: PolicyFn,
) -> tuple[list[CandidateEval], Counter[str]]:
    selected: list[CandidateEval] = []
    rejections = Counter[str]()
    for item in evaluated:
        accepted, reasons = policy(item)
        if accepted:
            selected.append(item)
            continue
        for reason in reasons:
            if reason != "not_in_baseline":
                rejections[reason] += 1
    return selected, rejections


def _variant_quality_score(
    *,
    success_uplift_pp: float,
    discovery_delta_pp: float,
    discovery_rate_pct: float,
    selected_count: int,
) -> float:
    if selected_count < 50:
        return -1000.0
    # Discovery muito baixo tende a inviabilizar operacao, mesmo com sucesso alto.
    discovery_floor_penalty = 0.0
    if discovery_rate_pct < 40.0:
        discovery_floor_penalty = (40.0 - discovery_rate_pct) * 1.8
    return (success_uplift_pp * 1.0) + (discovery_delta_pp * 0.15) - discovery_floor_penalty


def _summary(selected: list[CandidateEval], total: int) -> dict[str, float | int]:
    if not selected:
        return {
            "selected_count": 0,
            "discovery_rate_pct": 0.0,
            "success_rate_pct": 0.0,
            "avg_confidence_pct": 0.0,
            "avg_expected_financial_pct": 0.0,
            "avg_realized_move_pct": 0.0,
            "positive_realized_move_rate_pct": 0.0,
        }
    success_rate = (sum(1 for item in selected if item["success_realized"]) / len(selected)) * 100.0
    positive_realized = (
        sum(1 for item in selected if item["realized_move_pct"] > 0.0) / len(selected)
    ) * 100.0
    return {
        "selected_count": len(selected),
        "discovery_rate_pct": round((len(selected) / max(total, 1)) * 100.0, 4),
        "success_rate_pct": round(success_rate, 4),
        "avg_confidence_pct": round(mean(item["confidence_tese_pct"] for item in selected), 4),
        "avg_expected_financial_pct": round(
            mean(item["expected_financial_pct"] for item in selected),
            4,
        ),
        "avg_realized_move_pct": round(mean(item["realized_move_pct"] for item in selected), 4),
        "positive_realized_move_rate_pct": round(positive_realized, 4),
    }


def _build_candidate_eval(
    *,
    raw: RawCandidate,
    thesis: ThesisSummary,
) -> CandidateEval:
    return {
        "thesis_id": thesis["thesis_id"],
        "instrument": thesis["instrument"],
        "direction": thesis["direction"],
        "success_realized": raw["success_realized"],
        "realized_move_pct": raw["realized_move_pct"],
        "confidence_tese_pct": thesis["confidence_tese_pct"],
        "expected_financial_pct": thesis["expected_financial_pct"],
        "support_rate_pct": thesis["support_rate_pct"],
        "technical_support_pct": thesis["technical_support_pct"],
        "fundamental_support_pct": thesis["fundamental_support_pct"],
        "news_support_pct": thesis["news_support_pct"],
        "fundamental_available": thesis["fundamental_available"],
        "news_available": thesis["news_available"],
        "geo_oil_available": thesis["geo_oil_available"],
    }


def main() -> None:
    args = parse_args()
    instruments = _parse_instruments(args.instruments)
    if args.max_candidates <= 0:
        raise SystemExit("--max-candidates deve ser maior que zero.")
    if args.horizon_bars < 3:
        raise SystemExit("--horizon-bars deve ser maior ou igual a 3.")

    with SessionLocal() as db:
        instrument_list = _available_instruments(db, instruments)
        if not instrument_list:
            raise SystemExit("Sem instrumentos para executar experimento A/B.")

        raw_candidates: list[RawCandidate] = []
        for instrument in instrument_list:
            ticks = _ticks_for_instrument(db, instrument)
            raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, args.horizon_bars))
        if not raw_candidates:
            raise SystemExit("Historico insuficiente para gerar candidatos de tese.")
        raw_candidates = sorted(
            raw_candidates,
            key=lambda item: str(item["entry_time"]),
            reverse=True,
        )[: args.max_candidates]
        raw_index: dict[str, RawCandidate] = {}
        for item in raw_candidates:
            key = (
                f"{item['instrument']}::{item['entry_index']}::{item['entry_time']}::"
                f"{item['direction']}::{item['horizon_bars']}"
            )
            raw_index[key] = item

        thesis_candidates = _enriched_thesis_candidates(db, raw_candidates)
        evaluated: list[CandidateEval] = []
        for thesis in thesis_candidates:
            key = (
                f"{thesis['instrument']}::{thesis['entry_index']}::{thesis['entry_time']}::"
                f"{thesis['direction']}::{thesis['horizon_bars']}"
            )
            raw = raw_index.get(key)
            if raw is None:
                continue
            evaluated.append(_build_candidate_eval(raw=raw, thesis=thesis))

    policy_variants: dict[str, PolicyFn] = {
        "anti_blindspot_v1": _anti_blindspot_v1_policy,
        "anti_blindspot_v2_balanced": _anti_blindspot_v2_balanced_policy,
        "anti_blindspot_v3_soft": _anti_blindspot_v3_soft_policy,
    }

    baseline_selected = [item for item in evaluated if _baseline_policy(item)]
    baseline_summary = _summary(baseline_selected, len(evaluated))
    variants_summary: dict[str, dict[str, float | int]] = {"baseline": baseline_summary}
    rejection_reasons_by_variant: dict[str, list[tuple[str, int]]] = {}
    comparison_vs_baseline: dict[str, dict[str, float | int]] = {}

    recommendation = "baseline"
    best_quality_score = 0.0
    baseline_success = float(baseline_summary["success_rate_pct"])
    baseline_discovery = float(baseline_summary["discovery_rate_pct"])
    promotion_candidates: list[tuple[str, float, float]] = []

    for variant_name, policy in policy_variants.items():
        selected, rejections = _evaluate_policy(evaluated, policy)
        summary = _summary(selected, len(evaluated))
        variants_summary[variant_name] = summary
        rejection_reasons_by_variant[variant_name] = rejections.most_common(8)
        success_uplift = round(float(summary["success_rate_pct"]) - baseline_success, 4)
        discovery_delta = round(float(summary["discovery_rate_pct"]) - baseline_discovery, 4)
        quality_score = round(
            _variant_quality_score(
                success_uplift_pp=success_uplift,
                discovery_delta_pp=discovery_delta,
                discovery_rate_pct=float(summary["discovery_rate_pct"]),
                selected_count=int(summary["selected_count"]),
            ),
            4,
        )
        comparison_vs_baseline[variant_name] = {
            "success_rate_uplift_pp": success_uplift,
            "discovery_rate_delta_pp": discovery_delta,
            "quality_score": quality_score,
            "selected_count": summary["selected_count"],
        }
        if quality_score > best_quality_score and success_uplift >= 1.0:
            best_quality_score = quality_score
            recommendation = variant_name
        if (
            float(summary["discovery_rate_pct"]) >= _MIN_DISCOVERY_FOR_PROMOTION
            and success_uplift >= _MIN_SUCCESS_UPLIFT_FOR_PROMOTION
        ):
            promotion_candidates.append(
                (
                    variant_name,
                    success_uplift,
                    float(summary["discovery_rate_pct"]),
                )
            )

    if promotion_candidates:
        promotion_candidates.sort(key=lambda item: (item[1], item[2]), reverse=True)
        recommendation = promotion_candidates[0][0]

    selected_comparison = comparison_vs_baseline.get(
        recommendation,
        {
            "success_rate_uplift_pp": 0.0,
            "discovery_rate_delta_pp": 0.0,
        },
    )

    output = {
        "meta": {
            "user_id": args.user_id,
            "horizon_bars": args.horizon_bars,
            "max_candidates": args.max_candidates,
            "instrument_count": len(instrument_list),
            "evaluated_candidates": len(evaluated),
            "instruments": instrument_list,
        },
        "variants": variants_summary,
        "comparison": {
            "success_rate_uplift_pp": selected_comparison["success_rate_uplift_pp"],
            "discovery_rate_delta_pp": selected_comparison["discovery_rate_delta_pp"],
            "recommendation": recommendation,
            "top_rejection_reasons": rejection_reasons_by_variant.get(recommendation, []),
            "vs_baseline": comparison_vs_baseline,
            "top_rejection_reasons_by_variant": rejection_reasons_by_variant,
        },
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(output, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Arquivo gerado: {args.output_file}")
    print(
        "Resumo A/B: "
        f"baseline_success={baseline_summary['success_rate_pct']}% | "
        f"recomendacao={recommendation} | "
        f"uplift={selected_comparison['success_rate_uplift_pp']}pp | "
        f"baseline_discovery={baseline_summary['discovery_rate_pct']}% | "
        f"recommended_discovery={variants_summary[recommendation]['discovery_rate_pct']}%"
    )


if __name__ == "__main__":
    main()

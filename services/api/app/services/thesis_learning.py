from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import TypedDict

from app.models import MarketTick, SuitabilityProfile
from app.services.audit import record_audit_event
from app.services.thesis_case_study import (
    RawCandidate,
    ThesisSummary,
    _available_instruments,
    _enriched_thesis_candidates,
    _raw_candidates_from_ticks,
    _realized_financial_pct,
    _strategy_for_thesis,
    _ticks_for_instrument,
)
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

_DEFAULT_SKILL_PROFILE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_skill_profile.json"
)

_OIL_SENSITIVE_INSTRUMENTS = {
    "PETR4",
    "PRIO3",
    "RECV3",
    "VBBR3",
    "UGPA3",
}

_BLINDSPOT_BASE_MULTIPLIER = 26.0
_BLINDSPOT_MIN_PENALTY = 1.0
_BLINDSPOT_MAX_PENALTY = 9.0
_BLINDSPOT_MAX_COVERAGE_BY_CONDITION: dict[str, float] = {
    "expected_gt_real_by_2pp": 0.35,
}
_BLINDSPOT_PENALTY_CAP_BY_CONDITION: dict[str, float] = {
    "expected_gt_real_by_2pp": 4.0,
    "low_support_rate": 8.0,
}


class _LearningRecord(TypedDict):
    thesis_id: str
    instrument: str
    direction: str
    confidence_tese_pct: float
    expected_financial_pct: float
    realized_financial_pct: float
    success: bool
    support_rate_pct: float
    technical_support_pct: float
    fundamental_support_pct: float
    news_support_pct: float
    fundamental_available: bool
    news_available: bool
    geo_oil_available: bool
    volatility_pct: float


class BlindspotRule(TypedDict):
    condition: str
    sample_count: int
    failure_rate_pct: float
    penalty_points: float
    rationale: str


class ConfidenceBand(TypedDict):
    band: str
    sample_count: int
    avg_predicted_confidence_pct: float
    realized_success_rate_pct: float


class ThesisSkillProfile(TypedDict):
    generated_at: str
    sample_size: int
    calibration: dict[str, float]
    confidence_bands: list[ConfidenceBand]
    blindspots: list[BlindspotRule]


class ThesisLearningPayload(TypedDict):
    generated_at: str
    scan_scope: dict[str, object]
    profile_path: str
    profile: ThesisSkillProfile
    summary: dict[str, float]


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _extract_volatility_pct(thesis: ThesisSummary) -> float:
    signals = thesis.get("supporting_signals", [])
    if not isinstance(signals, list):
        return 0.0
    for signal in signals:
        if not isinstance(signal, str):
            continue
        if not signal.startswith("volatilidade_"):
            continue
        cleaned = signal.removeprefix("volatilidade_").removesuffix("pct")
        try:
            return float(cleaned)
        except ValueError:
            continue
    return 0.0


def _learning_records(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None,
    horizon_bars: int,
    max_candidates: int,
) -> tuple[list[_LearningRecord], list[str]]:
    instrument_list = _available_instruments(db, instruments)
    if not instrument_list:
        raise ValueError("Nao ha instrumentos disponiveis para ciclo de aprendizado de tese.")

    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    investor_profile = profile.investor_profile if profile is not None else "moderado"

    ticks_by_instrument: dict[str, list[MarketTick]] = {}
    raw_candidates: list[RawCandidate] = []
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        ticks_by_instrument[instrument] = ticks
        raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))
    if not raw_candidates:
        raise ValueError("Historico insuficiente para gerar teses no ciclo de aprendizado.")

    raw_candidates = sorted(
        raw_candidates,
        key=lambda item: str(item["entry_time"]),
        reverse=True,
    )[:max_candidates]

    raw_index: dict[str, RawCandidate] = {}
    for item in raw_candidates:
        key = (
            f"{item['instrument']}::{item['entry_index']}::{item['entry_time']}::"
            f"{item['direction']}::{item['horizon_bars']}"
        )
        raw_index[key] = item

    enriched = _enriched_thesis_candidates(
        db,
        raw_candidates,
        use_skill_profile=False,
    )
    records: list[_LearningRecord] = []
    for thesis in enriched:
        key = (
            f"{thesis['instrument']}::{thesis['entry_index']}::{thesis['entry_time']}::"
            f"{thesis['direction']}::{thesis['horizon_bars']}"
        )
        raw = raw_index.get(key)
        if raw is None:
            continue
        ticks = ticks_by_instrument.get(thesis["instrument"], [])
        exit_index = thesis["entry_index"] + thesis["horizon_bars"]
        if exit_index >= len(ticks) or thesis["entry_index"] < 0:
            continue
        exit_price = float(ticks[exit_index].price)
        operation = _strategy_for_thesis(thesis, investor_profile)
        realized_financial_pct = _realized_financial_pct(operation, thesis, exit_price)
        records.append(
            {
                "thesis_id": thesis["thesis_id"],
                "instrument": thesis["instrument"],
                "direction": thesis["direction"],
                "confidence_tese_pct": float(thesis["confidence_tese_pct"]),
                "expected_financial_pct": float(thesis["expected_financial_pct"]),
                "realized_financial_pct": float(realized_financial_pct),
                "success": bool(realized_financial_pct >= 0.0),
                "support_rate_pct": float(thesis["support_rate_pct"]),
                "technical_support_pct": float(thesis["technical_support_pct"]),
                "fundamental_support_pct": float(thesis["fundamental_support_pct"]),
                "news_support_pct": float(thesis["news_support_pct"]),
                "fundamental_available": bool(thesis["fundamental_available"]),
                "news_available": bool(thesis["news_available"]),
                "geo_oil_available": bool(thesis["geo_oil_available"]),
                "volatility_pct": _extract_volatility_pct(thesis),
            }
        )
    return records, instrument_list


def _confidence_bands(records: list[_LearningRecord]) -> list[ConfidenceBand]:
    bins = [
        (0.0, 50.0, "<50"),
        (50.0, 60.0, "50-59"),
        (60.0, 70.0, "60-69"),
        (70.0, 80.0, "70-79"),
        (80.0, 101.0, "80+"),
    ]
    bands: list[ConfidenceBand] = []
    for low, high, name in bins:
        bucket = [
            item
            for item in records
            if low <= item["confidence_tese_pct"] < high
        ]
        if not bucket:
            continue
        bands.append(
            {
                "band": name,
                "sample_count": len(bucket),
                "avg_predicted_confidence_pct": round(
                    mean(item["confidence_tese_pct"] for item in bucket),
                    4,
                ),
                "realized_success_rate_pct": round(
                    (sum(1 for item in bucket if item["success"]) / len(bucket)) * 100.0,
                    4,
                ),
            }
        )
    return bands


def _condition_flags(record: _LearningRecord) -> set[str]:
    conditions: set[str] = set()
    if not record["fundamental_available"]:
        conditions.add("fundamental_missing")
    if record["fundamental_support_pct"] < 52:
        conditions.add("low_fundamental_support")
    if not record["news_available"]:
        conditions.add("news_missing")
    if record["news_support_pct"] < 50:
        conditions.add("low_news_support")
    if record["volatility_pct"] >= 2.8:
        conditions.add("high_volatility")
    if record["support_rate_pct"] < 45:
        conditions.add("low_support_rate")
    if (
        record["instrument"] in _OIL_SENSITIVE_INSTRUMENTS
        and not record["geo_oil_available"]
    ):
        conditions.add("geo_oil_missing_for_oil_asset")
    if (record["expected_financial_pct"] - record["realized_financial_pct"]) > 2.0:
        conditions.add("expected_gt_real_by_2pp")
    return conditions


def _blindspot_rules(records: list[_LearningRecord]) -> list[BlindspotRule]:
    if not records:
        return []
    overall_failure_rate = sum(1 for item in records if not item["success"]) / len(records)
    minimum_sample = max(8, int(len(records) * 0.02))
    all_conditions = sorted(
        {
            condition
            for item in records
            for condition in _condition_flags(item)
        }
    )
    rules: list[BlindspotRule] = []
    for condition in all_conditions:
        scoped = [item for item in records if condition in _condition_flags(item)]
        if len(scoped) < minimum_sample:
            continue
        coverage_ratio = len(scoped) / len(records)
        max_coverage = _BLINDSPOT_MAX_COVERAGE_BY_CONDITION.get(condition, 0.85)
        if coverage_ratio > max_coverage:
            continue
        failure_rate = sum(1 for item in scoped if not item["success"]) / len(scoped)
        if failure_rate <= (overall_failure_rate + 0.07):
            continue
        raw_penalty = _clamp(
            (failure_rate - overall_failure_rate) * _BLINDSPOT_BASE_MULTIPLIER,
            _BLINDSPOT_MIN_PENALTY,
            _BLINDSPOT_MAX_PENALTY,
        )
        penalty_cap = _BLINDSPOT_PENALTY_CAP_BY_CONDITION.get(condition, _BLINDSPOT_MAX_PENALTY)
        penalty = round(min(raw_penalty, penalty_cap), 4)
        rules.append(
            {
                "condition": condition,
                "sample_count": len(scoped),
                "failure_rate_pct": round(failure_rate * 100.0, 4),
                "penalty_points": penalty,
                "rationale": (
                    "Condicao associada a taxa de falha acima da media historica "
                    "no recorte analisado."
                ),
            }
        )
    return sorted(rules, key=lambda item: item["penalty_points"], reverse=True)


def run_thesis_skill_learning_cycle(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 12,
    max_candidates: int = 1500,
    profile_path: Path | None = None,
) -> ThesisLearningPayload:
    if horizon_bars < 3:
        raise ValueError("horizon_bars deve ser maior ou igual a 3.")
    if max_candidates <= 0:
        raise ValueError("max_candidates deve ser maior que zero.")

    records, instrument_list = _learning_records(
        db,
        user_id=user_id,
        instruments=instruments,
        horizon_bars=horizon_bars,
        max_candidates=max_candidates,
    )
    if not records:
        raise ValueError("Ciclo sem registros validos para aprendizado.")

    predicted_mean = mean(item["confidence_tese_pct"] for item in records) / 100.0
    realized_success = sum(1 for item in records if item["success"]) / len(records)
    brier = mean(
        (
            ((item["confidence_tese_pct"] / 100.0) - (1.0 if item["success"] else 0.0))
            ** 2
        )
        for item in records
    )
    confidence_multiplier = 1.0
    if predicted_mean > 0:
        confidence_multiplier = _clamp(realized_success / predicted_mean, 0.75, 1.15)
    confidence_bias = _clamp((realized_success - predicted_mean) * 35.0, -8.0, 8.0)

    bands = _confidence_bands(records)
    blindspots = _blindspot_rules(records)

    profile: ThesisSkillProfile = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "sample_size": len(records),
        "calibration": {
            "confidence_multiplier": round(confidence_multiplier, 6),
            "confidence_bias_points": round(confidence_bias, 6),
            "avg_predicted_confidence_pct": round(predicted_mean * 100.0, 4),
            "realized_success_rate_pct": round(realized_success * 100.0, 4),
            "brier_score": round(brier, 6),
        },
        "confidence_bands": bands,
        "blindspots": blindspots,
    }

    output_path = profile_path or _DEFAULT_SKILL_PROFILE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, ensure_ascii=True, indent=2), encoding="utf-8")

    summary = {
        "success_rate_pct": round(realized_success * 100.0, 4),
        "avg_expected_financial_pct": round(
            mean(item["expected_financial_pct"] for item in records),
            4,
        ),
        "avg_realized_financial_pct": round(
            mean(item["realized_financial_pct"] for item in records),
            4,
        ),
        "avg_confidence_tese_pct": round(mean(item["confidence_tese_pct"] for item in records), 4),
        "blindspot_count": float(len(blindspots)),
    }

    payload: ThesisLearningPayload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "scan_scope": {
            "instrument_count": len(instrument_list),
            "horizon_bars": horizon_bars,
            "max_candidates": max_candidates,
            "instruments": instrument_list,
        },
        "profile_path": str(output_path),
        "profile": profile,
        "summary": summary,
    }
    record_audit_event(
        db,
        "thesis.skill.learning_cycle.completed",
        {
            "user_id": user_id,
            "sample_size": len(records),
            "confidence_multiplier": profile["calibration"]["confidence_multiplier"],
            "confidence_bias_points": profile["calibration"]["confidence_bias_points"],
            "blindspot_count": len(blindspots),
        },
        user_id,
    )
    return payload

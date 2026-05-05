from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev
from typing import Literal, TypedDict

from app.models import (
    FundamentalSnapshot,
    MarketTick,
    NewsAnalysisSnapshot,
    NewsArticle,
    SuitabilityProfile,
)
from app.services.audit import record_audit_event
from app.services.news import aggregate_sentiment_as_of
from app.services.point_in_time import latest_fundamentals_as_of
from app.services.thesis_policy import apply_active_policy
from app.services.thesis_postmortem import CaseStudyPostmortem, persist_case_study_postmortem
from app.services.utils import DISCLAIMER
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

Direction = Literal["bullish", "bearish", "range"]

_OIL_SENSITIVE_INSTRUMENTS = {
    "PETR4",
    "PRIO3",
    "RECV3",
    "VBBR3",
    "UGPA3",
}

_GEO_OIL_TERMS = (
    "guerra",
    "iran",
    "eua",
    "usa",
    "oriente medio",
    "oriente médio",
    "golfo",
    "hormuz",
    "opec",
    "petroleo",
    "petróleo",
    "brent",
    "logistica",
    "logística",
    "sancoes",
    "sanções",
)
_THESIS_SKILL_PROFILE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "thesis_skill_profile.json"
)
_SKILL_PENALTY_WEIGHT_BY_CONDITION: dict[str, float] = {
    "expected_gt_real_by_2pp": 0.35,
    "low_support_rate": 0.75,
    "low_news_support": 0.85,
    "low_fundamental_support": 0.8,
    "high_volatility": 0.7,
    "fundamental_missing": 0.65,
    "news_missing": 0.6,
    "geo_oil_missing_for_oil_asset": 0.9,
}
_SKILL_PENALTY_DEFAULT_WEIGHT = 0.75
_SKILL_PENALTY_MAX_TOTAL_POINTS = 10.0


class RawCandidate(TypedDict):
    instrument: str
    direction: Direction
    entry_index: int
    entry_time: str
    horizon_bars: int
    entry_price: float
    target_price: float
    stop_price: float
    target_move_pct: float
    volatility_pct: float
    momentum_pct: float
    confidence_base_pct: float
    success_realized: bool
    realized_move_pct: float


class ThesisSummary(TypedDict):
    thesis_id: str
    instrument: str
    direction: Direction
    entry_index: int
    entry_time: str
    entry_price: float
    target_price: float
    stop_price: float
    target_move_pct: float
    horizon_bars: int
    confidence_tese_pct: float
    success_probability_pct: float
    expected_financial_pct: float
    support_rate_pct: float
    technical_support_pct: float
    fundamental_support_pct: float
    news_support_pct: float
    geo_oil_support_pct: float
    news_available: bool
    geo_oil_available: bool
    fundamental_available: bool
    fundamental_context: FundamentalContext
    supporting_signals: list[str]


class FundamentalContext(TypedDict):
    available: bool
    support_pct: float
    rationale: list[str]
    snapshot: dict[str, object] | None


class StructuredLeg(TypedDict):
    side: str
    instrument: str
    option_type: str
    strike: float
    quantity: int


class StructuredOperation(TypedDict):
    strategy_id: str
    strategy_name: str
    rationale: str
    max_gain_pct: float
    max_loss_pct: float
    breakeven_price: float
    legs: list[StructuredLeg]


class OperationOutcome(TypedDict):
    exit_price: float
    exit_reason: str
    success: bool
    realized_financial_pct: float


class MonitoringEvent(TypedDict):
    event_time: str
    event_type: str
    severity: str
    message: str
    market_price: float


class KnowledgeSkill(TypedDict):
    skill_name: str
    thesis_signature: dict[str, object]
    replication_playbook: list[str]
    monitoring_triggers: list[str]
    guardrails: list[str]


class CaseStudyPayload(TypedDict):
    pipeline: dict[str, object]
    selected_case: dict[str, object]
    knowledge_skill: KnowledgeSkill
    postmortem: CaseStudyPostmortem
    disclaimer: str


def _leg(
    side: str,
    instrument: str,
    option_type: str,
    strike: float,
    quantity: int = 1,
) -> StructuredLeg:
    return {
        "side": side,
        "instrument": instrument,
        "option_type": option_type,
        "strike": strike,
        "quantity": quantity,
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _load_thesis_skill_profile() -> dict[str, object] | None:
    if not _THESIS_SKILL_PROFILE_PATH.exists():
        return None
    try:
        payload = json.loads(_THESIS_SKILL_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _active_skill_conditions(
    *,
    instrument: str,
    volatility_pct: float,
    support_rate_pct: float,
    fundamental_available: bool,
    fundamental_support_pct: float,
    news_available: bool,
    news_support_pct: float,
    geo_oil_available: bool,
    expected_financial_pct: float,
) -> set[str]:
    conditions: set[str] = set()
    if not fundamental_available:
        conditions.add("fundamental_missing")
    if fundamental_support_pct < 52:
        conditions.add("low_fundamental_support")
    if not news_available:
        conditions.add("news_missing")
    if news_support_pct < 50:
        conditions.add("low_news_support")
    if volatility_pct >= 2.8:
        conditions.add("high_volatility")
    if support_rate_pct < 45:
        conditions.add("low_support_rate")
    if instrument.upper() in _OIL_SENSITIVE_INSTRUMENTS and not geo_oil_available:
        conditions.add("geo_oil_missing_for_oil_asset")
    if expected_financial_pct > 4.5:
        conditions.add("expected_gt_real_by_2pp")
    return conditions


def _apply_skill_profile_adjustment(
    *,
    confidence_raw: float,
    skill_profile: dict[str, object] | None,
    active_conditions: set[str],
) -> tuple[float, list[str]]:
    if skill_profile is None:
        return confidence_raw, []
    calibration_raw = skill_profile.get("calibration")
    blindspots_raw = skill_profile.get("blindspots")
    if not isinstance(calibration_raw, dict):
        calibration_raw = {}
    multiplier = float(calibration_raw.get("confidence_multiplier", 1.0))
    bias_points = float(calibration_raw.get("confidence_bias_points", 0.0))
    adjusted = (confidence_raw * multiplier) + bias_points
    notes = [
        f"skill_calibration_mult_{multiplier:.4f}",
        f"skill_calibration_bias_{bias_points:.4f}",
    ]
    total_penalty_applied = 0.0
    if isinstance(blindspots_raw, list):
        for item in blindspots_raw:
            if not isinstance(item, dict):
                continue
            condition = item.get("condition")
            penalty_points = item.get("penalty_points")
            if not isinstance(condition, str) or condition not in active_conditions:
                continue
            if not isinstance(penalty_points, (int, float)):
                continue
            weight = _SKILL_PENALTY_WEIGHT_BY_CONDITION.get(
                condition,
                _SKILL_PENALTY_DEFAULT_WEIGHT,
            )
            weighted_penalty = max(float(penalty_points) * weight, 0.5)
            remaining = _SKILL_PENALTY_MAX_TOTAL_POINTS - total_penalty_applied
            if remaining <= 0:
                break
            applied_penalty = min(weighted_penalty, remaining)
            adjusted -= applied_penalty
            total_penalty_applied += applied_penalty
            notes.append(f"skill_penalty_{condition}_{applied_penalty:.4f}")
    return round(_clamp(adjusted, 5.0, 95.0), 4), notes


def _fundamental_snapshot_to_payload(snapshot: FundamentalSnapshot) -> dict[str, object]:
    return {
        "source_name": snapshot.source_name,
        "source_type": snapshot.source_type,
        "reference_time": snapshot.reference_time,
        "availability_time": snapshot.availability_time,
        "version_tag": snapshot.version_tag,
        "pe_ratio": snapshot.pe_ratio,
        "pb_ratio": snapshot.pb_ratio,
        "ev_ebitda": snapshot.ev_ebitda,
        "dividend_yield": snapshot.dividend_yield,
        "roe": snapshot.roe,
        "net_margin": snapshot.net_margin,
        "revenue_growth": snapshot.revenue_growth,
        "payout_ratio": snapshot.payout_ratio,
    }


def _bullish_fundamental_score(snapshot: FundamentalSnapshot) -> tuple[float, list[str]]:
    score = 50.0
    rationale: list[str] = []

    if snapshot.pe_ratio <= 14:
        score += 8
        rationale.append("valuation_pe_baixo")
    elif snapshot.pe_ratio >= 25:
        score -= 8
        rationale.append("valuation_pe_alto")

    if snapshot.pb_ratio <= 2.0:
        score += 6
        rationale.append("valuation_pb_controlado")
    elif snapshot.pb_ratio >= 4.0:
        score -= 6
        rationale.append("valuation_pb_esticado")

    if snapshot.ev_ebitda <= 8:
        score += 6
        rationale.append("valuation_ev_ebitda_controlado")
    elif snapshot.ev_ebitda >= 14:
        score -= 6
        rationale.append("valuation_ev_ebitda_pressao")

    if snapshot.roe >= 15:
        score += 10
        rationale.append("rentabilidade_roe_forte")
    elif snapshot.roe <= 5:
        score -= 8
        rationale.append("rentabilidade_roe_fraca")

    if snapshot.net_margin >= 10:
        score += 7
        rationale.append("margem_liquida_saudavel")
    elif snapshot.net_margin < 0:
        score -= 9
        rationale.append("margem_liquida_negativa")

    if snapshot.revenue_growth >= 8:
        score += 8
        rationale.append("crescimento_receita_consistente")
    elif snapshot.revenue_growth < 0:
        score -= 8
        rationale.append("crescimento_receita_negativo")

    if snapshot.dividend_yield >= 5:
        score += 3
        rationale.append("dividend_yield_suporte")
    elif snapshot.dividend_yield <= 1:
        score -= 2
        rationale.append("dividend_yield_limitado")

    if 20 <= snapshot.payout_ratio <= 70:
        score += 4
        rationale.append("payout_equilibrado")
    elif snapshot.payout_ratio > 100:
        score -= 4
        rationale.append("payout_estressado")

    return round(_clamp(score, 5.0, 95.0), 4), rationale


def _fundamental_context(
    db: Session,
    instrument: str,
    entry_time: datetime,
    direction: Direction,
) -> FundamentalContext:
    snapshot = latest_fundamentals_as_of(db, instrument.upper(), entry_time)
    if snapshot is None:
        return {
            "available": False,
            "support_pct": 50.0,
            "rationale": ["fundamentos_indisponiveis_neutro_50pct"],
            "snapshot": None,
        }

    bullish_score, rationale = _bullish_fundamental_score(snapshot)
    if direction == "bullish":
        support_pct = bullish_score
    elif direction == "bearish":
        support_pct = 100.0 - bullish_score
    else:
        support_pct = 100.0 - (abs(bullish_score - 50.0) * 1.4)

    rationale_tag = f"fundamental_alinhamento_{direction}_{support_pct:.1f}pct"
    return {
        "available": True,
        "support_pct": round(_clamp(support_pct, 5.0, 95.0), 4),
        "rationale": [*rationale, rationale_tag, f"fundamental_version_{snapshot.version_tag}"],
        "snapshot": _fundamental_snapshot_to_payload(snapshot),
    }


def _news_support_pct(
    db: Session,
    instrument: str,
    entry_time: datetime,
    direction: Direction,
) -> tuple[float, bool, str]:
    sentiment = aggregate_sentiment_as_of(db, instrument.upper(), entry_time)
    article_count = int(sentiment["article_count"])
    if article_count <= 0:
        return 50.0, False, "news_sentiment_indisponivel_neutro_50pct"

    weighted_sentiment = float(sentiment["weighted_sentiment"])
    if direction == "bullish":
        support = 50.0 + (weighted_sentiment * 50.0)
    elif direction == "bearish":
        support = 50.0 - (weighted_sentiment * 50.0)
    else:
        support = 100.0 - (abs(weighted_sentiment) * 60.0)
    support_pct = round(_clamp(support, 5.0, 95.0), 4)
    rationale = (
        f"news_sentiment_{sentiment['sentiment_bias']}_"
        f"{weighted_sentiment:.3f}_articles_{article_count}"
    )
    return support_pct, True, rationale


def _geopolitical_oil_support_pct(
    db: Session,
    instrument: str,
    entry_time: datetime,
    direction: Direction,
) -> tuple[float, bool, str]:
    instrument_code = instrument.upper()
    if instrument_code not in _OIL_SENSITIVE_INSTRUMENTS:
        return 50.0, False, "geo_oil_nao_aplicavel_para_ativo"

    window_start = (entry_time - timedelta(days=21)).isoformat()
    entry_iso = entry_time.isoformat()
    like_filters = [
        NewsArticle.headline.ilike(f"%{term}%")
        for term in _GEO_OIL_TERMS
    ]
    statement = (
        select(NewsArticle, NewsAnalysisSnapshot)
        .join(NewsAnalysisSnapshot, NewsAnalysisSnapshot.news_article_id == NewsArticle.id)
        .where(NewsArticle.instrument == instrument_code)
        .where(
            and_(
                NewsArticle.published_at >= window_start,
                NewsArticle.published_at <= entry_iso,
            )
        )
        .where(or_(*like_filters))
        .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
        .limit(40)
    )
    rows = list(db.execute(statement).all())
    if not rows:
        return 50.0, False, "geo_oil_sem_evento_relevante_no_recorte"

    weighted_sentiment_sum = 0.0
    weight_sum = 0.0
    magnitude_sum = 0.0
    for _, analysis in rows:
        confidence = float(analysis.model_confidence)
        magnitude = float(analysis.magnitude_score)
        weight = max(0.1, confidence * max(magnitude, 0.1))
        weighted_sentiment_sum += float(analysis.sentiment_score) * weight
        weight_sum += weight
        magnitude_sum += magnitude

    weighted_sentiment = weighted_sentiment_sum / max(weight_sum, 1e-9)
    average_magnitude = magnitude_sum / len(rows)
    shock_score = _clamp(
        50.0 + (weighted_sentiment * 35.0) + (average_magnitude * 10.0),
        5.0,
        95.0,
    )
    if direction == "bullish":
        support = shock_score
    elif direction == "bearish":
        support = 100.0 - shock_score
    else:
        support = 100.0 - (abs(shock_score - 50.0) * 1.5)
    support_pct = round(_clamp(support, 5.0, 95.0), 4)
    rationale = (
        f"geo_oil_context_sent_{weighted_sentiment:.3f}_"
        f"mag_{average_magnitude:.3f}_articles_{len(rows)}"
    )
    return support_pct, True, rationale


def _available_instruments(db: Session, instruments: list[str] | None) -> list[str]:
    if instruments:
        unique = list(dict.fromkeys(item.upper() for item in instruments))
        return unique
    statement = select(MarketTick.instrument).distinct().order_by(MarketTick.instrument.asc())
    return list(db.scalars(statement))


def _ticks_for_instrument(db: Session, instrument: str) -> list[MarketTick]:
    statement = (
        select(MarketTick)
        .where(MarketTick.instrument == instrument.upper())
        .order_by(MarketTick.event_time.asc())
    )
    return list(db.scalars(statement))


def _direction_from_momentum(momentum_pct: float, volatility_pct: float) -> Direction | None:
    if momentum_pct >= 1.2:
        return "bullish"
    if momentum_pct <= -1.2:
        return "bearish"
    if abs(momentum_pct) <= 0.8 and volatility_pct <= 1.8:
        return "range"
    return None


def _target_move_pct(direction: Direction, momentum_pct: float, volatility_pct: float) -> float:
    if direction == "range":
        return 1.5
    directional_strength = abs(momentum_pct) * 1.2
    return _clamp(directional_strength + (volatility_pct * 0.4), 1.5, 7.0)


def _confidence_base(momentum_pct: float, volatility_pct: float, volume_ratio: float) -> float:
    direction_strength = min(30.0, abs(momentum_pct) * 4.0)
    volatility_bonus = _clamp(20.0 - (volatility_pct * 5.0), 0.0, 20.0)
    volume_bonus = _clamp((volume_ratio - 1.0) * 20.0, 0.0, 12.0)
    return round(_clamp(45.0 + direction_strength + volatility_bonus + volume_bonus, 30.0, 95.0), 2)


def _raw_candidate_for_entry(
    instrument: str,
    ticks: list[MarketTick],
    closes: list[float],
    volumes: list[int],
    *,
    entry_index: int,
    horizon_bars: int,
    require_full_horizon: bool,
) -> RawCandidate | None:
    if entry_index < 10 or entry_index >= len(ticks):
        return None

    lookback = closes[entry_index - 10 : entry_index + 1]
    if len(lookback) < 11:
        return None

    entry_price = closes[entry_index]
    if entry_price <= 0:
        return None

    momentum_pct = ((entry_price - lookback[0]) / lookback[0]) * 100
    volatility_pct = 0.0
    if len(lookback) > 1:
        volatility_pct = (pstdev(lookback) / mean(lookback)) * 100

    direction = _direction_from_momentum(momentum_pct, volatility_pct)
    if direction is None:
        return None

    window_volumes = volumes[entry_index - 10 : entry_index]
    baseline_volume = max(1, int(mean(window_volumes)))
    volume_ratio = volumes[entry_index] / baseline_volume
    confidence_base_pct = _confidence_base(momentum_pct, volatility_pct, volume_ratio)
    target_move = _target_move_pct(direction, momentum_pct, volatility_pct)

    if direction == "bullish":
        target_price = entry_price * (1 + (target_move / 100))
        stop_price = entry_price * (1 - ((target_move * 0.6) / 100))
    elif direction == "bearish":
        target_price = entry_price * (1 - (target_move / 100))
        stop_price = entry_price * (1 + ((target_move * 0.6) / 100))
    else:
        target_price = entry_price
        stop_price = entry_price * (1 - (target_move / 100))

    future_prices = closes[entry_index + 1 : min(len(ticks), entry_index + 1 + horizon_bars)]
    if require_full_horizon and len(future_prices) < horizon_bars:
        return None

    success_realized = False
    realized_move_pct = 0.0
    if future_prices:
        terminal_price = future_prices[-1]
        if require_full_horizon:
            if direction == "bullish":
                success_realized = max(future_prices) >= target_price
                realized_move_pct = ((terminal_price - entry_price) / entry_price) * 100
            elif direction == "bearish":
                success_realized = min(future_prices) <= target_price
                realized_move_pct = ((entry_price - terminal_price) / entry_price) * 100
            else:
                upper_bound = entry_price * 1.015
                lower_bound = entry_price * 0.985
                success_realized = (
                    min(future_prices) >= lower_bound
                    and max(future_prices) <= upper_bound
                )
                realized_move_pct = (
                    1 - (abs(terminal_price - entry_price) / entry_price)
                ) * 100
        elif direction == "bullish":
            realized_move_pct = ((terminal_price - entry_price) / entry_price) * 100
        elif direction == "bearish":
            realized_move_pct = ((entry_price - terminal_price) / entry_price) * 100

    return {
        "instrument": instrument.upper(),
        "direction": direction,
        "entry_index": entry_index,
        "entry_time": ticks[entry_index].event_time,
        "horizon_bars": horizon_bars,
        "entry_price": round(entry_price, 4),
        "target_price": round(target_price, 4),
        "stop_price": round(stop_price, 4),
        "target_move_pct": round(target_move, 4),
        "volatility_pct": round(volatility_pct, 4),
        "momentum_pct": round(momentum_pct, 4),
        "confidence_base_pct": confidence_base_pct,
        "success_realized": success_realized,
        "realized_move_pct": round(realized_move_pct, 4),
    }


def _raw_candidates_from_ticks(
    instrument: str,
    ticks: list[MarketTick],
    horizon_bars: int,
) -> list[RawCandidate]:
    if len(ticks) < 20 or len(ticks) <= horizon_bars + 10:
        return []

    closes = [float(tick.price) for tick in ticks]
    volumes = [int(tick.volume) for tick in ticks]
    results: list[RawCandidate] = []

    for entry_index in range(10, len(ticks) - horizon_bars):
        candidate = _raw_candidate_for_entry(
            instrument,
            ticks,
            closes,
            volumes,
            entry_index=entry_index,
            horizon_bars=horizon_bars,
            require_full_horizon=True,
        )
        if candidate is not None:
            results.append(candidate)
    return results


def _live_candidates_from_ticks(
    instrument: str,
    ticks: list[MarketTick],
    horizon_bars: int,
    recent_bars_window: int,
) -> list[RawCandidate]:
    if len(ticks) < 11:
        return []

    closes = [float(tick.price) for tick in ticks]
    volumes = [int(tick.volume) for tick in ticks]
    latest_index = len(ticks) - 1
    start_index = max(
        10,
        latest_index - max(recent_bars_window - 1, 0),
        len(ticks) - horizon_bars,
    )

    results: list[RawCandidate] = []
    for entry_index in range(start_index, latest_index + 1):
        candidate = _raw_candidate_for_entry(
            instrument,
            ticks,
            closes,
            volumes,
            entry_index=entry_index,
            horizon_bars=horizon_bars,
            require_full_horizon=False,
        )
        if candidate is None:
            continue
        if entry_index + horizon_bars <= latest_index:
            continue
        results.append(candidate)
    return results


def _support_rate_by_signature(candidates: list[RawCandidate]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = {}
    for candidate in candidates:
        key = f"{candidate['instrument']}::{candidate['direction']}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(candidate["success_realized"])

    support: dict[str, float] = {}
    for key, outcomes in grouped.items():
        success_rate = (sum(1 for item in outcomes if item) / len(outcomes)) * 100
        support[key] = round(success_rate, 4)
    return support


def _enriched_thesis_candidates(
    db: Session,
    candidates: list[RawCandidate],
    *,
    support_candidates: list[RawCandidate] | None = None,
    use_skill_profile: bool = True,
) -> list[ThesisSummary]:
    if not candidates:
        return []

    support_map = _support_rate_by_signature(
        support_candidates if support_candidates is not None else candidates
    )
    skill_profile = _load_thesis_skill_profile() if use_skill_profile else None
    fundamental_cache: dict[str, FundamentalContext] = {}
    news_cache: dict[str, tuple[float, bool, str]] = {}
    geo_cache: dict[str, tuple[float, bool, str]] = {}
    enriched: list[ThesisSummary] = []
    for index, candidate in enumerate(candidates, start=1):
        support_key = f"{candidate['instrument']}::{candidate['direction']}"
        support_rate = support_map.get(support_key, 0.0)
        technical_support = candidate["confidence_base_pct"]
        fundamental_key = (
            f"{candidate['instrument']}::{candidate['entry_time']}::{candidate['direction']}"
        )
        if fundamental_key not in fundamental_cache:
            fundamental_cache[fundamental_key] = _fundamental_context(
                db,
                candidate["instrument"],
                _parse_iso_datetime(candidate["entry_time"]),
                candidate["direction"],
            )
        fundamental_context = fundamental_cache[fundamental_key]
        news_key = (
            f"{candidate['instrument']}::{candidate['entry_time']}::{candidate['direction']}"
        )
        if news_key not in news_cache:
            news_cache[news_key] = _news_support_pct(
                db,
                candidate["instrument"],
                _parse_iso_datetime(candidate["entry_time"]),
                candidate["direction"],
            )
        news_support_pct, news_available, news_rationale = news_cache[news_key]
        if news_key not in geo_cache:
            geo_cache[news_key] = _geopolitical_oil_support_pct(
                db,
                candidate["instrument"],
                _parse_iso_datetime(candidate["entry_time"]),
                candidate["direction"],
            )
        geo_oil_support_pct, geo_oil_available, geo_oil_rationale = geo_cache[news_key]

        success_probability_raw = round(
            _clamp(
                (technical_support * 0.46)
                + (support_rate * 0.20)
                + (fundamental_context["support_pct"] * 0.16)
                + (news_support_pct * 0.10)
                + (geo_oil_support_pct * 0.08),
                5.0,
                95.0,
            ),
            4,
        )
        reward_pct = candidate["target_move_pct"]
        risk_pct = candidate["target_move_pct"] * 0.6
        expected_financial_raw = round(
            ((success_probability_raw / 100) * reward_pct)
            - ((1 - (success_probability_raw / 100)) * risk_pct),
            4,
        )
        active_conditions = _active_skill_conditions(
            instrument=candidate["instrument"],
            volatility_pct=candidate["volatility_pct"],
            support_rate_pct=support_rate,
            fundamental_available=fundamental_context["available"],
            fundamental_support_pct=fundamental_context["support_pct"],
            news_available=news_available,
            news_support_pct=news_support_pct,
            geo_oil_available=geo_oil_available,
            expected_financial_pct=expected_financial_raw,
        )
        success_probability, skill_notes = _apply_skill_profile_adjustment(
            confidence_raw=success_probability_raw,
            skill_profile=skill_profile,
            active_conditions=active_conditions,
        )
        expected_financial = round(
            ((success_probability / 100) * reward_pct)
            - ((1 - (success_probability / 100)) * risk_pct),
            4,
        )
        supporting_signals = [
            f"momento_{candidate['direction']}_{candidate['momentum_pct']:.2f}pct",
            f"volatilidade_{candidate['volatility_pct']:.2f}pct",
            f"suporte_historico_{support_rate:.2f}pct",
            f"suporte_tecnico_{technical_support:.2f}pct",
            f"suporte_fundamental_{fundamental_context['support_pct']:.2f}pct",
            f"suporte_news_{news_support_pct:.2f}pct",
            f"suporte_geo_oil_{geo_oil_support_pct:.2f}pct",
            news_rationale,
            geo_oil_rationale,
            *fundamental_context["rationale"],
            *skill_notes,
        ]
        enriched.append(
            {
                "thesis_id": (
                    f"TH-{candidate['instrument']}-{candidate['direction']}-{index:04d}"
                ),
                "instrument": candidate["instrument"],
                "direction": candidate["direction"],
                "entry_index": candidate["entry_index"],
                "entry_time": candidate["entry_time"],
                "entry_price": candidate["entry_price"],
                "target_price": candidate["target_price"],
                "stop_price": candidate["stop_price"],
                "target_move_pct": candidate["target_move_pct"],
                "horizon_bars": candidate["horizon_bars"],
                "confidence_tese_pct": success_probability,
                "success_probability_pct": success_probability,
                "expected_financial_pct": expected_financial,
                "support_rate_pct": support_rate,
                "technical_support_pct": round(technical_support, 4),
                "fundamental_support_pct": fundamental_context["support_pct"],
                "news_support_pct": news_support_pct,
                "geo_oil_support_pct": geo_oil_support_pct,
                "news_available": news_available,
                "geo_oil_available": geo_oil_available,
                "fundamental_available": fundamental_context["available"],
                "fundamental_context": fundamental_context,
                "supporting_signals": supporting_signals,
            }
        )
    return sorted(
        enriched,
        key=lambda item: (
            item["confidence_tese_pct"],
            item["expected_financial_pct"],
        ),
        reverse=True,
    )


def _strategy_for_thesis(
    thesis: ThesisSummary,
    investor_profile: str,
) -> StructuredOperation:
    entry_price = thesis["entry_price"]
    direction = thesis["direction"]

    if direction == "bullish":
        strategy_id = "BULL_CALL_SPREAD"
        strategy_name = "Bull Call Spread"
        k1 = round(entry_price * 1.01, 2)
        k2 = round(entry_price * 1.06, 2)
        max_gain_pct = 5.4
        max_loss_pct = 2.2
        breakeven = round(entry_price * 1.026, 2)
        legs: list[StructuredLeg] = [
            _leg("long", thesis["instrument"], "call", k1),
            _leg("short", thesis["instrument"], "call", k2),
        ]
    elif direction == "bearish":
        strategy_id = "BEAR_PUT_SPREAD"
        strategy_name = "Bear Put Spread"
        k1 = round(entry_price * 0.99, 2)
        k2 = round(entry_price * 0.94, 2)
        max_gain_pct = 5.2
        max_loss_pct = 2.3
        breakeven = round(entry_price * 0.972, 2)
        legs = [
            _leg("long", thesis["instrument"], "put", k1),
            _leg("short", thesis["instrument"], "put", k2),
        ]
    else:
        strategy_id = "IRON_CONDOR"
        strategy_name = "Iron Condor"
        lower_put = round(entry_price * 0.92, 2)
        upper_put = round(entry_price * 0.96, 2)
        lower_call = round(entry_price * 1.04, 2)
        upper_call = round(entry_price * 1.08, 2)
        max_gain_pct = 2.4
        max_loss_pct = 3.8
        breakeven = round(entry_price, 2)
        legs = [
            _leg("long", thesis["instrument"], "put", lower_put),
            _leg("short", thesis["instrument"], "put", upper_put),
            _leg("short", thesis["instrument"], "call", lower_call),
            _leg("long", thesis["instrument"], "call", upper_call),
        ]

    suitability_note = "perfil moderado/arrojado"
    if investor_profile == "conservador":
        max_gain_pct = round(max_gain_pct * 0.7, 4)
        max_loss_pct = round(max_loss_pct * 0.7, 4)
        suitability_note = "perfil conservador (alocacao reduzida)"

    return {
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "rationale": (
            f"Estrutura alinhada ao cenario {direction} com risco definido ({suitability_note}). "
            "Simulacao educacional baseada em historico local."
        ),
        "max_gain_pct": max_gain_pct,
        "max_loss_pct": max_loss_pct,
        "breakeven_price": breakeven,
        "legs": legs,
    }


def _realized_financial_pct(
    operation: StructuredOperation,
    thesis: ThesisSummary,
    exit_price: float,
) -> float:
    entry_price = thesis["entry_price"]
    if entry_price <= 0:
        return 0.0
    move_pct = ((exit_price - entry_price) / entry_price) * 100

    if operation["strategy_id"] == "BULL_CALL_SPREAD":
        scaled = (move_pct / max(thesis["target_move_pct"], 0.1)) * operation["max_gain_pct"]
        return round(_clamp(scaled, -operation["max_loss_pct"], operation["max_gain_pct"]), 4)
    if operation["strategy_id"] == "BEAR_PUT_SPREAD":
        bearish_move = -move_pct
        scaled = (bearish_move / max(thesis["target_move_pct"], 0.1)) * operation["max_gain_pct"]
        return round(_clamp(scaled, -operation["max_loss_pct"], operation["max_gain_pct"]), 4)

    range_width = 1.8
    distance = abs(move_pct)
    if distance <= range_width:
        gain_factor = 1 - (distance / range_width)
        return round(gain_factor * operation["max_gain_pct"], 4)
    loss_factor = min(1.0, (distance - range_width) / max(0.1, thesis["target_move_pct"]))
    return round(-(loss_factor * operation["max_loss_pct"]), 4)


def _monitoring_timeline(
    ticks: list[MarketTick],
    thesis: ThesisSummary,
    operation: StructuredOperation,
    entry_index: int,
    exit_index: int,
) -> list[MonitoringEvent]:
    if entry_index < 0 or exit_index < entry_index:
        return []
    path = ticks[entry_index : exit_index + 1]
    if not path:
        return []

    events: list[MonitoringEvent] = [
        {
            "event_time": path[0].event_time,
            "event_type": "entry_snapshot",
            "severity": "info",
            "message": "Operacao estruturada iniciada em simulacao.",
            "market_price": round(float(path[0].price), 4),
        }
    ]
    for tick in path[1:]:
        price = float(tick.price)
        if thesis["direction"] == "bullish" and price <= thesis["stop_price"]:
            events.append(
                {
                    "event_time": tick.event_time,
                    "event_type": "stop_risk_warning",
                    "severity": "high",
                    "message": "Preco entrou na zona de invalidacao da tese bullish.",
                    "market_price": round(price, 4),
                }
            )
            continue
        if thesis["direction"] == "bearish" and price >= thesis["stop_price"]:
            events.append(
                {
                    "event_time": tick.event_time,
                    "event_type": "stop_risk_warning",
                    "severity": "high",
                    "message": "Preco entrou na zona de invalidacao da tese bearish.",
                    "market_price": round(price, 4),
                }
            )
            continue
        if thesis["direction"] == "range":
            upper = thesis["entry_price"] * 1.018
            lower = thesis["entry_price"] * 0.982
            if price > upper or price < lower:
                events.append(
                    {
                        "event_time": tick.event_time,
                        "event_type": "range_break_alert",
                        "severity": "medium",
                        "message": "Ativo saiu do range esperado para a estrutura neutra.",
                        "market_price": round(price, 4),
                    }
                )
                continue
        if thesis["direction"] in {"bullish", "bearish"}:
            target_hit = (
                price >= thesis["target_price"]
                if thesis["direction"] == "bullish"
                else price <= thesis["target_price"]
            )
            if target_hit:
                events.append(
                    {
                        "event_time": tick.event_time,
                        "event_type": "target_watch",
                        "severity": "info",
                        "message": "Preco atingiu a zona-alvo da tese durante monitoramento.",
                        "market_price": round(price, 4),
                    }
                )

    events.append(
        {
            "event_time": path[-1].event_time,
            "event_type": "exit_snapshot",
            "severity": "info",
            "message": f"Encerramento da simulacao da estrutura {operation['strategy_id']}.",
            "market_price": round(float(path[-1].price), 4),
        }
    )
    return events


def _effective_result_reason(
    *,
    expected_financial_pct: float,
    realized_financial_pct: float,
    monitoring_events: list[MonitoringEvent],
) -> str:
    delta = round(realized_financial_pct - expected_financial_pct, 4)
    high_risk_count = sum(1 for event in monitoring_events if event["severity"] == "high")
    medium_risk_count = sum(1 for event in monitoring_events if event["severity"] == "medium")

    if delta >= 0.75:
        baseline = "Resultado efetivo acima do esperado para a tese no horizonte analisado."
    elif delta <= -0.75:
        baseline = "Resultado efetivo abaixo do esperado para a tese no horizonte analisado."
    else:
        baseline = "Resultado efetivo proximo do esperado para a tese no horizonte analisado."

    if high_risk_count > 0:
        driver = (
            f"Foram observados {high_risk_count} eventos de risco alto no monitoramento, "
            "impactando o desempenho da estrutura."
        )
    elif medium_risk_count > 0:
        driver = (
            f"O monitoramento registrou {medium_risk_count} eventos de risco medio, "
            "indicando regime de mercado menos estavel."
        )
    else:
        driver = "Nao houve eventos relevantes de risco no monitoramento da operacao."
    return f"{baseline} {driver}"


def _knowledge_skill(thesis: ThesisSummary, operation: StructuredOperation) -> KnowledgeSkill:
    return {
        "skill_name": (
            f"SSE_{thesis['instrument']}_{thesis['direction']}_{operation['strategy_id']}"
        ),
        "thesis_signature": {
            "instrument": thesis["instrument"],
            "direction": thesis["direction"],
            "confidence_tese_pct": thesis["confidence_tese_pct"],
            "support_rate_pct": thesis["support_rate_pct"],
            "horizon_bars": thesis["horizon_bars"],
        },
        "replication_playbook": [
            "Detectar tese com varredura de momento e volatilidade no historico point-in-time.",
            "Validar suporte da tese por taxa historica de acerto e estabilidade do sinal.",
            "Selecionar estrutura SSE com risco definido e compatibilidade com suitability.",
            "Monitorar eventos de stop/target/range-break ate o encerramento da janela.",
            "Registrar KPIs de confianca, esperado e realizado para aprendizado continuo.",
        ],
        "monitoring_triggers": [
            "stop_risk_warning",
            "target_watch",
            "range_break_alert",
            "exit_snapshot",
        ],
        "guardrails": [
            "Somente simulacao paper trading.",
            "Sem linguagem de recomendacao personalizada.",
            "Adequar estrutura ao perfil de suitability do usuario.",
        ],
    }


def run_thesis_case_study(
    db: Session,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 8,
) -> CaseStudyPayload:
    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    if profile is None:
        raise ValueError("Suitability obrigatorio para estudo de caso de tese estruturada.")

    instrument_list = _available_instruments(db, instruments)
    if not instrument_list:
        raise ValueError("Nao ha instrumentos com historico de mercado para varredura.")

    raw_candidates: list[RawCandidate] = []
    ticks_by_instrument: dict[str, list[MarketTick]] = {}
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        ticks_by_instrument[instrument] = ticks
        raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))

    if not raw_candidates:
        raise ValueError("Historico insuficiente para validar teses no horizonte solicitado.")

    thesis_candidates = _enriched_thesis_candidates(db, raw_candidates)
    policy_candidates, policy_metadata = apply_active_policy(thesis_candidates)
    validated = [
        item
        for item in policy_candidates
        if item["confidence_tese_pct"] >= 55 and item["expected_financial_pct"] > 0
    ]
    selected = validated[0] if validated else policy_candidates[0]
    selected_ticks = ticks_by_instrument.get(selected["instrument"], [])

    entry_idx = selected["entry_index"]
    exit_idx = entry_idx + selected["horizon_bars"]
    if entry_idx < 0 or len(selected_ticks) <= exit_idx:
        raise ValueError("Serie selecionada nao possui barras suficientes para simular saida.")

    entry_time = selected_ticks[entry_idx].event_time
    exit_time = selected_ticks[exit_idx].event_time
    exit_price = round(float(selected_ticks[exit_idx].price), 4)

    operation = _strategy_for_thesis(selected, profile.investor_profile)
    realized_financial_pct = _realized_financial_pct(operation, selected, exit_price)
    success = realized_financial_pct >= 0
    outcome: OperationOutcome = {
        "exit_price": exit_price,
        "exit_reason": "target_or_window_close",
        "success": success,
        "realized_financial_pct": realized_financial_pct,
    }
    monitoring = _monitoring_timeline(selected_ticks, selected, operation, entry_idx, exit_idx)
    effective_result_reason = _effective_result_reason(
        expected_financial_pct=selected["expected_financial_pct"],
        realized_financial_pct=realized_financial_pct,
        monitoring_events=monitoring,
    )
    knowledge_skill = _knowledge_skill(selected, operation)

    pipeline_summary = {
        "scan_scope": {
            "instruments": instrument_list,
            "horizon_bars": horizon_bars,
            "total_ticks": sum(len(items) for items in ticks_by_instrument.values()),
        },
        "candidate_count": len(thesis_candidates),
        "policy_candidate_count": len(policy_candidates),
        "validated_count": len(validated),
        "selected_thesis_id": selected["thesis_id"],
        "policy": policy_metadata,
    }

    payload: CaseStudyPayload = {
        "pipeline": pipeline_summary,
        "selected_case": {
            "thesis": selected,
            "thesis_raised_at": entry_time,
            "suggested_entry_time": entry_time,
            "suggested_exit_time": exit_time,
            "structured_operation": operation,
            "outcome": outcome,
            "kpis": {
                "confidence_tese_pct": selected["confidence_tese_pct"],
                "expected_financial_pct": selected["expected_financial_pct"],
                "realized_financial_pct": realized_financial_pct,
            },
            "fundamental_context": selected["fundamental_context"],
            "effective_result_reason": effective_result_reason,
            "monitoring_timeline": monitoring,
        },
        "knowledge_skill": knowledge_skill,
        "postmortem": {
            "generated_at": "",
            "thesis_id": "",
            "instrument": "",
            "direction": "",
            "strategy_id": "",
            "policy_name": "",
            "signature": "",
            "success": False,
            "confidence_tese_pct": 0.0,
            "expected_financial_pct": 0.0,
            "realized_financial_pct": 0.0,
            "expected_vs_real_gap_pct": 0.0,
            "market_move_pct": 0.0,
            "structure_cushion_pct": 0.0,
            "stop_risk_event_count": 0,
            "high_risk_event_count": 0,
            "early_invalidation": False,
            "analysis_tags": [],
            "learning_actions": [],
            "shadow_profile_snapshot": {},
        },
        "disclaimer": DISCLAIMER,
    }
    record_audit_event(
        db,
        "thesis.case_study.generated",
        {
            "user_id": user_id,
            "selected_thesis_id": selected["thesis_id"],
            "strategy_id": operation["strategy_id"],
            "policy_name": policy_metadata["active_policy"],
            "confidence_tese_pct": selected["confidence_tese_pct"],
            "expected_financial_pct": selected["expected_financial_pct"],
            "realized_financial_pct": realized_financial_pct,
        },
        user_id,
    )
    postmortem = persist_case_study_postmortem(payload)
    payload["postmortem"] = postmortem
    record_audit_event(
        db,
        "thesis.postmortem.generated",
        {
            "user_id": user_id,
            "thesis_id": postmortem["thesis_id"],
            "signature": postmortem["signature"],
            "analysis_tags": postmortem["analysis_tags"],
            "learning_actions": postmortem["learning_actions"],
        },
        user_id,
    )
    return payload

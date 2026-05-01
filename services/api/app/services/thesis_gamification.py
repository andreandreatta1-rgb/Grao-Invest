from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypedDict

from app.models import MarketTick, SuitabilityProfile
from app.services.audit import record_audit_event
from app.services.thesis_case_study import (
    ThesisSummary,
    _available_instruments,
    _enriched_thesis_candidates,
    _raw_candidates_from_ticks,
    _realized_financial_pct,
    _strategy_for_thesis,
    _ticks_for_instrument,
)
from app.services.thesis_policy import apply_active_policy
from app.services.utils import DISCLAIMER
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

OptionId = Literal["A", "B", "C"]
StrategyProfile = Literal[
    "auto_conservative",
    "auto_balanced",
    "auto_aggressive",
    "custom",
]


class PlayerDecisionInput(TypedDict):
    thesis_id: str
    follow: bool
    option_id: OptionId
    allocation_pct: float


class PlayerConfigInput(TypedDict):
    name: str
    initial_capital: float
    strategy_profile: StrategyProfile
    decisions: list[PlayerDecisionInput] | None


class ThesisOptionCard(TypedDict):
    option_id: OptionId
    label: str
    strategy_id: str
    strategy_name: str
    expected_return_pct: float
    realized_return_pct: float
    max_gain_pct: float
    max_loss_pct: float
    risk_level: str
    follow_hint: str


class ThesisGameCard(TypedDict):
    thesis_id: str
    instrument: str
    direction: str
    thesis_raised_at: str
    suggested_entry_time: str
    suggested_exit_time: str
    confidence_tese_pct: float
    success_probability_pct: float
    expected_financial_pct: float
    realized_base_financial_pct: float
    why_raised: list[str]
    options: list[ThesisOptionCard]


class PlayerStepResult(TypedDict):
    thesis_id: str
    follow: bool
    option_id: OptionId
    allocation_pct: float
    capital_before: float
    allocated_amount: float
    expected_return_pct: float
    realized_return_pct: float
    expected_pnl_amount: float
    pnl_amount: float
    capital_after: float


class PlayerSimulationResult(TypedDict):
    name: str
    strategy_profile: StrategyProfile
    initial_capital: float
    final_capital: float
    total_pnl_amount: float
    total_return_pct: float
    expected_total_pnl_amount: float
    followed_count: int
    skipped_count: int
    hit_rate_pct: float
    steps: list[PlayerStepResult]


class LeaderboardRow(TypedDict):
    rank: int
    name: str
    final_capital: float
    total_return_pct: float
    total_pnl_amount: float
    hit_rate_pct: float


class GameSimulationPayload(TypedDict):
    generated_at: str
    user_id: int
    horizon_bars: int
    thesis_count: int
    scan_scope: dict[str, object]
    theses: list[ThesisGameCard]
    players: list[PlayerSimulationResult]
    leaderboard: list[LeaderboardRow]
    winner: LeaderboardRow
    disclaimer: str


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _default_players() -> list[PlayerConfigInput]:
    return [
        {
            "name": "Andre",
            "initial_capital": 100_000.0,
            "strategy_profile": "auto_conservative",
            "decisions": None,
        },
        {
            "name": "Enzo",
            "initial_capital": 100_000.0,
            "strategy_profile": "auto_aggressive",
            "decisions": None,
        },
    ]


def _resolve_exit_tick(
    ticks_by_instrument: dict[str, list[MarketTick]],
    thesis: ThesisSummary,
) -> MarketTick | None:
    ticks = ticks_by_instrument.get(thesis["instrument"], [])
    exit_index = thesis["entry_index"] + thesis["horizon_bars"]
    if thesis["entry_index"] < 0 or exit_index >= len(ticks):
        return None
    return ticks[exit_index]


def _pick_top_theses(
    theses: list[ThesisSummary],
    ticks_by_instrument: dict[str, list[MarketTick]],
    thesis_count: int,
) -> list[ThesisSummary]:
    selected: list[ThesisSummary] = []
    by_instrument: dict[str, int] = {}
    max_per_instrument = 4
    for thesis in theses:
        if _resolve_exit_tick(ticks_by_instrument, thesis) is None:
            continue
        instrument = thesis["instrument"]
        current = by_instrument.get(instrument, 0)
        if current >= max_per_instrument:
            continue
        selected.append(thesis)
        by_instrument[instrument] = current + 1
        if len(selected) >= thesis_count:
            break

    if len(selected) >= thesis_count:
        return selected

    used = {item["thesis_id"] for item in selected}
    for thesis in theses:
        if thesis["thesis_id"] in used:
            continue
        if _resolve_exit_tick(ticks_by_instrument, thesis) is None:
            continue
        selected.append(thesis)
        used.add(thesis["thesis_id"])
        if len(selected) >= thesis_count:
            break
    return selected


def _scaled_return(base_return_pct: float, gain_scale: float, loss_scale: float) -> float:
    if base_return_pct >= 0:
        return round(base_return_pct * gain_scale, 4)
    return round(base_return_pct * loss_scale, 4)


def _follow_hint(confidence_pct: float, expected_return_pct: float, risk_level: str) -> str:
    if expected_return_pct <= 0:
        return "nao_seguir"
    if confidence_pct >= 65 and risk_level in {"baixo", "medio"}:
        return "seguir"
    if confidence_pct >= 58:
        return "avaliar"
    return "nao_seguir"


def _build_option_cards(
    thesis: ThesisSummary,
    exit_price: float,
    investor_profile: str,
) -> list[ThesisOptionCard]:
    base_operation = _strategy_for_thesis(thesis, investor_profile)
    base_realized = _realized_financial_pct(base_operation, thesis, exit_price)
    base_expected = thesis["expected_financial_pct"]

    cards: list[ThesisOptionCard] = []
    option_setup: list[tuple[OptionId, str, float, float, str]] = [
        ("A", "Base balanceada", 1.0, 1.0, "medio"),
        ("B", "Defensiva", 0.72, 0.58, "baixo"),
        ("C", "Agressiva", 1.55, 1.75, "alto"),
    ]
    for option_id, label, gain_scale, loss_scale, risk_level in option_setup:
        expected = _scaled_return(base_expected, gain_scale, loss_scale)
        realized = _scaled_return(base_realized, gain_scale, loss_scale)
        cards.append(
            {
                "option_id": option_id,
                "label": label,
                "strategy_id": base_operation["strategy_id"],
                "strategy_name": base_operation["strategy_name"],
                "expected_return_pct": expected,
                "realized_return_pct": realized,
                "max_gain_pct": round(base_operation["max_gain_pct"] * gain_scale, 4),
                "max_loss_pct": round(base_operation["max_loss_pct"] * loss_scale, 4),
                "risk_level": risk_level,
                "follow_hint": _follow_hint(
                    thesis["confidence_tese_pct"],
                    expected,
                    risk_level,
                ),
            }
        )
    return cards


def _to_game_card(
    thesis: ThesisSummary,
    ticks_by_instrument: dict[str, list[MarketTick]],
    investor_profile: str,
) -> ThesisGameCard | None:
    exit_tick = _resolve_exit_tick(ticks_by_instrument, thesis)
    if exit_tick is None:
        return None
    exit_price = round(float(exit_tick.price), 4)
    options = _build_option_cards(thesis, exit_price, investor_profile)
    base_option = next(item for item in options if item["option_id"] == "A")
    return {
        "thesis_id": thesis["thesis_id"],
        "instrument": thesis["instrument"],
        "direction": thesis["direction"],
        "thesis_raised_at": thesis["entry_time"],
        "suggested_entry_time": thesis["entry_time"],
        "suggested_exit_time": exit_tick.event_time,
        "confidence_tese_pct": thesis["confidence_tese_pct"],
        "success_probability_pct": thesis["success_probability_pct"],
        "expected_financial_pct": thesis["expected_financial_pct"],
        "realized_base_financial_pct": base_option["realized_return_pct"],
        "why_raised": thesis["supporting_signals"][:5],
        "options": options,
    }


def _option_lookup(card: ThesisGameCard) -> dict[OptionId, ThesisOptionCard]:
    return {item["option_id"]: item for item in card["options"]}


def _auto_decision(
    strategy_profile: StrategyProfile,
    card: ThesisGameCard,
) -> PlayerDecisionInput:
    confidence = card["confidence_tese_pct"]
    expected = card["expected_financial_pct"]
    thesis_id = card["thesis_id"]

    if strategy_profile == "auto_conservative":
        if confidence < 63 or expected <= 0:
            return {
                "thesis_id": thesis_id,
                "follow": False,
                "option_id": "B",
                "allocation_pct": 0.0,
            }
        option_id: OptionId = "B" if confidence < 72 else "A"
        allocation_pct = 8.0 if confidence < 70 else 10.0
        return {
            "thesis_id": thesis_id,
            "follow": True,
            "option_id": option_id,
            "allocation_pct": allocation_pct,
        }

    if strategy_profile == "auto_balanced":
        if confidence < 58 or expected <= -0.25:
            return {
                "thesis_id": thesis_id,
                "follow": False,
                "option_id": "A",
                "allocation_pct": 0.0,
            }
        option_id = "A" if expected >= 0 else "B"
        allocation_pct = 12.0 if confidence < 70 else 14.0
        return {
            "thesis_id": thesis_id,
            "follow": True,
            "option_id": option_id,
            "allocation_pct": allocation_pct,
        }

    if strategy_profile == "auto_aggressive":
        if confidence < 54 and expected < 0.5:
            return {
                "thesis_id": thesis_id,
                "follow": False,
                "option_id": "C",
                "allocation_pct": 0.0,
            }
        option_id = "C" if confidence >= 70 else "A"
        allocation_pct = 16.0 if expected < 1.2 else 20.0
        return {
            "thesis_id": thesis_id,
            "follow": True,
            "option_id": option_id,
            "allocation_pct": allocation_pct,
        }

    return {
        "thesis_id": thesis_id,
        "follow": False,
        "option_id": "A",
        "allocation_pct": 0.0,
    }


def _normalize_player(
    raw: PlayerConfigInput,
    known_thesis_ids: set[str],
) -> PlayerConfigInput:
    name = raw["name"].strip()
    if not name:
        raise ValueError("Nome de jogador invalido na simulacao gamificada.")
    if raw["initial_capital"] <= 0:
        raise ValueError(f"Capital inicial invalido para jogador {name}.")

    strategy_profile: StrategyProfile = raw["strategy_profile"]
    if strategy_profile not in {
        "auto_conservative",
        "auto_balanced",
        "auto_aggressive",
        "custom",
    }:
        raise ValueError(f"strategy_profile invalido para jogador {name}.")

    decisions = raw["decisions"]
    if decisions is None:
        return {
            "name": name,
            "initial_capital": round(raw["initial_capital"], 4),
            "strategy_profile": strategy_profile,
            "decisions": None,
        }

    normalized_decisions: list[PlayerDecisionInput] = []
    seen_thesis_ids: set[str] = set()
    for decision in decisions:
        thesis_id = decision["thesis_id"].strip()
        if thesis_id not in known_thesis_ids:
            raise ValueError(
                f"Jogador {name} possui decisao para thesis_id desconhecido: {thesis_id}."
            )
        if thesis_id in seen_thesis_ids:
            raise ValueError(f"Jogador {name} possui decisao duplicada para {thesis_id}.")
        seen_thesis_ids.add(thesis_id)
        allocation_pct = round(float(decision["allocation_pct"]), 4)
        if allocation_pct < 0 or allocation_pct > 35:
            raise ValueError(
                f"allocation_pct fora do limite [0,35] para jogador {name} em {thesis_id}."
            )
        normalized_decisions.append(
            {
                "thesis_id": thesis_id,
                "follow": bool(decision["follow"]),
                "option_id": decision["option_id"],
                "allocation_pct": allocation_pct,
            }
        )

    return {
        "name": name,
        "initial_capital": round(raw["initial_capital"], 4),
        "strategy_profile": strategy_profile,
        "decisions": normalized_decisions,
    }


def _decision_map(decisions: list[PlayerDecisionInput] | None) -> dict[str, PlayerDecisionInput]:
    if decisions is None:
        return {}
    return {decision["thesis_id"]: decision for decision in decisions}


def _simulate_player(
    player: PlayerConfigInput,
    cards: list[ThesisGameCard],
) -> PlayerSimulationResult:
    capital = round(player["initial_capital"], 4)
    initial_capital = capital
    follow_count = 0
    hit_count = 0
    total_expected_pnl = 0.0
    steps: list[PlayerStepResult] = []
    custom_map = _decision_map(player["decisions"])

    for card in cards:
        decision = custom_map.get(card["thesis_id"])
        if decision is None:
            decision = _auto_decision(player["strategy_profile"], card)

        if not decision["follow"]:
            step: PlayerStepResult = {
                "thesis_id": card["thesis_id"],
                "follow": False,
                "option_id": decision["option_id"],
                "allocation_pct": 0.0,
                "capital_before": capital,
                "allocated_amount": 0.0,
                "expected_return_pct": 0.0,
                "realized_return_pct": 0.0,
                "expected_pnl_amount": 0.0,
                "pnl_amount": 0.0,
                "capital_after": capital,
            }
            steps.append(step)
            continue

        if decision["allocation_pct"] <= 0:
            raise ValueError(
                f"Jogador {player['name']} marcou follow=true com allocation_pct <= 0 "
                f"na tese {card['thesis_id']}."
            )

        option_map = _option_lookup(card)
        option = option_map.get(decision["option_id"])
        if option is None:
            raise ValueError(
                f"Opcao invalida para jogador {player['name']} na tese {card['thesis_id']}."
            )
        allocation_pct = _clamp(decision["allocation_pct"], 0.0, 35.0)
        allocated_amount = round(capital * (allocation_pct / 100), 4)
        expected_return_pct = option["expected_return_pct"]
        realized_return_pct = option["realized_return_pct"]
        expected_pnl_amount = round(allocated_amount * (expected_return_pct / 100), 4)
        pnl_amount = round(allocated_amount * (realized_return_pct / 100), 4)
        capital_after = round(capital + pnl_amount, 4)

        follow_count += 1
        if pnl_amount >= 0:
            hit_count += 1
        total_expected_pnl += expected_pnl_amount
        steps.append(
            {
                "thesis_id": card["thesis_id"],
                "follow": True,
                "option_id": decision["option_id"],
                "allocation_pct": allocation_pct,
                "capital_before": capital,
                "allocated_amount": allocated_amount,
                "expected_return_pct": expected_return_pct,
                "realized_return_pct": realized_return_pct,
                "expected_pnl_amount": expected_pnl_amount,
                "pnl_amount": pnl_amount,
                "capital_after": capital_after,
            }
        )
        capital = capital_after

    total_pnl = round(capital - initial_capital, 4)
    total_return_pct = round((total_pnl / initial_capital) * 100, 4)
    hit_rate_pct = round(((hit_count / follow_count) * 100), 4) if follow_count > 0 else 0.0
    return {
        "name": player["name"],
        "strategy_profile": player["strategy_profile"],
        "initial_capital": initial_capital,
        "final_capital": capital,
        "total_pnl_amount": total_pnl,
        "total_return_pct": total_return_pct,
        "expected_total_pnl_amount": round(total_expected_pnl, 4),
        "followed_count": follow_count,
        "skipped_count": len(cards) - follow_count,
        "hit_rate_pct": hit_rate_pct,
        "steps": steps,
    }


def _leaderboard(players: list[PlayerSimulationResult]) -> list[LeaderboardRow]:
    sorted_players = sorted(
        players,
        key=lambda item: (item["final_capital"], item["total_return_pct"]),
        reverse=True,
    )
    rows: list[LeaderboardRow] = []
    for index, player in enumerate(sorted_players, start=1):
        rows.append(
            {
                "rank": index,
                "name": player["name"],
                "final_capital": player["final_capital"],
                "total_return_pct": player["total_return_pct"],
                "total_pnl_amount": player["total_pnl_amount"],
                "hit_rate_pct": player["hit_rate_pct"],
            }
        )
    return rows


def run_thesis_game_simulation(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 8,
    thesis_count: int = 10,
    players: list[PlayerConfigInput] | None = None,
) -> GameSimulationPayload:
    profile = db.scalar(
        select(SuitabilityProfile)
        .where(SuitabilityProfile.user_id == user_id)
        .order_by(desc(SuitabilityProfile.id))
        .limit(1)
    )
    if profile is None:
        raise ValueError("Suitability obrigatorio para simulacao gamificada.")

    instrument_list = _available_instruments(db, instruments)
    if not instrument_list:
        raise ValueError("Nao ha historico de mercado para montar as teses do experimento.")

    raw_candidates = []
    ticks_by_instrument: dict[str, list[MarketTick]] = {}
    for instrument in instrument_list:
        ticks = _ticks_for_instrument(db, instrument)
        ticks_by_instrument[instrument] = ticks
        raw_candidates.extend(_raw_candidates_from_ticks(instrument, ticks, horizon_bars))
    if not raw_candidates:
        raise ValueError("Historico insuficiente para montar teses no horizonte solicitado.")

    enriched = _enriched_thesis_candidates(db, raw_candidates)
    policy_candidates, policy_metadata = apply_active_policy(enriched)
    picked = _pick_top_theses(policy_candidates, ticks_by_instrument, thesis_count)
    if len(picked) < thesis_count:
        raise ValueError(
            f"Foi possivel montar apenas {len(picked)} teses; ajuste universo ou horizonte."
        )

    cards: list[ThesisGameCard] = []
    for thesis in picked:
        card = _to_game_card(thesis, ticks_by_instrument, profile.investor_profile)
        if card is not None:
            cards.append(card)
    if len(cards) < thesis_count:
        raise ValueError(
            f"Apenas {len(cards)} teses possuem janela completa de entrada/saida no momento."
        )

    cards = sorted(cards, key=lambda item: _parse_iso_datetime(item["thesis_raised_at"]))
    selected_cards = cards[:thesis_count]
    thesis_ids = {card["thesis_id"] for card in selected_cards}

    raw_players = players if players is not None else _default_players()
    if len(raw_players) < 1:
        raise ValueError("Informe ao menos um jogador para a simulacao.")

    normalized_players = [_normalize_player(player, thesis_ids) for player in raw_players]
    player_results = [_simulate_player(player, selected_cards) for player in normalized_players]
    leaderboard = _leaderboard(player_results)
    winner = leaderboard[0]

    payload: GameSimulationPayload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "user_id": user_id,
        "horizon_bars": horizon_bars,
        "thesis_count": thesis_count,
        "scan_scope": {
            "instruments": instrument_list,
            "tick_count": sum(len(items) for items in ticks_by_instrument.values()),
            "candidate_count": len(enriched),
            "policy_candidate_count": len(policy_candidates),
            "policy": policy_metadata,
        },
        "theses": selected_cards,
        "players": player_results,
        "leaderboard": leaderboard,
        "winner": winner,
        "disclaimer": DISCLAIMER,
    }
    record_audit_event(
        db,
        "thesis.game_simulation.generated",
        {
            "user_id": user_id,
            "thesis_count": thesis_count,
            "winner": winner,
            "players": [
                {
                    "name": player["name"],
                    "final_capital": player["final_capital"],
                    "total_return_pct": player["total_return_pct"],
                }
                for player in player_results
            ],
        },
        user_id,
    )
    return payload

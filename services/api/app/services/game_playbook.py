from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypedDict, cast

from app.services.game_context import GameHistoricalContext, context_for_reference_time
from app.services.thesis_gamification import (
    PlayerConfigInput,
    ThesisGameCard,
    run_thesis_game_simulation,
)
from app.services.utils import DISCLAIMER
from sqlalchemy.orm import Session

OptionId = Literal["A", "B", "C"]


class GamePlaybookOption(TypedDict):
    option_id: OptionId
    label: str
    strategy_id: str
    strategy_name: str
    expected_return_pct: float
    realized_return_pct: float
    risk_level: str
    follow_hint: str


class GamePlaybookThesis(TypedDict):
    thesis_id: str
    instrument: str
    direction: str
    thesis_raised_at: str
    suggested_entry_time: str
    suggested_exit_time: str
    thesis_statement: str
    objective: str
    suggested_operation: GamePlaybookOption
    why_thesis: list[str]
    context: GameHistoricalContext
    options: list[GamePlaybookOption]


class GamePlaybookPayload(TypedDict):
    generated_at: str
    user_id: int
    player_initial_capital: float
    thesis_count: int
    horizon_bars: int
    scan_scope: dict[str, object]
    theses: list[GamePlaybookThesis]
    disclaimer: str


def _default_template_player(initial_capital: float) -> list[PlayerConfigInput]:
    return [
        {
            "name": "TemplatePlayer",
            "initial_capital": round(initial_capital, 4),
            "strategy_profile": "auto_balanced",
            "decisions": None,
        }
    ]


def _direction_label(direction: str) -> str:
    mapping = {
        "bullish": "continuidade de alta",
        "bearish": "correcao/queda",
        "range": "lateralidade controlada",
    }
    return mapping.get(direction, direction)


def _to_playbook_option(option: dict[str, object]) -> GamePlaybookOption:
    def _to_float(value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    option_id = cast(OptionId, str(option.get("option_id", "A")).upper())
    return {
        "option_id": option_id,
        "label": str(option.get("label", "")),
        "strategy_id": str(option.get("strategy_id", "")),
        "strategy_name": str(option.get("strategy_name", "")),
        "expected_return_pct": _to_float(option.get("expected_return_pct")),
        "realized_return_pct": _to_float(option.get("realized_return_pct")),
        "risk_level": str(option.get("risk_level", "medio")),
        "follow_hint": str(option.get("follow_hint", "avaliar")),
    }


def _extract_option_a(options: list[GamePlaybookOption]) -> GamePlaybookOption:
    for option in options:
        if option["option_id"] == "A":
            return option
    return options[0]


def _to_playbook_thesis(thesis: ThesisGameCard) -> GamePlaybookThesis:
    options = [_to_playbook_option(cast(dict[str, object], option)) for option in thesis["options"]]
    option_a = _extract_option_a(options)
    direction = thesis["direction"]
    thesis_statement = (
        f"{thesis['instrument']} com tese de {_direction_label(direction)} "
        f"identificada no historico."
    )
    objective = (
        f"Capturar o movimento esperado no horizonte da tese com risco limitado. "
        f"Probabilidade historica estimada: {thesis['success_probability_pct']:.2f}%."
    )
    context = context_for_reference_time(thesis["thesis_raised_at"], thesis["instrument"])
    return {
        "thesis_id": thesis["thesis_id"],
        "instrument": thesis["instrument"],
        "direction": direction,
        "thesis_raised_at": thesis["thesis_raised_at"],
        "suggested_entry_time": thesis["suggested_entry_time"],
        "suggested_exit_time": thesis["suggested_exit_time"],
        "thesis_statement": thesis_statement,
        "objective": objective,
        "suggested_operation": option_a,
        "why_thesis": thesis["why_raised"],
        "context": context,
        "options": options,
    }


def build_game_playbook(
    db: Session,
    *,
    user_id: int,
    instruments: list[str] | None = None,
    horizon_bars: int = 8,
    thesis_count: int = 5,
    player_initial_capital: float = 100_000.0,
) -> GamePlaybookPayload:
    simulation = run_thesis_game_simulation(
        db,
        user_id=user_id,
        instruments=instruments,
        horizon_bars=horizon_bars,
        thesis_count=thesis_count,
        players=_default_template_player(player_initial_capital),
    )
    theses = [_to_playbook_thesis(thesis) for thesis in simulation["theses"][:thesis_count]]
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "user_id": user_id,
        "player_initial_capital": round(player_initial_capital, 4),
        "thesis_count": thesis_count,
        "horizon_bars": horizon_bars,
        "scan_scope": simulation["scan_scope"],
        "theses": theses,
        "disclaimer": DISCLAIMER,
    }

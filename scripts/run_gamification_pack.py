from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.thesis_gamification import PlayerConfigInput, run_thesis_game_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa pacote A/B/C de simulacoes gamificadas para Andre e Enzo."
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario base.")
    parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Lista separada por virgula (ex.: PETR4,VALE3,ITUB4,B3SA3,WEGE3).",
    )
    parser.add_argument("--horizon-bars", type=int, default=8)
    parser.add_argument("--thesis-count", type=int, default=10)
    parser.add_argument("--initial-capital", type=float, default=100_000.0)
    return parser.parse_args()


def _scenario_players(name: str, initial_capital: float) -> list[PlayerConfigInput]:
    capital = round(initial_capital, 4)
    if name == "A":
        return [
            {
                "name": "Andre",
                "initial_capital": capital,
                "strategy_profile": "auto_conservative",
                "decisions": None,
            },
            {
                "name": "Enzo",
                "initial_capital": capital,
                "strategy_profile": "auto_aggressive",
                "decisions": None,
            },
        ]
    if name == "B":
        return [
            {
                "name": "Andre",
                "initial_capital": capital,
                "strategy_profile": "auto_balanced",
                "decisions": None,
            },
            {
                "name": "Enzo",
                "initial_capital": capital,
                "strategy_profile": "auto_balanced",
                "decisions": None,
            },
        ]
    return [
        {
            "name": "Andre",
            "initial_capital": capital,
            "strategy_profile": "auto_aggressive",
            "decisions": None,
        },
        {
            "name": "Enzo",
            "initial_capital": capital,
            "strategy_profile": "auto_aggressive",
            "decisions": None,
        },
    ]


def _to_markdown(payload: dict[str, object]) -> str:
    lines: list[str] = [
        "# Pacote de Simulacoes A/B/C",
        "",
        "## Cenarios",
        "- A: Andre conservador vs Enzo agressivo",
        "- B: Andre e Enzo balanceados",
        "- C: Andre e Enzo agressivos",
        "",
        "## Resultado Consolidado",
    ]
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        scenario_name = scenario["scenario"]
        winner = scenario["winner"]
        leaderboard = scenario["leaderboard"]
        assert isinstance(winner, dict)
        assert isinstance(leaderboard, list)
        lines.append("")
        lines.append(f"### Cenario {scenario_name}")
        lines.append(
            f"- vencedor: {winner['name']} | retorno={winner['total_return_pct']:.2f}% | "
            f"capital_final={winner['final_capital']:.2f}"
        )
        lines.append("| rank | jogador | retorno_% | capital_final | hit_rate_% |")
        lines.append("|---:|---|---:|---:|---:|")
        for row in leaderboard:
            assert isinstance(row, dict)
            lines.append(
                f"| {row['rank']} | {row['name']} | {row['total_return_pct']:.2f} | "
                f"{row['final_capital']:.2f} | {row['hit_rate_pct']:.2f} |"
            )
    lines.append("")
    lines.append(f"Guardrail: {payload['disclaimer']}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]

    scenario_runs = []
    disclaimer = ""
    with SessionLocal() as db:
        for scenario_name in ["A", "B", "C"]:
            simulation = run_thesis_game_simulation(
                db,
                user_id=args.user_id,
                instruments=instruments or None,
                horizon_bars=args.horizon_bars,
                thesis_count=args.thesis_count,
                players=_scenario_players(scenario_name, args.initial_capital),
            )
            scenario_runs.append(
                {
                    "scenario": scenario_name,
                    "generated_at": simulation["generated_at"],
                    "winner": simulation["winner"],
                    "leaderboard": simulation["leaderboard"],
                    "players": simulation["players"],
                    "theses": simulation["theses"],
                }
            )
            if not disclaimer:
                disclaimer = simulation["disclaimer"]

    payload = {
        "user_id": args.user_id,
        "thesis_count": args.thesis_count,
        "horizon_bars": args.horizon_bars,
        "instruments": instruments,
        "scenarios": scenario_runs,
        "disclaimer": disclaimer,
    }
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "gamification_pack_latest.json"
    md_path = data_dir / "gamification_pack_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")

    print(f"JSON salvo em: {json_path}")
    print(f"Markdown salvo em: {md_path}")
    for scenario in payload["scenarios"]:
        winner = scenario["winner"]
        print(
            f"Cenario {scenario['scenario']}: "
            f"vencedor={winner['name']} retorno={winner['total_return_pct']:.2f}%"
        )


if __name__ == "__main__":
    main()

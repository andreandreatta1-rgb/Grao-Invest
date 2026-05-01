from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.thesis_gamification import (
    GameSimulationPayload,
    PlayerConfigInput,
    run_thesis_game_simulation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa experimento gamificado com 10 teses (ou N configuravel), "
            "decisoes seguir/nao seguir e placar final entre jogadores."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario base.")
    parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Lista separada por virgula (ex.: PETR4,VALE3,ITUB4).",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=8,
        help="Horizonte em barras para saida da tese.",
    )
    parser.add_argument(
        "--thesis-count",
        type=int,
        default=10,
        help="Quantidade de teses no game (5..20).",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=100_000.0,
        help="Capital inicial por jogador no modo padrao.",
    )
    parser.add_argument(
        "--decision-file",
        type=str,
        default="",
        help=(
            "Caminho opcional para JSON de jogadores/decisoes customizadas. "
            "Se ausente, usa Andre(auto_conservative) e Enzo(auto_aggressive)."
        ),
    )
    return parser.parse_args()


def _load_players_from_json(path: Path) -> list[PlayerConfigInput]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Arquivo de decisoes deve ser um objeto JSON.")
    players = parsed.get("players")
    if not isinstance(players, list) or not players:
        raise ValueError("Arquivo de decisoes deve conter lista nao-vazia em 'players'.")
    normalized: list[PlayerConfigInput] = []
    for item in players:
        if not isinstance(item, dict):
            raise ValueError("Cada player no arquivo de decisao deve ser objeto.")
        name = str(item.get("name", "")).strip()
        initial_capital = float(item.get("initial_capital", 0))
        strategy_profile = str(item.get("strategy_profile", "custom")).strip()
        decisions_raw = item.get("decisions")
        decisions = None
        if isinstance(decisions_raw, list):
            decisions = []
            for decision in decisions_raw:
                if not isinstance(decision, dict):
                    raise ValueError("Cada decisao precisa ser objeto JSON.")
                decisions.append(
                    {
                        "thesis_id": str(decision.get("thesis_id", "")).strip(),
                        "follow": bool(decision.get("follow", False)),
                        "option_id": str(decision.get("option_id", "A")).strip().upper(),
                        "allocation_pct": float(decision.get("allocation_pct", 0)),
                    }
                )
        normalized.append(
            {
                "name": name,
                "initial_capital": initial_capital,
                "strategy_profile": strategy_profile,  # validacao ocorre no service
                "decisions": decisions,
            }
        )
    return normalized


def _default_players(initial_capital: float) -> list[PlayerConfigInput]:
    base_capital = round(initial_capital, 4)
    return [
        {
            "name": "Andre",
            "initial_capital": base_capital,
            "strategy_profile": "auto_conservative",
            "decisions": None,
        },
        {
            "name": "Enzo",
            "initial_capital": base_capital,
            "strategy_profile": "auto_aggressive",
            "decisions": None,
        },
    ]


def _format_money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _to_markdown(payload: GameSimulationPayload) -> str:
    lines: list[str] = []
    lines.append("# Experimento Gamificado de Teses")
    lines.append("")
    lines.append("## Resumo")
    lines.append(f"- generated_at: {payload['generated_at']}")
    lines.append(f"- user_id: {payload['user_id']}")
    lines.append(f"- thesis_count: {payload['thesis_count']}")
    lines.append(f"- horizon_bars: {payload['horizon_bars']}")
    lines.append(f"- instrumentos_escaneados: {', '.join(payload['scan_scope']['instruments'])}")
    lines.append(f"- candidato_teses: {payload['scan_scope']['candidate_count']}")
    lines.append("")
    lines.append("## Ranking Final")
    for row in payload["leaderboard"]:
        lines.append(
            f"- #{row['rank']} {row['name']}: final={_format_money(row['final_capital'])} | "
            "retorno="
            f"{row['total_return_pct']:.2f}% | "
            f"pnl={_format_money(row['total_pnl_amount'])} | "
            f"hit_rate={row['hit_rate_pct']:.2f}%"
        )
    lines.append("")
    winner_line = (
        f"Vencedor: {payload['winner']['name']} com "
        f"{_format_money(payload['winner']['final_capital'])}."
    )
    lines.append(winner_line)
    lines.append("")
    lines.append("## Teses (10 opcoes para o game)")
    for index, thesis in enumerate(payload["theses"], start=1):
        lines.append("")
        lines.append(f"### Tese {index}: {thesis['thesis_id']} ({thesis['instrument']})")
        lines.append(f"- direction: {thesis['direction']}")
        lines.append(f"- thesis_raised_at: {thesis['thesis_raised_at']}")
        lines.append(f"- suggested_entry_time: {thesis['suggested_entry_time']}")
        lines.append(f"- suggested_exit_time: {thesis['suggested_exit_time']}")
        lines.append(f"- confidence_tese_pct: {thesis['confidence_tese_pct']:.2f}%")
        lines.append(f"- expected_financial_pct: {thesis['expected_financial_pct']:.2f}%")
        lines.append(f"- realized_base_financial_pct: {thesis['realized_base_financial_pct']:.2f}%")
        lines.append(f"- why_raised: {', '.join(thesis['why_raised'])}")
        lines.append("- opcoes:")
        for option in thesis["options"]:
            lines.append(
                f"  - {option['option_id']} {option['label']}: "
                f"esperado={option['expected_return_pct']:.2f}% | "
                f"realizado={option['realized_return_pct']:.2f}% | "
                f"risco={option['risk_level']} | hint={option['follow_hint']}"
            )

    lines.append("")
    lines.append("## Decisoes e Resultado por Jogador")
    for player in payload["players"]:
        lines.append("")
        lines.append(f"### {player['name']} ({player['strategy_profile']})")
        lines.append(f"- initial_capital: {_format_money(player['initial_capital'])}")
        lines.append(f"- final_capital: {_format_money(player['final_capital'])}")
        lines.append(f"- total_return_pct: {player['total_return_pct']:.2f}%")
        lines.append(
            "- expected_total_pnl_amount: "
            f"{_format_money(player['expected_total_pnl_amount'])}"
        )
        lines.append(f"- total_pnl_amount: {_format_money(player['total_pnl_amount'])}")
        lines.append(f"- followed_count: {player['followed_count']}")
        lines.append(f"- skipped_count: {player['skipped_count']}")
        lines.append(f"- hit_rate_pct: {player['hit_rate_pct']:.2f}%")
        lines.append("")
        lines.append(
            "| tese | seguir | opcao | alocacao_% | "
            "retorno_real_% | pnl | capital_final |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for step in player["steps"]:
            lines.append(
                "| "
                f"{step['thesis_id']} | "
                f"{'sim' if step['follow'] else 'nao'} | "
                f"{step['option_id']} | "
                f"{step['allocation_pct']:.2f} | "
                f"{step['realized_return_pct']:.2f} | "
                f"{step['pnl_amount']:.2f} | "
                f"{step['capital_after']:.2f} |"
            )
    lines.append("")
    lines.append("## Guardrail")
    lines.append(f"- {payload['disclaimer']}")
    return "\n".join(lines)


def _build_players(args: argparse.Namespace) -> list[PlayerConfigInput]:
    if args.decision_file:
        path = Path(args.decision_file).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Arquivo de decisao nao encontrado: {path}")
        return _load_players_from_json(path)
    return _default_players(args.initial_capital)


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    players = _build_players(args)

    with SessionLocal() as db:
        payload = run_thesis_game_simulation(
            db,
            user_id=args.user_id,
            instruments=instruments or None,
            horizon_bars=args.horizon_bars,
            thesis_count=args.thesis_count,
            players=players,
        )

    typed_payload: GameSimulationPayload = payload

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "gamification_experiment_latest.json"
    md_path = data_dir / "gamification_experiment_latest.md"
    json_path.write_text(json.dumps(typed_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(typed_payload), encoding="utf-8")

    winner = typed_payload["winner"]
    print(f"JSON salvo em: {json_path}")
    print(f"Markdown salvo em: {md_path}")
    print(
        "Resumo: "
        f"vencedor={winner['name']} | "
        f"capital_final={winner['final_capital']:.2f} | "
        f"retorno={winner['total_return_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()

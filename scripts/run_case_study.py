from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.thesis_case_study import run_thesis_case_study


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa estudo de caso de tese estruturada com base no historico local "
            "(point-in-time)."
        )
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID do usuario.")
    parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Lista separada por virgula de instrumentos (ex.: PETR4,VALE3).",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=8,
        help="Quantidade de barras para janela de validacao/saida.",
    )
    return parser.parse_args()


def to_markdown(payload: dict[str, object]) -> str:
    selected_case = payload["selected_case"]
    thesis = selected_case["thesis"]
    operation = selected_case["structured_operation"]
    outcome = selected_case["outcome"]
    kpis = selected_case["kpis"]
    fundamental_context = selected_case["fundamental_context"]
    lines = [
        "# Estudo de Caso SSE",
        "",
        "## Tese Selecionada",
        f"- `thesis_id`: {thesis['thesis_id']}",
        f"- `instrument`: {thesis['instrument']}",
        f"- `direction`: {thesis['direction']}",
        f"- `thesis_raised_at`: {selected_case['thesis_raised_at']}",
        f"- `suggested_entry_time`: {selected_case['suggested_entry_time']}",
        f"- `suggested_exit_time`: {selected_case['suggested_exit_time']}",
        f"- `confidence_tese_pct`: {thesis['confidence_tese_pct']:.2f}%",
        f"- `success_probability_pct`: {thesis['success_probability_pct']:.2f}%",
        f"- `technical_support_pct`: {thesis['technical_support_pct']:.2f}%",
        f"- `fundamental_support_pct`: {thesis['fundamental_support_pct']:.2f}%",
        f"- `fundamental_available`: {thesis['fundamental_available']}",
        "",
        "## Operacao Estruturada",
        f"- `strategy_id`: {operation['strategy_id']}",
        f"- `strategy_name`: {operation['strategy_name']}",
        f"- `max_gain_pct`: {operation['max_gain_pct']:.2f}%",
        f"- `max_loss_pct`: {operation['max_loss_pct']:.2f}%",
        "",
        "## Resultado de Saida",
        f"- `exit_price`: {outcome['exit_price']}",
        f"- `success`: {outcome['success']}",
        f"- `realized_financial_pct`: {outcome['realized_financial_pct']:.2f}%",
        f"- `effective_result_reason`: {selected_case['effective_result_reason']}",
        "",
        "## KPIs",
        f"- `confianca_tese_pct`: {kpis['confidence_tese_pct']:.2f}%",
        f"- `financeiro_esperado_pct`: {kpis['expected_financial_pct']:.2f}%",
        f"- `financeiro_real_pct`: {kpis['realized_financial_pct']:.2f}%",
        "",
        "## Fundamental Context",
        f"- `support_pct`: {fundamental_context['support_pct']:.2f}%",
        f"- `available`: {fundamental_context['available']}",
        f"- `rationale`: {', '.join(fundamental_context['rationale'])}",
        "",
        "## Guardrails",
        f"- {payload['disclaimer']}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    with SessionLocal() as db:
        payload = run_thesis_case_study(
            db,
            user_id=args.user_id,
            instruments=instruments or None,
            horizon_bars=args.horizon_bars,
        )

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "case_study_latest.json"
    md_path = data_dir / "case_study_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(payload), encoding="utf-8")

    print(f"JSON salvo em: {json_path}")
    print(f"Markdown salvo em: {md_path}")
    print("Resumo KPI:")
    kpis = payload["selected_case"]["kpis"]
    print(
        f"confianca={kpis['confidence_tese_pct']:.2f}% | "
        f"esperado={kpis['expected_financial_pct']:.2f}% | "
        f"real={kpis['realized_financial_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()

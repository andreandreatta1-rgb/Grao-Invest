from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db import SessionLocal
from app.services.thesis_current_monitor import run_current_thesis_monitor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa monitoramento de teses atuais com sugestao de operacao e "
            "status diario (educacional)."
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
        help="Quantidade de barras para construccao da tese.",
    )
    parser.add_argument(
        "--thesis-count",
        type=int,
        default=8,
        help="Quantidade maxima de teses atuais no reporte.",
    )
    parser.add_argument(
        "--recent-bars-window",
        type=int,
        default=7,
        help="Janela de barras para considerar tese como atual.",
    )
    return parser.parse_args()


def to_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary", {})
    theses = payload.get("theses", [])
    lines = [
        "# Monitor de Teses Atuais",
        "",
        f"- `generated_at`: {payload.get('generated_at', '-')}",
        f"- `thesis_count`: {payload.get('thesis_count', 0)}",
        f"- `target_hits`: {summary.get('target_hits', 0)}",
        f"- `stop_alerts`: {summary.get('stop_alerts', 0)}",
        f"- `monitoring_count`: {summary.get('monitoring_count', 0)}",
        (
            f"- `avg_unrealized_financial_pct`: "
            f"{summary.get('avg_unrealized_financial_pct', 0)}"
        ),
        "",
        "## Teses",
    ]
    if not isinstance(theses, list) or not theses:
        lines.append("- Sem teses atuais no recorte.")
    else:
        for item in theses:
            if not isinstance(item, dict):
                continue
            lines.extend(
                [
                    "",
                    f"- `thesis_id`: {item.get('thesis_id', '-')}",
                    f"- `instrument`: {item.get('instrument', '-')}",
                    f"- `direction`: {item.get('direction', '-')}",
                    f"- `reason_category`: {item.get('reason_category', '-')}",
                    f"- `entry_price`: {item.get('entry_price', '-')}",
                    f"- `target_price`: {item.get('target_price', '-')}",
                    f"- `stop_price`: {item.get('stop_price', '-')}",
                    f"- `latest_price`: {item.get('latest_price', '-')}",
                    f"- `monitor_status`: {item.get('monitor_status', '-')}",
                    f"- `suggested_action`: {item.get('suggested_action', '-')}",
                    (
                        f"- `expected_financial_pct`: {item.get('expected_financial_pct', '-')}"
                    ),
                    (
                        f"- `unrealized_financial_pct`: "
                        f"{item.get('unrealized_financial_pct', '-')}"
                    ),
                ]
            )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    with SessionLocal() as db:
        payload = run_current_thesis_monitor(
            db,
            user_id=args.user_id,
            instruments=instruments or None,
            horizon_bars=args.horizon_bars,
            thesis_count=args.thesis_count,
            recent_bars_window=args.recent_bars_window,
        )

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "current_thesis_monitor_latest.json"
    md_path = data_dir / "current_thesis_monitor_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(payload), encoding="utf-8")

    print(f"JSON salvo em: {json_path}")
    print(f"Markdown salvo em: {md_path}")


if __name__ == "__main__":
    main()


from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.db import SessionLocal
from app.services.thesis_case_study import run_thesis_case_study


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera report executivo simplificado (JSON/MD/SVG).")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument(
        "--instruments",
        type=str,
        default="PETR4,MGLU3,RENT3,VALE3,ITUB4",
        help="Lista separada por virgula.",
    )
    parser.add_argument("--horizon-bars", type=int, default=8)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _fmt_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.astimezone(UTC).date().isoformat()


def _fmt_brl(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}%"


def _classify_reason(thesis: dict[str, Any]) -> str:
    signals = thesis.get("supporting_signals", [])
    if not isinstance(signals, list):
        signals = []
    signal_str = " ".join(str(item).lower() for item in signals)
    reasons: list[str] = []
    if "momento_" in signal_str or "suporte_tecnico_" in signal_str:
        reasons.append("grafico/tecnico")
    if "fundamental_" in signal_str or "valuation_" in signal_str or "roe_" in signal_str:
        reasons.append("fundamentalista")
    if "news_sentiment_" in signal_str:
        reasons.append("noticias/contexto externo")
    if "geo_oil_" in signal_str and "nao_aplicavel" not in signal_str and "sem_evento" not in signal_str:
        reasons.append("geopolitico")
    if not reasons:
        return "misto"
    return " + ".join(dict.fromkeys(reasons))


def _extract_example(case_payload: dict[str, Any]) -> dict[str, Any]:
    selected = case_payload.get("selected_case", {})
    thesis = selected.get("thesis", {})
    operation = selected.get("structured_operation", {})
    outcome = selected.get("outcome", {})
    reason = _classify_reason(thesis)
    entry_price = float(thesis.get("entry_price", 0.0))
    target_price = float(thesis.get("target_price", 0.0))
    stop_price = float(thesis.get("stop_price", 0.0))
    direction = str(thesis.get("direction", "")).lower()
    if direction == "bullish":
        high_guard = target_price
        low_guard = stop_price
    elif direction == "bearish":
        high_guard = stop_price
        low_guard = target_price
    else:
        high_guard = max(target_price, entry_price)
        low_guard = min(stop_price, entry_price)

    return {
        "instrument": thesis.get("instrument", "-"),
        "thesis_id": thesis.get("thesis_id", "-"),
        "reason": reason,
        "strategy": operation.get("strategy_name", "-"),
        "entry_date": _fmt_date(selected.get("suggested_entry_time")),
        "entry_price": entry_price,
        "target_price": target_price,
        "high_guard": high_guard,
        "low_guard": low_guard,
        "exit_date": _fmt_date(selected.get("suggested_exit_time")),
        "exit_price": float(outcome.get("exit_price", 0.0)),
        "realized_financial_pct": float(outcome.get("realized_financial_pct", 0.0)),
        "expected_financial_pct": float(thesis.get("expected_financial_pct", 0.0)),
        "effective_result_reason": selected.get("effective_result_reason", "-"),
    }


def _cycle_window_metrics(policy_state: dict[str, Any], days: int) -> dict[str, float]:
    history = policy_state.get("cycle_history", [])
    if not isinstance(history, list):
        history = []
    cutoff = datetime.now(UTC) - timedelta(days=days)
    samples: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        run_at = item.get("run_at")
        if not isinstance(run_at, str):
            continue
        try:
            dt = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            samples.append(item)
    if not samples:
        return {"success_rate_pct": 0.0, "discovery_rate_pct": 0.0, "sample_count": 0}
    success = sum(float(s.get("success_rate_pct", 0.0)) for s in samples) / len(samples)
    discovery = sum(float(s.get("discovery_rate_pct", 0.0)) for s in samples) / len(samples)
    return {
        "success_rate_pct": round(success, 4),
        "discovery_rate_pct": round(discovery, 4),
        "sample_count": len(samples),
    }


def _build_svg(report: dict[str, Any], output_path: Path) -> None:
    objective = "Objetivo: encontrar teses no historico, simular operacoes e evoluir a taxa de acerto."
    kpis = report["kpis"]
    evo = report["evolution"]
    examples = report["examples"][:4]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="980" viewBox="0 0 1400 980">',
        '<rect width="1400" height="980" fill="#0f172a"/>',
        '<rect x="30" y="24" width="1340" height="110" rx="14" fill="#111827"/>',
        '<text x="56" y="62" fill="#f9fafb" font-size="32" font-family="Segoe UI,Arial">Radar Executivo - Evolucao de Teses</text>',
        f'<text x="56" y="95" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">{objective}</text>',
        f'<text x="56" y="121" fill="#94a3b8" font-size="15" font-family="Segoe UI,Arial">Atualizado em {report["generated_at"]}</text>',
        '<rect x="30" y="150" width="1340" height="130" rx="14" fill="#111827"/>',
        f'<text x="56" y="190" fill="#e2e8f0" font-size="20" font-family="Segoe UI,Arial">Resultado consolidado: sucesso {_fmt_pct(kpis["success_rate_pct"])} | descoberta {_fmt_pct(kpis["discovery_rate_pct"])} | confianca media {_fmt_pct(kpis["avg_confidence_pct"])}</text>',
        f'<text x="56" y="223" fill="#93c5fd" font-size="20" font-family="Segoe UI,Arial">Financeiro esperado {_fmt_pct(kpis["avg_expected_financial_pct"])} vs realizado {_fmt_pct(kpis["avg_realized_financial_pct"])}</text>',
        f'<text x="56" y="255" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">Ultimo dia: sucesso {_fmt_pct(evo["last_day"]["success_rate_pct"])} | Ultimos 7 dias: sucesso {_fmt_pct(evo["last_7_days"]["success_rate_pct"])}</text>',
    ]

    y = 300
    for example in examples:
        lines.extend(
            [
                f'<rect x="30" y="{y}" width="1340" height="150" rx="12" fill="#111827"/>',
                f'<text x="56" y="{y + 34}" fill="#f8fafc" font-size="22" font-family="Segoe UI,Arial">{example["instrument"]} | {example["strategy"]} | motivo: {example["reason"]}</text>',
                f'<text x="56" y="{y + 64}" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">Entrada {_fmt_date(example["entry_date"])} em {_fmt_brl(example["entry_price"])} | alvo {_fmt_brl(example["target_price"])}</text>',
                f'<text x="56" y="{y + 92}" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">Trava alta {_fmt_brl(example["high_guard"])} | trava baixa {_fmt_brl(example["low_guard"])}</text>',
                f'<text x="56" y="{y + 120}" fill="#86efac" font-size="18" font-family="Segoe UI,Arial">Saida {_fmt_date(example["exit_date"])} em {_fmt_brl(example["exit_price"])} | resultado {_fmt_pct(example["realized_financial_pct"])} (esperado {_fmt_pct(example["expected_financial_pct"])})</text>',
            ]
        )
        y += 162

    lines.extend(
        [
            '<text x="30" y="955" fill="#94a3b8" font-size="14" font-family="Segoe UI,Arial">Conteudo educacional. Nao constitui recomendacao de investimento.</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = _parse_args()
    instruments = [item.strip().upper() for item in args.instruments.split(",") if item.strip()]
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    examples: list[dict[str, Any]] = []
    with SessionLocal() as db:
        for instrument in instruments:
            try:
                case_payload = run_thesis_case_study(
                    db,
                    user_id=args.user_id,
                    instruments=[instrument],
                    horizon_bars=args.horizon_bars,
                )
            except Exception:
                continue
            examples.append(_extract_example(case_payload))

    skill_learning = _load_json(data_dir / "thesis_skill_learning_latest.json")
    shadow_cycle = _load_json(data_dir / "thesis_shadow_cycle_latest.json")
    policy_state = _load_json(data_dir / "thesis_policy_state.json")

    cycle_summary = {}
    cycles = skill_learning.get("cycles", [])
    if isinstance(cycles, list) and cycles:
        latest_cycle = cycles[-1]
        if isinstance(latest_cycle, dict):
            cycle_summary = latest_cycle.get("summary", {}) or {}
    if not cycle_summary:
        cycle_summary = {}

    shadow_metrics = shadow_cycle.get("shadow_metrics", {}) if isinstance(shadow_cycle, dict) else {}

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "objective": "Descobrir teses historicas, testar operacoes e melhorar assertividade continuamente.",
        "kpis": {
            "success_rate_pct": float(cycle_summary.get("success_rate_pct", shadow_metrics.get("success_rate_pct", 0.0))),
            "discovery_rate_pct": float(shadow_metrics.get("discovery_rate_pct", 0.0)),
            "avg_confidence_pct": float(cycle_summary.get("avg_confidence_tese_pct", 0.0)),
            "avg_expected_financial_pct": float(cycle_summary.get("avg_expected_financial_pct", 0.0)),
            "avg_realized_financial_pct": float(cycle_summary.get("avg_realized_financial_pct", 0.0)),
        },
        "evolution": {
            "last_day": _cycle_window_metrics(policy_state, 1),
            "last_7_days": _cycle_window_metrics(policy_state, 7),
        },
        "examples": examples,
    }

    json_path = data_dir / "executive_report_latest.json"
    md_path = data_dir / "executive_report_latest.md"
    svg_path = data_dir / "executive_report_snapshot.svg"

    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    md_lines = [
        "# Report Executivo",
        "",
        f"- Atualizado em: {report['generated_at']}",
        f"- Objetivo: {report['objective']}",
        "",
        "## Resultado consolidado",
        f"- Taxa de sucesso: {_fmt_pct(report['kpis']['success_rate_pct'])}",
        f"- Taxa de descoberta: {_fmt_pct(report['kpis']['discovery_rate_pct'])}",
        f"- Confianca media: {_fmt_pct(report['kpis']['avg_confidence_pct'])}",
        f"- Financeiro esperado medio: {_fmt_pct(report['kpis']['avg_expected_financial_pct'])}",
        f"- Financeiro realizado medio: {_fmt_pct(report['kpis']['avg_realized_financial_pct'])}",
        "",
        "## Evolucao",
        (
            f"- Ultimo dia: sucesso {_fmt_pct(report['evolution']['last_day']['success_rate_pct'])} | "
            f"descoberta {_fmt_pct(report['evolution']['last_day']['discovery_rate_pct'])} | "
            f"ciclos {int(report['evolution']['last_day']['sample_count'])}"
        ),
        (
            f"- Ultimos 7 dias: sucesso {_fmt_pct(report['evolution']['last_7_days']['success_rate_pct'])} | "
            f"descoberta {_fmt_pct(report['evolution']['last_7_days']['discovery_rate_pct'])} | "
            f"ciclos {int(report['evolution']['last_7_days']['sample_count'])}"
        ),
        "",
        "## Exemplos de teses avaliadas",
    ]
    for ex in examples:
        md_lines.extend(
            [
                "",
                f"- Ativo: {ex['instrument']} ({ex['thesis_id']})",
                f"- Porque entrou: {ex['reason']}",
                f"- Operacao: {ex['strategy']}",
                f"- Entrada: {_fmt_date(ex['entry_date'])} em {_fmt_brl(ex['entry_price'])}",
                f"- Pretensao de saida: {_fmt_brl(ex['target_price'])}",
                f"- Trava de alta: {_fmt_brl(ex['high_guard'])} | trava de baixa: {_fmt_brl(ex['low_guard'])}",
                f"- Saida efetiva: {_fmt_date(ex['exit_date'])} em {_fmt_brl(ex['exit_price'])}",
                f"- Resultado: {_fmt_pct(ex['realized_financial_pct'])} (esperado {_fmt_pct(ex['expected_financial_pct'])})",
                f"- Leitura do resultado: {ex['effective_result_reason']}",
            ]
        )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    _build_svg(report, svg_path)

    print(f"JSON salvo em: {json_path}")
    print(f"Markdown salvo em: {md_path}")
    print(f"SVG salvo em: {svg_path}")


if __name__ == "__main__":
    main()


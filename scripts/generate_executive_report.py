from __future__ import annotations

import argparse
import html
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


def _latest_completed_window_report(data_dir: Path) -> tuple[dict[str, Any], Path | None]:
    window_root = data_dir / "case_study_windows"
    if not window_root.exists():
        return {}, None
    candidates = sorted(
        window_root.glob("*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for report_path in candidates:
        payload = _load_json(report_path)
        if payload.get("status") == "completed":
            return payload, report_path.parent
    return {}, None


def _load_iteration_payload(window_dir: Path | None, iteration: object) -> dict[str, Any]:
    if window_dir is None or not isinstance(iteration, int):
        return {}
    payload_path = window_dir / "iterations" / f"iteration_{iteration:04d}.json"
    return _load_json(payload_path)


def _signal_summary(thesis: dict[str, Any]) -> str:
    direction = "alta" if str(thesis.get("direction", "")).lower() == "bullish" else "baixa"
    support = float(thesis.get("support_rate_pct", 0.0))
    technical = float(thesis.get("technical_support_pct", 0.0))
    fundamental = float(thesis.get("fundamental_support_pct", 0.0))
    news = float(thesis.get("news_support_pct", 0.0))
    missing: list[str] = []
    if not thesis.get("fundamental_available"):
        missing.append("fundamental")
    if not thesis.get("news_available"):
        missing.append("noticias")
    missing_text = "sem lacunas relevantes" if not missing else "faltava " + " e ".join(missing)
    return (
        f"Tese de {direction}: tecnico {technical:.0f}%, suporte historico {support:.0f}%, "
        f"fundamental {fundamental:.0f}% e noticias {news:.0f}%; {missing_text}."
    )


def _learning_action(tags: list[str], success: bool) -> str:
    tag_set = set(tags)
    if not success and "confidence_overweighted_by_technical" in tag_set:
        return (
            "Na proxima rodada, reduzir a confianca ou bloquear quando o sinal tecnico vier forte, "
            "mas o suporte historico for baixo e faltarem confirmacoes externas."
        )
    if success and "expected_overstretch_without_confirmation" in tag_set:
        return (
            "Manter a tese quando houver confirmacao fundamental/noticias, mas recalibrar o alvo "
            "quando o retorno esperado ficar agressivo demais."
        )
    if success and "missing_confirmation_inputs" in tag_set:
        return (
            "Falta de confirmacao isolada nao deve bloquear a tese; ela deve virar penalidade e exigir "
            "monitoramento mais curto."
        )
    return (
        "Registrar o padrao no pos-morte e testar a regra em shadow antes de mudar a politica ativa."
    )


def _extract_learning_case(
    *,
    label: str,
    case_payload: dict[str, Any],
    narrative: str,
) -> dict[str, Any]:
    selected = case_payload.get("selected_case", {})
    if not isinstance(selected, dict):
        selected = {}
    thesis = selected.get("thesis", {})
    if not isinstance(thesis, dict):
        thesis = {}
    operation = selected.get("structured_operation", {})
    if not isinstance(operation, dict):
        operation = {}
    outcome = selected.get("outcome", {})
    if not isinstance(outcome, dict):
        outcome = {}
    postmortem = case_payload.get("postmortem", {})
    if not isinstance(postmortem, dict):
        postmortem = {}
    tags = selected.get(
        "postmortem_tags",
        case_payload.get("postmortem_tags", postmortem.get("analysis_tags", [])),
    )
    if not isinstance(tags, list):
        tags = []
    normalized_tags = [str(tag) for tag in tags]
    success = bool(outcome.get("success", False))
    return {
        "label": label,
        "instrument": thesis.get("instrument", "-"),
        "thesis_id": thesis.get("thesis_id", "-"),
        "strategy": operation.get("strategy_name", "-"),
        "entry_date": _fmt_date(selected.get("suggested_entry_time")),
        "entry_price": float(thesis.get("entry_price", 0.0)),
        "target_price": float(thesis.get("target_price", 0.0)),
        "stop_price": float(thesis.get("stop_price", 0.0)),
        "exit_date": _fmt_date(selected.get("suggested_exit_time")),
        "exit_price": float(outcome.get("exit_price", 0.0)),
        "confidence_pct": float(thesis.get("confidence_tese_pct", 0.0)),
        "expected_financial_pct": float(thesis.get("expected_financial_pct", 0.0)),
        "realized_financial_pct": float(outcome.get("realized_financial_pct", 0.0)),
        "max_gain_pct": float(operation.get("max_gain_pct", 0.0)),
        "max_loss_pct": float(operation.get("max_loss_pct", 0.0)),
        "why_entered": _signal_summary(thesis),
        "result_reading": selected.get("effective_result_reason", "-"),
        "postmortem_tags": normalized_tags[:8],
        "learning": _learning_action(normalized_tags, success),
        "narrative": narrative,
        "success": success,
    }


def _build_learning_evolution(
    window_report: dict[str, Any],
    window_dir: Path | None,
) -> dict[str, Any]:
    worst_cases = window_report.get("worst_cases", [])
    latest_cases = window_report.get("latest_cases", [])
    best_cases = window_report.get("best_cases", [])
    if not isinstance(worst_cases, list):
        worst_cases = []
    if not isinstance(latest_cases, list):
        latest_cases = []
    if not isinstance(best_cases, list):
        best_cases = []

    failure_case = next((item for item in worst_cases if isinstance(item, dict)), {})
    confirmed_case = next(
        (
            item
            for item in latest_cases
            if isinstance(item, dict) and item.get("instrument") == "PETR4"
        ),
        {},
    )
    exception_case = next((item for item in best_cases if isinstance(item, dict)), {})

    cases: list[dict[str, Any]] = []
    if failure_case:
        payload = _load_iteration_payload(window_dir, failure_case.get("iteration"))
        cases.append(
            _extract_learning_case(
                label="Tese A: tecnico forte, confirmacao fraca",
                case_payload=payload,
                narrative=(
                    "Entramos porque o grafico parecia forte. O resultado mostrou que o tecnico, "
                    "sozinho, estava inflando a confianca."
                ),
            )
        )
    if confirmed_case:
        payload = _load_iteration_payload(window_dir, confirmed_case.get("iteration"))
        cases.append(
            _extract_learning_case(
                label="Tese B: confirmacao fundamental sustentou melhor",
                case_payload=payload,
                narrative=(
                    "Aqui o tecnico veio acompanhado de fundamento e noticias. O retorno ficou abaixo "
                    "do esperado, mas a tese foi positiva."
                ),
            )
        )
    if exception_case:
        payload = _load_iteration_payload(window_dir, exception_case.get("iteration"))
        cases.append(
            _extract_learning_case(
                label="Tese C: excecao que nao deve virar bloqueio automatico",
                case_payload=payload,
                narrative=(
                    "Mesmo sem todas as confirmacoes, a operacao funcionou. A licao e penalizar "
                    "a ausencia de dados, nao bloquear tudo de forma cega."
                ),
            )
        )

    return {
        "headline": "O pos-morte esta transformando resultado em regra candidata.",
        "context": (
            "A politica ativa ainda nao mudou. O aprendizado foi registrado para ser testado em shadow "
            "antes de qualquer promocao."
        ),
        "cases": cases,
        "conclusion": (
            "Tecnico forte continua relevante, mas passa a precisar de confirmacao. "
            "Quando faltam fundamentos/noticias e o suporte historico e baixo, a proxima politica "
            "deve reduzir confianca, reduzir alvo ou bloquear a entrada."
        ),
    }


def _examples_from_window_report(
    window_report: dict[str, Any],
    window_dir: Path | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_iterations: set[int] = set()
    for key in ("latest_cases", "best_cases", "worst_cases"):
        raw_items = window_report.get(key, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            iteration = item.get("iteration")
            if not isinstance(iteration, int) or iteration in seen_iterations:
                continue
            payload = _load_iteration_payload(window_dir, iteration)
            if payload:
                rows.append(_extract_example(payload))
                seen_iterations.add(iteration)
            if len(rows) >= 6:
                return rows
    return rows


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
    learning = report.get("learning_evolution", {})
    learning_cases = learning.get("cases", []) if isinstance(learning, dict) else []
    examples = report["examples"][:3]

    def svg_text(value: object) -> str:
        return html.escape(str(value), quote=False)

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1180" viewBox="0 0 1400 1180">',
        '<rect width="1400" height="1180" fill="#0f172a"/>',
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
    lines.extend(
        [
            f'<rect x="30" y="{y}" width="1340" height="170" rx="14" fill="#111827"/>',
            '<text x="56" y="338" fill="#f8fafc" font-size="24" font-family="Segoe UI,Arial">Evolucao do aprendizado</text>',
            f'<text x="56" y="370" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">{svg_text(learning.get("headline", "-") if isinstance(learning, dict) else "-")}</text>',
            f'<text x="56" y="400" fill="#93c5fd" font-size="18" font-family="Segoe UI,Arial">{svg_text(learning.get("conclusion", "-") if isinstance(learning, dict) else "-")[:150]}</text>',
        ]
    )
    if isinstance(learning_cases, list) and learning_cases:
        first_case = learning_cases[0]
        if isinstance(first_case, dict):
            lines.append(
                f'<text x="56" y="438" fill="#fca5a5" font-size="17" font-family="Segoe UI,Arial">{svg_text(first_case.get("label", "-"))}: {svg_text(first_case.get("instrument", "-"))} | real {_fmt_pct(first_case.get("realized_financial_pct"))} | esperado {_fmt_pct(first_case.get("expected_financial_pct"))}</text>'
            )
    y = 500
    for example in examples:
        lines.extend(
            [
                f'<rect x="30" y="{y}" width="1340" height="150" rx="12" fill="#111827"/>',
                f'<text x="56" y="{y + 34}" fill="#f8fafc" font-size="22" font-family="Segoe UI,Arial">{svg_text(example["instrument"])} | {svg_text(example["strategy"])} | motivo: {svg_text(example["reason"])}</text>',
                f'<text x="56" y="{y + 64}" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">Entrada {_fmt_date(example["entry_date"])} em {_fmt_brl(example["entry_price"])} | alvo {_fmt_brl(example["target_price"])}</text>',
                f'<text x="56" y="{y + 92}" fill="#cbd5e1" font-size="18" font-family="Segoe UI,Arial">Trava alta {_fmt_brl(example["high_guard"])} | trava baixa {_fmt_brl(example["low_guard"])}</text>',
                f'<text x="56" y="{y + 120}" fill="#86efac" font-size="18" font-family="Segoe UI,Arial">Saida {_fmt_date(example["exit_date"])} em {_fmt_brl(example["exit_price"])} | resultado {_fmt_pct(example["realized_financial_pct"])} (esperado {_fmt_pct(example["expected_financial_pct"])})</text>',
            ]
        )
        y += 162

    lines.extend(
        [
            '<text x="30" y="1155" fill="#94a3b8" font-size="14" font-family="Segoe UI,Arial">Conteudo educacional. Nao constitui recomendacao de investimento.</text>',
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

    window_report, window_dir = _latest_completed_window_report(data_dir)
    examples = _examples_from_window_report(window_report, window_dir)
    if not examples:
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
    window_kpis = window_report.get("kpis", {}) if isinstance(window_report, dict) else {}
    learning_evolution = _build_learning_evolution(window_report, window_dir) if window_report else {}

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "objective": "Descobrir teses historicas, testar operacoes e melhorar assertividade continuamente.",
        "kpis": {
            "success_rate_pct": float(
                window_kpis.get(
                    "thesis_success_rate_pct",
                    cycle_summary.get(
                        "success_rate_pct",
                        shadow_metrics.get("success_rate_pct", 0.0),
                    ),
                )
            ),
            "discovery_rate_pct": float(shadow_metrics.get("discovery_rate_pct", 0.0)),
            "avg_confidence_pct": float(
                window_kpis.get("avg_confidence_tese_pct", cycle_summary.get("avg_confidence_tese_pct", 0.0))
            ),
            "avg_expected_financial_pct": float(
                window_kpis.get("avg_expected_financial_pct", cycle_summary.get("avg_expected_financial_pct", 0.0))
            ),
            "avg_realized_financial_pct": float(
                window_kpis.get("avg_realized_financial_pct", cycle_summary.get("avg_realized_financial_pct", 0.0))
            ),
            "total_iterations": int(window_kpis.get("total_iterations", 0)),
            "engine_success_rate_pct": float(window_kpis.get("engine_success_rate_pct", 0.0)),
        },
        "evolution": {
            "last_day": _cycle_window_metrics(policy_state, 1),
            "last_7_days": _cycle_window_metrics(policy_state, 7),
        },
        "learning_evolution": learning_evolution,
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
        "## Evolucao do aprendizado",
        f"- {learning_evolution.get('headline', 'Sem aprendizado consolidado ainda.')}",
        f"- {learning_evolution.get('context', '-')}",
        f"- Conclusao: {learning_evolution.get('conclusion', '-')}",
        "",
        "### Casos do pos-morte",
    ]
    for case in learning_evolution.get("cases", []):
        if not isinstance(case, dict):
            continue
        md_lines.extend(
            [
                "",
                f"- {case['label']}: {case['instrument']} ({case['strategy']})",
                f"- Porque entrou: {case['why_entered']}",
                (
                    f"- Entrada {_fmt_date(case['entry_date'])} em {_fmt_brl(case['entry_price'])}; "
                    f"alvo {_fmt_brl(case['target_price'])}; stop {_fmt_brl(case['stop_price'])}"
                ),
                (
                    f"- Saida {_fmt_date(case['exit_date'])} em {_fmt_brl(case['exit_price'])}; "
                    f"resultado {_fmt_pct(case['realized_financial_pct'])} "
                    f"(esperado {_fmt_pct(case['expected_financial_pct'])})"
                ),
                f"- Aprendizado: {case['learning']}",
            ]
        )
    md_lines.extend(
        [
            "",
            "## Exemplos de teses avaliadas",
        ]
    )
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

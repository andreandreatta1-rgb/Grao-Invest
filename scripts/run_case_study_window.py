from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "services" / "api"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app.db import SessionLocal  # noqa: E402
from app.services.audit import record_audit_event  # noqa: E402
from app.services.thesis_case_study import run_thesis_case_study  # noqa: E402


DEFAULT_INSTRUMENTS = (
    "PETR4,VALE3,ITUB4,BBDC4,BBAS3,ABEV3,WEGE3,B3SA3,RENT3,SUZB3,"
    "JBSS3,PRIO3,RADL3,GGBR4,VBBR3,LREN3,HAPV3,BPAC11,RAIL3,CMIG4"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa thesis.case_study.generated em janela controlada, com historico "
            "por iteracao e relatorio consolidado ao final."
        )
    )
    parser.add_argument("--user-id", type=int, default=1, help="ID do usuario.")
    parser.add_argument(
        "--instruments",
        type=str,
        default=DEFAULT_INSTRUMENTS,
        help="Lista CSV do pool de instrumentos.",
    )
    parser.add_argument(
        "--horizon-bars",
        type=int,
        default=8,
        help="Horizonte de barras por estudo de caso.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=120.0,
        help="Duracao da janela em minutos.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=5.0,
        help="Pausa entre iteracoes concluidas.",
    )
    parser.add_argument(
        "--min-instruments-per-run",
        type=int,
        default=4,
        help="Quantidade minima de instrumentos por iteracao.",
    )
    parser.add_argument(
        "--max-instruments-per-run",
        type=int,
        default=8,
        help="Quantidade maxima de instrumentos por iteracao.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Limite opcional de iteracoes (0 = sem limite).",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=8,
        help="Limite de falhas consecutivas para abortar.",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Rotulo opcional da janela. Vazio = gera automatico.",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def iso_local(value: datetime) -> str:
    return value.astimezone().replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 4)


def safe_pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def compact_signal_list(items: list[str], limit: int = 5) -> list[str]:
    return [item for item in items[:limit] if isinstance(item, str)]


def case_payload_to_markdown(payload: dict[str, Any]) -> str:
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
        f"- thesis_id: {thesis['thesis_id']}",
        f"- instrument: {thesis['instrument']}",
        f"- direction: {thesis['direction']}",
        f"- thesis_raised_at: {selected_case['thesis_raised_at']}",
        f"- suggested_entry_time: {selected_case['suggested_entry_time']}",
        f"- suggested_exit_time: {selected_case['suggested_exit_time']}",
        f"- confidence_tese_pct: {thesis['confidence_tese_pct']:.2f}%",
        f"- success_probability_pct: {thesis['success_probability_pct']:.2f}%",
        f"- technical_support_pct: {thesis['technical_support_pct']:.2f}%",
        f"- fundamental_support_pct: {thesis['fundamental_support_pct']:.2f}%",
        f"- fundamental_available: {thesis['fundamental_available']}",
        "",
        "## Operacao Estruturada",
        f"- strategy_id: {operation['strategy_id']}",
        f"- strategy_name: {operation['strategy_name']}",
        f"- max_gain_pct: {operation['max_gain_pct']:.2f}%",
        f"- max_loss_pct: {operation['max_loss_pct']:.2f}%",
        "",
        "## Resultado de Saida",
        f"- exit_price: {outcome['exit_price']}",
        f"- success: {outcome['success']}",
        f"- realized_financial_pct: {outcome['realized_financial_pct']:.2f}%",
        f"- effective_result_reason: {selected_case['effective_result_reason']}",
        "",
        "## KPIs",
        f"- confianca_tese_pct: {kpis['confidence_tese_pct']:.2f}%",
        f"- financeiro_esperado_pct: {kpis['expected_financial_pct']:.2f}%",
        f"- financeiro_real_pct: {kpis['realized_financial_pct']:.2f}%",
        "",
        "## Fundamental Context",
        f"- support_pct: {fundamental_context['support_pct']:.2f}%",
        f"- available: {fundamental_context['available']}",
        f"- rationale: {', '.join(fundamental_context['rationale'])}",
        "",
        "## Guardrails",
        f"- {payload['disclaimer']}",
    ]
    return "\n".join(lines)


def normalize_instrument_pool(raw_csv: str) -> list[str]:
    return [item.strip().upper() for item in raw_csv.split(",") if item.strip()]


def select_instruments(
    pool: list[str],
    *,
    min_count: int,
    max_count: int,
) -> list[str]:
    if len(pool) <= max(1, min_count):
        return list(pool)
    upper = min(len(pool), max(max_count, min_count))
    lower = max(1, min(min_count, upper))
    requested_count = random.randint(lower, upper)
    return random.sample(pool, requested_count)


def summarize_case_payload(
    *,
    iteration: int,
    requested_instruments: list[str],
    payload: dict[str, Any],
    payload_path: Path,
    started_at: datetime,
    finished_at: datetime,
) -> dict[str, Any]:
    selected_case = payload["selected_case"]
    thesis = selected_case["thesis"]
    operation = selected_case["structured_operation"]
    outcome = selected_case["outcome"]
    pipeline = payload["pipeline"]
    policy = pipeline["policy"]
    postmortem = payload.get("postmortem", {})
    duration_seconds = round((finished_at - started_at).total_seconds(), 3)

    return {
        "status": "success",
        "iteration": iteration,
        "requested_instruments": requested_instruments,
        "started_at_utc": iso_utc(started_at),
        "finished_at_utc": iso_utc(finished_at),
        "duration_seconds": duration_seconds,
        "payload_file": str(payload_path),
        "selected_thesis_id": thesis["thesis_id"],
        "instrument": thesis["instrument"],
        "direction": thesis["direction"],
        "entry_time": selected_case["suggested_entry_time"],
        "exit_time": selected_case["suggested_exit_time"],
        "strategy_id": operation["strategy_id"],
        "strategy_name": operation["strategy_name"],
        "policy_name": policy["active_policy"],
        "confidence_tese_pct": thesis["confidence_tese_pct"],
        "expected_financial_pct": selected_case["kpis"]["expected_financial_pct"],
        "realized_financial_pct": selected_case["kpis"]["realized_financial_pct"],
        "success": bool(outcome["success"]),
        "candidate_count": pipeline["candidate_count"],
        "policy_candidate_count": pipeline["policy_candidate_count"],
        "validated_count": pipeline["validated_count"],
        "support_rate_pct": thesis["support_rate_pct"],
        "technical_support_pct": thesis["technical_support_pct"],
        "fundamental_support_pct": thesis["fundamental_support_pct"],
        "news_support_pct": thesis["news_support_pct"],
        "geo_oil_support_pct": thesis["geo_oil_support_pct"],
        "news_available": thesis["news_available"],
        "fundamental_available": thesis["fundamental_available"],
        "geo_oil_available": thesis["geo_oil_available"],
        "max_gain_pct": operation["max_gain_pct"],
        "max_loss_pct": operation["max_loss_pct"],
        "breakeven_price": operation["breakeven_price"],
        "effective_result_reason": selected_case["effective_result_reason"],
        "supporting_signals": compact_signal_list(thesis["supporting_signals"]),
        "fundamental_rationale": compact_signal_list(
            selected_case["fundamental_context"]["rationale"],
            limit=3,
        ),
        "postmortem_tags": compact_signal_list(
            postmortem.get("analysis_tags", []) if isinstance(postmortem, dict) else [],
            limit=8,
        ),
        "postmortem_learning_actions": compact_signal_list(
            postmortem.get("learning_actions", []) if isinstance(postmortem, dict) else [],
            limit=8,
        ),
        "postmortem_signature": (
            str(postmortem.get("signature"))
            if isinstance(postmortem, dict) and isinstance(postmortem.get("signature"), str)
            else ""
        ),
    }


def summarize_failure(
    *,
    iteration: int,
    requested_instruments: list[str],
    started_at: datetime,
    finished_at: datetime,
    exc: BaseException,
) -> dict[str, Any]:
    return {
        "status": "failure",
        "iteration": iteration,
        "requested_instruments": requested_instruments,
        "started_at_utc": iso_utc(started_at),
        "finished_at_utc": iso_utc(finished_at),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
    }


def build_examples(records: list[dict[str, Any]], *, reverse: bool) -> list[dict[str, Any]]:
    if not records:
        return []
    ordered = sorted(records, key=lambda item: item["realized_financial_pct"], reverse=reverse)
    examples: list[dict[str, Any]] = []
    for item in ordered[:3]:
        examples.append(
            {
                "iteration": item["iteration"],
                "instrument": item["instrument"],
                "selected_thesis_id": item["selected_thesis_id"],
                "direction": item["direction"],
                "strategy_name": item["strategy_name"],
                "policy_name": item["policy_name"],
                "entry_time": item["entry_time"],
                "exit_time": item["exit_time"],
                "confidence_tese_pct": item["confidence_tese_pct"],
                "expected_financial_pct": item["expected_financial_pct"],
                "realized_financial_pct": item["realized_financial_pct"],
                "max_gain_pct": item["max_gain_pct"],
                "max_loss_pct": item["max_loss_pct"],
                "supporting_signals": item["supporting_signals"],
                "postmortem_tags": item.get("postmortem_tags", []),
                "effective_result_reason": item["effective_result_reason"],
            }
        )
    return examples


def build_report(
    *,
    run_id: str,
    started_at: datetime,
    planned_end_at: datetime,
    finished_at: datetime,
    history: list[dict[str, Any]],
    window_dir: Path,
) -> dict[str, Any]:
    successes = [item for item in history if item["status"] == "success"]
    failures = [item for item in history if item["status"] == "failure"]

    confidence_values = [float(item["confidence_tese_pct"]) for item in successes]
    expected_values = [float(item["expected_financial_pct"]) for item in successes]
    realized_values = [float(item["realized_financial_pct"]) for item in successes]
    duration_values = [float(item["duration_seconds"]) for item in history]
    candidate_values = [int(item["candidate_count"]) for item in successes]
    validated_values = [int(item["validated_count"]) for item in successes]

    instrument_counter = Counter(item["instrument"] for item in successes)
    strategy_counter = Counter(item["strategy_name"] for item in successes)
    policy_counter = Counter(item["policy_name"] for item in successes)
    thesis_counter = Counter(item["selected_thesis_id"] for item in successes)
    postmortem_tag_counter = Counter(
        tag
        for item in successes
        for tag in item.get("postmortem_tags", [])
        if isinstance(tag, str)
    )
    postmortem_action_counter = Counter(
        action
        for item in successes
        for action in item.get("postmortem_learning_actions", [])
        if isinstance(action, str)
    )

    realized_success_count = sum(1 for item in successes if item.get("success"))
    avg_expected = safe_mean(expected_values)
    avg_realized = safe_mean(realized_values)

    report = {
        "run_id": run_id,
        "status": "completed",
        "generated_at_utc": iso_utc(utc_now()),
        "window": {
            "started_at_utc": iso_utc(started_at),
            "started_at_local": iso_local(started_at),
            "planned_end_at_utc": iso_utc(planned_end_at),
            "planned_end_at_local": iso_local(planned_end_at),
            "finished_at_utc": iso_utc(finished_at),
            "finished_at_local": iso_local(finished_at),
            "planned_duration_minutes": round((planned_end_at - started_at).total_seconds() / 60.0, 2),
            "actual_duration_minutes": round((finished_at - started_at).total_seconds() / 60.0, 2),
        },
        "kpis": {
            "total_iterations": len(history),
            "completed_case_studies": len(successes),
            "failed_iterations": len(failures),
            "engine_success_rate_pct": safe_pct(len(successes), len(history)),
            "thesis_success_rate_pct": safe_pct(realized_success_count, len(successes)),
            "avg_confidence_tese_pct": safe_mean(confidence_values),
            "avg_expected_financial_pct": avg_expected,
            "avg_realized_financial_pct": avg_realized,
            "expected_vs_real_gap_pct": (
                None
                if avg_expected is None or avg_realized is None
                else round(avg_realized - avg_expected, 4)
            ),
            "avg_iteration_duration_seconds": safe_mean(duration_values),
            "avg_candidate_count": safe_mean([float(item) for item in candidate_values]),
            "avg_validated_count": safe_mean([float(item) for item in validated_values]),
            "unique_theses": len(thesis_counter),
            "unique_instruments": len(instrument_counter),
        },
        "distribution": {
            "top_instruments": instrument_counter.most_common(5),
            "top_strategies": strategy_counter.most_common(5),
            "policies_seen": policy_counter.most_common(),
            "top_postmortem_tags": postmortem_tag_counter.most_common(8),
            "top_learning_actions": postmortem_action_counter.most_common(8),
        },
        "best_cases": build_examples(successes, reverse=True),
        "worst_cases": build_examples(successes, reverse=False),
        "latest_cases": [
            {
                "iteration": item["iteration"],
                "instrument": item["instrument"],
                "selected_thesis_id": item["selected_thesis_id"],
                "strategy_name": item["strategy_name"],
                "policy_name": item["policy_name"],
                "confidence_tese_pct": item["confidence_tese_pct"],
                "expected_financial_pct": item["expected_financial_pct"],
                "realized_financial_pct": item["realized_financial_pct"],
                "success": item["success"],
                "supporting_signals": item["supporting_signals"],
                "postmortem_tags": item.get("postmortem_tags", []),
                "postmortem_signature": item.get("postmortem_signature", ""),
            }
            for item in successes[-3:]
        ],
        "failures": [
            {
                "iteration": item["iteration"],
                "error_type": item["error_type"],
                "error_message": item["error_message"],
            }
            for item in failures[-5:]
        ],
        "artifacts": {
            "window_dir": str(window_dir),
            "history_file": str(window_dir / "history.jsonl"),
            "status_file": str(window_dir / "status.json"),
            "report_json_file": str(window_dir / "report.json"),
            "report_md_file": str(window_dir / "report.md"),
        },
    }
    return report


def report_to_markdown(report: dict[str, Any]) -> str:
    kpis = report["kpis"]
    window = report["window"]
    distribution = report["distribution"]

    lines = [
        "# Relatorio da Janela de Case Study",
        "",
        f"- run_id: {report['run_id']}",
        f"- inicio_local: {window['started_at_local']}",
        f"- fim_local: {window['finished_at_local']}",
        f"- duracao_planejada_min: {window['planned_duration_minutes']}",
        f"- duracao_real_min: {window['actual_duration_minutes']}",
        "",
        "## KPIs Consolidados",
        f"- iteracoes_totais: {kpis['total_iterations']}",
        f"- case_studies_concluidos: {kpis['completed_case_studies']}",
        f"- falhas: {kpis['failed_iterations']}",
        f"- engine_success_rate_pct: {kpis['engine_success_rate_pct']}",
        f"- thesis_success_rate_pct: {kpis['thesis_success_rate_pct']}",
        f"- avg_confidence_tese_pct: {kpis['avg_confidence_tese_pct']}",
        f"- avg_expected_financial_pct: {kpis['avg_expected_financial_pct']}",
        f"- avg_realized_financial_pct: {kpis['avg_realized_financial_pct']}",
        f"- expected_vs_real_gap_pct: {kpis['expected_vs_real_gap_pct']}",
        f"- avg_iteration_duration_seconds: {kpis['avg_iteration_duration_seconds']}",
        f"- unique_theses: {kpis['unique_theses']}",
        f"- unique_instruments: {kpis['unique_instruments']}",
        "",
        "## Distribuicao",
        f"- top_instruments: {distribution['top_instruments']}",
        f"- top_strategies: {distribution['top_strategies']}",
        f"- policies_seen: {distribution['policies_seen']}",
        f"- top_postmortem_tags: {distribution['top_postmortem_tags']}",
        f"- top_learning_actions: {distribution['top_learning_actions']}",
        "",
        "## Melhores Casos",
    ]

    for item in report["best_cases"]:
        lines.extend(
            [
                (
                    f"- iter={item['iteration']} | {item['instrument']} | {item['strategy_name']} "
                    f"| conf={item['confidence_tese_pct']:.2f}% | "
                    f"esp={item['expected_financial_pct']:.2f}% | "
                    f"real={item['realized_financial_pct']:.2f}%"
                ),
                f"  sinais: {', '.join(item['supporting_signals'])}",
                f"  postmortem: {', '.join(item.get('postmortem_tags', []))}",
            ]
        )

    lines.extend(["", "## Piores Casos"])
    for item in report["worst_cases"]:
        lines.extend(
            [
                (
                    f"- iter={item['iteration']} | {item['instrument']} | {item['strategy_name']} "
                    f"| conf={item['confidence_tese_pct']:.2f}% | "
                    f"esp={item['expected_financial_pct']:.2f}% | "
                    f"real={item['realized_financial_pct']:.2f}%"
                ),
                f"  sinais: {', '.join(item['supporting_signals'])}",
                f"  postmortem: {', '.join(item.get('postmortem_tags', []))}",
            ]
        )

    if report["failures"]:
        lines.extend(["", "## Falhas Recentes"])
        for item in report["failures"]:
            lines.append(
                f"- iter={item['iteration']} | {item['error_type']} | {item['error_message']}"
            )

    lines.extend(
        [
            "",
            "## Artefatos",
            f"- report_json_file: {report['artifacts']['report_json_file']}",
            f"- report_md_file: {report['artifacts']['report_md_file']}",
            f"- history_file: {report['artifacts']['history_file']}",
        ]
    )

    return "\n".join(lines)


def build_status(
    *,
    run_id: str,
    state: str,
    started_at: datetime,
    planned_end_at: datetime,
    completed_iterations: int,
    success_count: int,
    failure_count: int,
    last_record: dict[str, Any] | None,
    report_path: Path | None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "state": state,
        "updated_at_utc": iso_utc(utc_now()),
        "started_at_utc": iso_utc(started_at),
        "started_at_local": iso_local(started_at),
        "planned_end_at_utc": iso_utc(planned_end_at),
        "planned_end_at_local": iso_local(planned_end_at),
        "completed_iterations": completed_iterations,
        "success_count": success_count,
        "failure_count": failure_count,
        "last_record": last_record,
        "report_path": str(report_path) if report_path is not None else "",
    }


def write_pointer(
    *,
    pointer_path: Path,
    run_id: str,
    state: str,
    window_dir: Path,
    report_path: Path | None,
    status_path: Path,
) -> None:
    payload = {
        "run_id": run_id,
        "state": state,
        "window_dir": str(window_dir),
        "report_path": str(report_path) if report_path is not None else "",
        "status_path": str(status_path),
        "updated_at_utc": iso_utc(utc_now()),
    }
    write_json(pointer_path, payload)


def main() -> None:
    args = parse_args()
    random.seed()

    instrument_pool = normalize_instrument_pool(args.instruments)
    if not instrument_pool:
        raise SystemExit("A lista de instrumentos nao pode ficar vazia.")

    started_at = utc_now()
    planned_end_at = started_at + timedelta(minutes=max(args.duration_minutes, 0.1))
    run_id = args.label.strip() or f"case_study_window_{started_at.strftime('%Y%m%d_%H%M%S')}"

    base_dir = REPO_ROOT / "data" / "case_study_windows"
    window_dir = base_dir / run_id
    iterations_dir = window_dir / "iterations"
    ensure_dir(iterations_dir)

    history_file = window_dir / "history.jsonl"
    status_file = window_dir / "status.json"
    report_json_file = window_dir / "report.json"
    report_md_file = window_dir / "report.md"
    run_meta_file = window_dir / "run_meta.json"
    latest_pointer_file = REPO_ROOT / "data" / "case_study_window_latest.json"
    active_pointer_file = REPO_ROOT / "data" / "case_study_window_active.json"

    run_meta = {
        "run_id": run_id,
        "user_id": args.user_id,
        "started_at_utc": iso_utc(started_at),
        "started_at_local": iso_local(started_at),
        "planned_end_at_utc": iso_utc(planned_end_at),
        "planned_end_at_local": iso_local(planned_end_at),
        "duration_minutes": args.duration_minutes,
        "sleep_seconds": args.sleep_seconds,
        "horizon_bars": args.horizon_bars,
        "instrument_pool": instrument_pool,
        "min_instruments_per_run": args.min_instruments_per_run,
        "max_instruments_per_run": args.max_instruments_per_run,
        "max_iterations": args.max_iterations,
        "max_consecutive_failures": args.max_consecutive_failures,
    }
    write_json(run_meta_file, run_meta)

    history: list[dict[str, Any]] = []
    consecutive_failures = 0
    success_count = 0
    failure_count = 0
    report_payload: dict[str, Any] | None = None

    write_json(
        status_file,
        build_status(
            run_id=run_id,
            state="running",
            started_at=started_at,
            planned_end_at=planned_end_at,
            completed_iterations=0,
            success_count=0,
            failure_count=0,
            last_record=None,
            report_path=None,
        ),
    )
    write_pointer(
        pointer_path=active_pointer_file,
        run_id=run_id,
        state="running",
        window_dir=window_dir,
        report_path=None,
        status_path=status_file,
    )

    with SessionLocal() as db:
        record_audit_event(
            db,
            "thesis.case_study.window.started",
            {
                "run_id": run_id,
                "user_id": args.user_id,
                "duration_minutes": args.duration_minutes,
                "horizon_bars": args.horizon_bars,
            },
            args.user_id,
        )

    try:
        iteration = 0
        while utc_now() < planned_end_at:
            if args.max_iterations > 0 and iteration >= args.max_iterations:
                break

            iteration += 1
            requested_instruments = select_instruments(
                instrument_pool,
                min_count=args.min_instruments_per_run,
                max_count=args.max_instruments_per_run,
            )
            iteration_started_at = utc_now()

            try:
                with SessionLocal() as db:
                    payload = run_thesis_case_study(
                        db,
                        user_id=args.user_id,
                        instruments=requested_instruments,
                        horizon_bars=args.horizon_bars,
                    )
                    record_audit_event(
                        db,
                        "thesis.case_study.window.iteration",
                        {
                            "run_id": run_id,
                            "iteration": iteration,
                            "requested_instruments": requested_instruments,
                            "selected_thesis_id": payload["selected_case"]["thesis"]["thesis_id"],
                            "strategy_id": payload["selected_case"]["structured_operation"]["strategy_id"],
                            "confidence_tese_pct": payload["selected_case"]["kpis"]["confidence_tese_pct"],
                            "expected_financial_pct": payload["selected_case"]["kpis"]["expected_financial_pct"],
                            "realized_financial_pct": payload["selected_case"]["kpis"]["realized_financial_pct"],
                        },
                        args.user_id,
                    )

                iteration_finished_at = utc_now()
                payload_path = iterations_dir / f"iteration_{iteration:04d}.json"
                payload_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                record = summarize_case_payload(
                    iteration=iteration,
                    requested_instruments=requested_instruments,
                    payload=payload,
                    payload_path=payload_path,
                    started_at=iteration_started_at,
                    finished_at=iteration_finished_at,
                )
                history.append(record)
                append_jsonl(history_file, record)
                success_count += 1
                consecutive_failures = 0
            except Exception as exc:  # noqa: BLE001
                iteration_finished_at = utc_now()
                record = summarize_failure(
                    iteration=iteration,
                    requested_instruments=requested_instruments,
                    started_at=iteration_started_at,
                    finished_at=iteration_finished_at,
                    exc=exc,
                )
                history.append(record)
                append_jsonl(history_file, record)
                failure_count += 1
                consecutive_failures += 1

                with SessionLocal() as db:
                    record_audit_event(
                        db,
                        "thesis.case_study.window.iteration_failed",
                        {
                            "run_id": run_id,
                            "iteration": iteration,
                            "requested_instruments": requested_instruments,
                            "error_type": record["error_type"],
                            "error_message": record["error_message"],
                        },
                        args.user_id,
                    )

                if consecutive_failures >= args.max_consecutive_failures:
                    break

            write_json(
                status_file,
                build_status(
                    run_id=run_id,
                    state="running",
                    started_at=started_at,
                    planned_end_at=planned_end_at,
                    completed_iterations=len(history),
                    success_count=success_count,
                    failure_count=failure_count,
                    last_record=history[-1] if history else None,
                    report_path=None,
                ),
            )
            write_pointer(
                pointer_path=active_pointer_file,
                run_id=run_id,
                state="running",
                window_dir=window_dir,
                report_path=None,
                status_path=status_file,
            )

            remaining_seconds = (planned_end_at - utc_now()).total_seconds()
            if remaining_seconds <= 0:
                break
            sleep_seconds = min(max(args.sleep_seconds, 0.0), remaining_seconds)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        finished_at = utc_now()
        report_payload = build_report(
            run_id=run_id,
            started_at=started_at,
            planned_end_at=planned_end_at,
            finished_at=finished_at,
            history=history,
            window_dir=window_dir,
        )
        write_json(report_json_file, report_payload)
        report_md_file.write_text(report_to_markdown(report_payload), encoding="utf-8")

        write_json(
            status_file,
            build_status(
                run_id=run_id,
                state="completed",
                started_at=started_at,
                planned_end_at=planned_end_at,
                completed_iterations=len(history),
                success_count=success_count,
                failure_count=failure_count,
                last_record=history[-1] if history else None,
                report_path=report_json_file,
            ),
        )
        write_pointer(
            pointer_path=active_pointer_file,
            run_id=run_id,
            state="completed",
            window_dir=window_dir,
            report_path=report_json_file,
            status_path=status_file,
        )
        write_pointer(
            pointer_path=latest_pointer_file,
            run_id=run_id,
            state="completed",
            window_dir=window_dir,
            report_path=report_json_file,
            status_path=status_file,
        )

        with SessionLocal() as db:
            record_audit_event(
                db,
                "thesis.case_study.window.completed",
                {
                    "run_id": run_id,
                    "user_id": args.user_id,
                    "iterations": len(history),
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "avg_confidence_tese_pct": report_payload["kpis"]["avg_confidence_tese_pct"],
                    "avg_expected_financial_pct": report_payload["kpis"][
                        "avg_expected_financial_pct"
                    ],
                    "avg_realized_financial_pct": report_payload["kpis"][
                        "avg_realized_financial_pct"
                    ],
                },
                args.user_id,
            )

        print(f"run_id={run_id}")
        print(f"window_dir={window_dir}")
        print(f"report_json={report_json_file}")
        print(f"report_md={report_md_file}")
        print(
            "summary="
            f"iterations:{report_payload['kpis']['total_iterations']} | "
            f"success:{report_payload['kpis']['completed_case_studies']} | "
            f"failures:{report_payload['kpis']['failed_iterations']} | "
            f"avg_confidence:{report_payload['kpis']['avg_confidence_tese_pct']}"
        )
    except Exception as exc:  # noqa: BLE001
        failed_at = utc_now()
        failure_payload = {
            "run_id": run_id,
            "state": "failed",
            "failed_at_utc": iso_utc(failed_at),
            "failed_at_local": iso_local(failed_at),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
        }
        write_json(status_file, failure_payload)
        write_pointer(
            pointer_path=active_pointer_file,
            run_id=run_id,
            state="failed",
            window_dir=window_dir,
            report_path=report_json_file if report_json_file.exists() else None,
            status_path=status_file,
        )
        with SessionLocal() as db:
            record_audit_event(
                db,
                "thesis.case_study.window.failed",
                {
                    "run_id": run_id,
                    "user_id": args.user_id,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                args.user_id,
            )
        raise


if __name__ == "__main__":
    main()

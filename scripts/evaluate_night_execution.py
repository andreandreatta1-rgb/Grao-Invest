from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditEvent


DEFAULT_TIMEZONE = "America/Sao_Paulo"


@dataclass
class WindowEvent:
    event: AuditEvent
    details: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia execucao noturna da janela de case study e gera relatorio "
            "executivo (JSON/MD/CSV)."
        )
    )
    parser.add_argument("--user-id", type=int, default=1, help="ID do usuario.")
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Run ID especifico da janela. Vazio = usa a ultima janela concluida.",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default=DEFAULT_TIMEZONE,
        help="Timezone para apresentacao das datas.",
    )
    return parser.parse_args()


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_local_iso(dt: datetime | None, tz: ZoneInfo) -> str:
    if dt is None:
        return ""
    return dt.astimezone(tz).isoformat()


def _load_details(event: AuditEvent) -> dict[str, Any]:
    try:
        payload = json.loads(event.details) if event.details else {}
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_instrument(thesis_id: str) -> str:
    parts = thesis_id.split("-")
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return "n/d"


def _extract_direction(thesis_id: str) -> str:
    parts = thesis_id.split("-")
    if len(parts) >= 3 and parts[2]:
        return parts[2]
    return "n/d"


def _mean_or_zero(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def _resolve_timezone(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except Exception:
        # Fallback when tzdata is unavailable in runtime.
        return datetime.now().astimezone().tzinfo or timezone.utc


def main() -> None:
    args = parse_args()
    tz = _resolve_timezone(args.timezone)
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    run_id_arg = args.run_id.strip()

    with SessionLocal() as db:
        completed_stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.user_id == args.user_id,
                AuditEvent.event_type == "thesis.case_study.window.completed",
            )
            .order_by(AuditEvent.id.desc())
            .limit(200)
        )
        completed_events_raw = list(db.scalars(completed_stmt))
        completed_events = [WindowEvent(event=e, details=_load_details(e)) for e in completed_events_raw]

        if not completed_events:
            raise SystemExit("Nenhuma janela concluida encontrada para este usuario.")

        selected_completed: WindowEvent | None = None
        if run_id_arg:
            for item in completed_events:
                if str(item.details.get("run_id") or "") == run_id_arg:
                    selected_completed = item
                    break
            if selected_completed is None:
                raise SystemExit(f"Run ID nao encontrado: {run_id_arg}")
        else:
            selected_completed = completed_events[0]

        run_id = str(selected_completed.details.get("run_id") or "")
        if not run_id:
            raise SystemExit("Janela concluida sem run_id.")

        started_stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.user_id == args.user_id,
                AuditEvent.event_type == "thesis.case_study.window.started",
            )
            .order_by(AuditEvent.id.desc())
            .limit(200)
        )
        started_events = [WindowEvent(event=e, details=_load_details(e)) for e in db.scalars(started_stmt)]
        selected_started = next(
            (item for item in started_events if str(item.details.get("run_id") or "") == run_id),
            None,
        )

        iteration_stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.user_id == args.user_id,
                AuditEvent.event_type == "thesis.case_study.window.iteration",
            )
            .order_by(AuditEvent.id.asc())
        )
        iteration_events_raw = list(db.scalars(iteration_stmt))
        iteration_events = [WindowEvent(event=e, details=_load_details(e)) for e in iteration_events_raw]
        selected_iterations = [
            item for item in iteration_events if str(item.details.get("run_id") or "") == run_id
        ]

        if not selected_iterations:
            raise SystemExit(f"Nenhuma iteracao encontrada para run_id={run_id}")

        iteration_rows: list[dict[str, Any]] = []
        for item in selected_iterations:
            details = item.details
            thesis_id = str(details.get("selected_thesis_id") or "")
            expected = _safe_float(details.get("expected_financial_pct"))
            realized = _safe_float(details.get("realized_financial_pct"))
            confidence = _safe_float(details.get("confidence_tese_pct"))
            event_dt = _parse_iso(item.event.created_at)
            iteration_rows.append(
                {
                    "audit_id": item.event.id,
                    "created_at_utc": item.event.created_at,
                    "created_at_local": _as_local_iso(event_dt, tz),
                    "iteration": int(details.get("iteration") or 0),
                    "thesis_id": thesis_id,
                    "instrument": _extract_instrument(thesis_id),
                    "direction": _extract_direction(thesis_id),
                    "strategy_id": str(details.get("strategy_id") or "n/d"),
                    "confidence_tese_pct": confidence,
                    "expected_financial_pct": expected,
                    "realized_financial_pct": realized,
                    "requested_instruments": ",".join(
                        str(x) for x in (details.get("requested_instruments") or []) if isinstance(x, str)
                    ),
                }
            )

        iteration_rows.sort(key=lambda row: int(row["iteration"]))

        start_dt = _parse_iso(selected_started.event.created_at) if selected_started is not None else None
        end_dt = _parse_iso(selected_completed.event.created_at)
        if start_dt is None:
            start_dt = _parse_iso(iteration_rows[0]["created_at_utc"])
        if end_dt is None:
            end_dt = _parse_iso(iteration_rows[-1]["created_at_utc"])

        case_stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.user_id == args.user_id,
                AuditEvent.event_type == "thesis.case_study.generated",
            )
            .order_by(AuditEvent.id.asc())
        )
        case_events = list(db.scalars(case_stmt))
        case_in_window: list[WindowEvent] = []
        for event in case_events:
            event_dt = _parse_iso(event.created_at)
            if event_dt is None or start_dt is None or end_dt is None:
                continue
            if start_dt <= event_dt <= end_dt:
                case_in_window.append(WindowEvent(event=event, details=_load_details(event)))

        postmortem_stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.user_id == args.user_id,
                AuditEvent.event_type == "thesis.postmortem.generated",
            )
            .order_by(AuditEvent.id.asc())
        )
        postmortem_events = list(db.scalars(postmortem_stmt))
        postmortem_in_window = 0
        for event in postmortem_events:
            event_dt = _parse_iso(event.created_at)
            if event_dt is None or start_dt is None or end_dt is None:
                continue
            if start_dt <= event_dt <= end_dt:
                postmortem_in_window += 1

    expected_values = [row["expected_financial_pct"] for row in iteration_rows if isinstance(row["expected_financial_pct"], float)]
    realized_values = [row["realized_financial_pct"] for row in iteration_rows if isinstance(row["realized_financial_pct"], float)]
    confidence_values = [row["confidence_tese_pct"] for row in iteration_rows if isinstance(row["confidence_tese_pct"], float)]

    positive_count = sum(1 for value in realized_values if value >= 0.0)
    negative_count = sum(1 for value in realized_values if value < 0.0)
    unresolved_count = max(0, len(iteration_rows) - len(realized_values))
    financial_win_rate_pct = round((positive_count / len(realized_values)) * 100, 2) if realized_values else 0.0

    instrument_counter = Counter(str(row["instrument"]) for row in iteration_rows)
    strategy_counter = Counter(str(row["strategy_id"]) for row in iteration_rows)

    duration_minutes = 0.0
    if start_dt is not None and end_dt is not None:
        duration_minutes = round((end_dt - start_dt).total_seconds() / 60.0, 2)

    completed_details = selected_completed.details
    window_iterations = int(completed_details.get("iterations") or len(iteration_rows))
    window_success_count = int(completed_details.get("success_count") or 0)
    window_failure_count = int(completed_details.get("failure_count") or 0)

    b3_summary = _read_json(data_dir / "b3_daily_job_latest.json")
    dashboard_seed = _read_json(data_dir / "dashboard_seed.json")
    thesis_overview = dashboard_seed.get("thesis_history_overview")
    thesis_overview_dict = thesis_overview if isinstance(thesis_overview, dict) else {}

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timezone": args.timezone,
        "user_id": args.user_id,
        "run_id": run_id,
        "window": {
            "started_at_utc": start_dt.isoformat() if start_dt is not None else "",
            "ended_at_utc": end_dt.isoformat() if end_dt is not None else "",
            "started_at_local": _as_local_iso(start_dt, tz),
            "ended_at_local": _as_local_iso(end_dt, tz),
            "duration_minutes": duration_minutes,
        },
        "kpis": {
            "iterations_total": window_iterations,
            "iterations_logged": len(iteration_rows),
            "execution_success_count": window_success_count,
            "execution_failure_count": window_failure_count,
            "financial_positive_count": positive_count,
            "financial_negative_count": negative_count,
            "financial_unresolved_count": unresolved_count,
            "financial_win_rate_pct": financial_win_rate_pct,
            "avg_confidence_tese_pct": _mean_or_zero(confidence_values),
            "avg_expected_financial_pct": _mean_or_zero(expected_values),
            "avg_realized_financial_pct": _mean_or_zero(realized_values),
            "case_study_generated_count": len(case_in_window),
            "postmortem_generated_count": postmortem_in_window,
        },
        "distribution": {
            "top_instruments": instrument_counter.most_common(10),
            "top_strategies": strategy_counter.most_common(10),
        },
        "b3_daily_job_latest": {
            "run_at": b3_summary.get("pipeline", {}).get("run_at") if isinstance(b3_summary.get("pipeline"), dict) else "",
            "build_executed": b3_summary.get("build", {}).get("executed") if isinstance(b3_summary.get("build"), dict) else False,
            "load_executed": b3_summary.get("load", {}).get("executed") if isinstance(b3_summary.get("load"), dict) else False,
            "case_study_executed": b3_summary.get("case_study", {}).get("executed") if isinstance(b3_summary.get("case_study"), dict) else False,
            "inserted": b3_summary.get("load", {}).get("inserted") if isinstance(b3_summary.get("load"), dict) else 0,
            "duplicates_ignored": b3_summary.get("load", {}).get("duplicates_ignored") if isinstance(b3_summary.get("load"), dict) else 0,
            "parse_errors": b3_summary.get("load", {}).get("parse_errors") if isinstance(b3_summary.get("load"), dict) else 0,
        },
        "dashboard_seed_latest": {
            "total_tested": thesis_overview_dict.get("total_tested"),
            "success_count": thesis_overview_dict.get("success_count"),
            "success_rate_pct": thesis_overview_dict.get("success_rate_pct"),
            "expectancy_net_pct": thesis_overview_dict.get("expectancy_net_pct"),
            "window_start": thesis_overview_dict.get("window_start"),
            "window_end": thesis_overview_dict.get("window_end"),
        },
    }

    safe_run_id = _safe_filename(run_id)
    json_latest = data_dir / "night_execution_report_latest.json"
    json_run = data_dir / f"night_execution_report_{safe_run_id}.json"
    md_latest = data_dir / "night_execution_report_latest.md"
    md_run = data_dir / f"night_execution_report_{safe_run_id}.md"
    csv_latest = data_dir / "night_execution_iterations_latest.csv"
    csv_run = data_dir / f"night_execution_iterations_{safe_run_id}.csv"

    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    json_latest.write_text(json_text, encoding="utf-8")
    json_run.write_text(json_text, encoding="utf-8")

    md_lines = [
        "# Night Execution Report",
        "",
        f"- run_id: `{run_id}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- window_local: `{report['window']['started_at_local']}` -> `{report['window']['ended_at_local']}`",
        f"- duration_minutes: `{report['window']['duration_minutes']}`",
        "",
        "## KPIs",
        f"- iterations_total: `{report['kpis']['iterations_total']}`",
        f"- execution_success_count: `{report['kpis']['execution_success_count']}`",
        f"- execution_failure_count: `{report['kpis']['execution_failure_count']}`",
        f"- case_study_generated_count: `{report['kpis']['case_study_generated_count']}`",
        f"- postmortem_generated_count: `{report['kpis']['postmortem_generated_count']}`",
        f"- financial_win_rate_pct: `{report['kpis']['financial_win_rate_pct']}`",
        f"- avg_expected_financial_pct: `{report['kpis']['avg_expected_financial_pct']}`",
        f"- avg_realized_financial_pct: `{report['kpis']['avg_realized_financial_pct']}`",
        "",
        "## Top Instruments",
    ]
    for instrument, qty in report["distribution"]["top_instruments"]:
        md_lines.append(f"- {instrument}: {qty}")
    md_lines.extend(["", "## Top Strategies"])
    for strategy, qty in report["distribution"]["top_strategies"]:
        md_lines.append(f"- {strategy}: {qty}")
    md_lines.extend(
        [
            "",
            "## B3 Daily Job Latest",
            f"- build_executed: `{report['b3_daily_job_latest']['build_executed']}`",
            f"- load_executed: `{report['b3_daily_job_latest']['load_executed']}`",
            f"- case_study_executed: `{report['b3_daily_job_latest']['case_study_executed']}`",
            f"- inserted: `{report['b3_daily_job_latest']['inserted']}`",
            f"- duplicates_ignored: `{report['b3_daily_job_latest']['duplicates_ignored']}`",
            f"- parse_errors: `{report['b3_daily_job_latest']['parse_errors']}`",
        ]
    )
    md_text = "\n".join(md_lines)
    md_latest.write_text(md_text, encoding="utf-8")
    md_run.write_text(md_text, encoding="utf-8")

    csv_headers = [
        "audit_id",
        "created_at_utc",
        "created_at_local",
        "iteration",
        "thesis_id",
        "instrument",
        "direction",
        "strategy_id",
        "confidence_tese_pct",
        "expected_financial_pct",
        "realized_financial_pct",
        "requested_instruments",
    ]
    for output_path in (csv_latest, csv_run):
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(iteration_rows)

    print(f"JSON latest: {json_latest}")
    print(f"Markdown latest: {md_latest}")
    print(f"CSV latest: {csv_latest}")
    print(
        "Resumo: "
        f"iterations={report['kpis']['iterations_total']} | "
        f"financial_win_rate={report['kpis']['financial_win_rate_pct']}% | "
        f"avg_realized={report['kpis']['avg_realized_financial_pct']}% | "
        f"case_generated={report['kpis']['case_study_generated_count']}"
    )


if __name__ == "__main__":
    main()

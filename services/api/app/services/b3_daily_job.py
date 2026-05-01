from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SNAPSHOT_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})$")


def find_latest_snapshot_dir(*, data_b3_root: Path, prefix: str) -> Path | None:
    if not data_b3_root.exists():
        return None
    candidates: list[tuple[datetime, Path]] = []
    for item in data_b3_root.iterdir():
        if not item.is_dir():
            continue
        if not item.name.startswith(prefix):
            continue
        match = _SNAPSHOT_DATE_PATTERN.search(item.name)
        if match is None:
            continue
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        candidates.append((dt, item))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: (pair[0], pair[1].name), reverse=True)
    return candidates[0][1]


def build_b3_daily_job_markdown(payload: dict[str, Any]) -> str:
    pipeline = payload.get("pipeline", {})
    build = payload.get("build", {})
    load = payload.get("load", {})
    case_study = payload.get("case_study", {})
    dashboard_seed = payload.get("dashboard_seed", {})
    run_at = str(pipeline.get("run_at", ""))
    source_root = str(pipeline.get("source_root", ""))
    output_root = str(pipeline.get("output_root", ""))
    lines = [
        "# B3 Daily Job",
        "",
        "## Pipeline",
        f"- `run_at`: {run_at}",
        f"- `source_root`: {source_root}",
        f"- `output_root`: {output_root}",
        "",
        "## Build",
        f"- `executed`: {build.get('executed', False)}",
        f"- `cotahist_silver_rows`: {build.get('cotahist_silver_rows', 0)}",
        f"- `cambio_input_files`: {build.get('cambio_input_files', 0)}",
        f"- `renda_fixa_silver_rows`: {build.get('renda_fixa_silver_rows', 0)}",
        "",
        "## Load",
        f"- `executed`: {load.get('executed', False)}",
        f"- `provider`: {load.get('provider', '')}",
        f"- `inserted`: {load.get('inserted', 0)}",
        f"- `duplicates_ignored`: {load.get('duplicates_ignored', 0)}",
        f"- `parse_errors`: {load.get('parse_errors', 0)}",
        "",
        "## Case Study",
        f"- `executed`: {case_study.get('executed', False)}",
        f"- `thesis_id`: {case_study.get('thesis_id', '')}",
        f"- `instrument`: {case_study.get('instrument', '')}",
        f"- `confidence_pct`: {case_study.get('confidence_pct', 0)}",
        f"- `expected_pct`: {case_study.get('expected_pct', 0)}",
        f"- `realized_pct`: {case_study.get('realized_pct', 0)}",
        "",
        "## Dashboard Seed",
        f"- `executed`: {dashboard_seed.get('executed', False)}",
        f"- `user_id`: {dashboard_seed.get('user_id', '')}",
        f"- `total_tested`: {dashboard_seed.get('total_tested', 0)}",
        f"- `summary_file`: {dashboard_seed.get('summary_file', '')}",
    ]
    return "\n".join(lines)


def utc_iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()

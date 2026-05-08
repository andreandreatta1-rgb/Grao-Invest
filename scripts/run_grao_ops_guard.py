from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"

B3_INSTRUMENTS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "ABEV3",
    "WEGE3",
    "B3SA3",
    "RENT3",
    "SUZB3",
    "JBSS3",
    "PRIO3",
    "RADL3",
    "GGBR4",
    "VBBR3",
    "LREN3",
    "HAPV3",
    "BPAC11",
    "RAIL3",
    "CMIG4",
]
CRYPTO_INSTRUMENTS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica o ciclo operacional do Grao Invest: scheduler, feeds, "
            "gerador de teses, seed do dashboard e contrato opcional da API."
        )
    )
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--max-b3-age-days", type=float, default=4.0)
    parser.add_argument("--max-crypto-age-days", type=float, default=1.0)
    parser.add_argument("--skip-scheduler", action="store_true")
    parser.add_argument("--write-dashboard-seed", action="store_true")
    parser.add_argument(
        "--api-url",
        type=str,
        default="",
        help="URL opcional para comparar a API viva com o seed local.",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def parse_dt(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def age_days(raw: object, *, now: datetime) -> float | None:
    parsed = parse_dt(raw)
    if parsed is None:
        return None
    return round(max((now - parsed).total_seconds(), 0.0) / 86400.0, 3)


def stage(status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "message": message}
    payload.update(extra)
    return payload


def preflight_stage() -> dict[str, Any]:
    required = [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / "scripts" / "run_b3_daily_job.py",
        REPO_ROOT / "scripts" / "run_current_thesis_by_front_job.py",
        REPO_ROOT / "scripts" / "publish_dashboard_seed.py",
        DB_PATH,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return stage("fail", "Preflight encontrou arquivos obrigatorios ausentes.", missing=missing)
    return stage("ok", "Preflight operacional: scripts, venv e banco encontrados.")


def scheduler_stage(*, user_id: int, skip: bool) -> dict[str, Any]:
    if skip:
        return stage("skipped", "Verificacao do Task Scheduler ignorada.")
    if platform.system().lower() != "windows":
        return stage("skipped", "Task Scheduler indisponivel fora do Windows.")
    script = REPO_ROOT / "scripts" / "verify_grao_tasks.ps1"
    if not script.exists():
        return stage("fail", "Script verify_grao_tasks.ps1 ausente.", script=str(script))
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-RepoRoot",
            str(REPO_ROOT),
            "-UserId",
            str(user_id),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    raw = completed.stdout.strip()
    parsed: dict[str, Any] | None = None
    if raw:
        try:
            parsed_json = json.loads(raw)
            if isinstance(parsed_json, dict):
                parsed = parsed_json
        except json.JSONDecodeError:
            parsed = None
    if completed.returncode != 0:
        return stage(
            "fail",
            "Task Scheduler esta inconsistente; execute scripts/repair_grao_tasks.ps1.",
            returncode=completed.returncode,
            details=parsed,
            stderr=completed.stderr.strip(),
        )
    return stage(
        "ok",
        "Task Scheduler aponta para powershell.exe com paths protegidos.",
        details=parsed,
    )


def latest_ticks_for(instruments: list[str]) -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"count": 0, "latest_event_time": None, "latest_ingest_time": None, "providers": []}
    placeholders = ",".join("?" for _ in instruments)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT instrument, provider, COUNT(*) AS qty, MAX(event_time), MAX(ingest_time)
            FROM market_ticks
            WHERE instrument IN ({placeholders})
            GROUP BY instrument, provider
            """,
            instruments,
        ).fetchall()
    total = sum(int(row[2] or 0) for row in rows)
    latest_event = max((str(row[3]) for row in rows if row[3]), default=None)
    latest_ingest = max((str(row[4]) for row in rows if row[4]), default=None)
    providers: dict[str, int] = {}
    instruments_seen: set[str] = set()
    for instrument, provider, qty, *_ in rows:
        instruments_seen.add(str(instrument))
        providers[str(provider)] = providers.get(str(provider), 0) + int(qty or 0)
    return {
        "count": total,
        "instrument_count": len(instruments_seen),
        "requested_instrument_count": len(instruments),
        "latest_event_time": latest_event,
        "latest_ingest_time": latest_ingest,
        "providers": [
            {"provider": key, "count": value}
            for key, value in sorted(providers.items())
        ],
    }


def market_feed_stage(
    *,
    now: datetime,
    max_b3_age_days: float,
    max_crypto_age_days: float,
) -> dict[str, Any]:
    b3 = latest_ticks_for(B3_INSTRUMENTS)
    crypto = latest_ticks_for(CRYPTO_INSTRUMENTS)
    b3_age = age_days(b3.get("latest_event_time"), now=now)
    crypto_age = age_days(crypto.get("latest_event_time"), now=now)
    fronts: dict[str, Any] = {
        "b3": {**b3, "age_days": b3_age, "max_age_days": max_b3_age_days},
        "crypto": {**crypto, "age_days": crypto_age, "max_age_days": max_crypto_age_days},
    }

    stale: list[str] = []
    if b3_age is None or b3_age > max_b3_age_days:
        stale.append("b3")
    if crypto_age is None or crypto_age > max_crypto_age_days:
        stale.append("crypto")
    if stale:
        return stage(
            "blocked",
            "Feed de mercado stale; o gerador nao deve publicar teses atuais com dado velho.",
            stale_fronts=stale,
            fronts=fronts,
        )
    return stage("ok", "Feeds de mercado dentro da janela de frescor.", fronts=fronts)


def current_thesis_stage() -> dict[str, Any]:
    payload = load_json(DATA_DIR / "current_thesis_by_front_latest.json")
    if payload is None:
        return stage("fail", "Artefato current_thesis_by_front_latest.json ausente ou invalido.")
    quality = payload.get("data_quality") if isinstance(payload.get("data_quality"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    thesis_count = int(payload.get("thesis_count") or 0)
    status = str(quality.get("status") or "")
    if status == "no_fresh_market_data":
        return stage(
            "blocked",
            "Gerador rodou, mas bloqueou publicacao de teses atuais por falta de dados frescos.",
            generated_at=payload.get("generated_at"),
            thesis_count=thesis_count,
            data_quality=quality,
            front_errors=summary.get("front_errors", {}),
        )
    if thesis_count <= 0:
        return stage(
            "warning",
            "Gerador rodou sem teses no recorte; verificar se isso e esperado.",
            generated_at=payload.get("generated_at"),
            thesis_count=thesis_count,
            data_quality=quality,
        )
    return stage(
        "ok",
        "Gerador publicou teses atuais.",
        generated_at=payload.get("generated_at"),
        thesis_count=thesis_count,
        summary=summary,
    )


def dashboard_seed_stage(*, now: datetime) -> dict[str, Any]:
    seed = load_json(DATA_DIR / "dashboard_seed.json")
    if seed is None:
        return stage("fail", "dashboard_seed.json ausente ou invalido.")
    ops = seed.get("thesis_open_operations")
    operations = ops if isinstance(ops, list) else []
    by_front: dict[str, int] = {}
    for item in operations:
        if not isinstance(item, dict):
            continue
        front = str(item.get("front") or "sem_frente")
        by_front[front] = by_front.get(front, 0) + 1
    generated_at = seed.get("generated_at")
    return stage(
        "ok",
        "Dashboard seed legivel.",
        generated_at=generated_at,
        age_days=age_days(generated_at, now=now),
        thesis_open_operations=len(operations),
        operations_by_front=by_front,
    )


def b3_daily_stage(*, now: datetime) -> dict[str, Any]:
    payload = load_json(DATA_DIR / "b3_daily_job_latest.json")
    if payload is None:
        return stage("warning", "b3_daily_job_latest.json ausente ou invalido.")
    load = payload.get("load") if isinstance(payload.get("load"), dict) else {}
    build = payload.get("build") if isinstance(payload.get("build"), dict) else {}
    case = payload.get("case_study") if isinstance(payload.get("case_study"), dict) else {}
    run_at = (
        payload.get("pipeline", {}).get("run_at")
        if isinstance(payload.get("pipeline"), dict)
        else None
    )
    return stage(
        "ok",
        "Resumo do ultimo job B3 encontrado.",
        run_at=run_at,
        age_days=age_days(run_at, now=now),
        build_executed=bool(build.get("executed")),
        load_executed=bool(load.get("executed")),
        case_study_executed=bool(case.get("executed")),
        inserted=int(load.get("inserted") or 0),
        duplicates_ignored=int(load.get("duplicates_ignored") or 0),
        parse_errors=int(load.get("parse_errors") or 0),
    )


def api_stage(api_url: str) -> dict[str, Any]:
    if not api_url.strip():
        return stage("skipped", "Comparacao com API viva nao configurada.")
    try:
        from urllib.request import urlopen

        with urlopen(api_url, timeout=8) as response:  # noqa: S310 - local/operator URL.
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - operational diagnostics.
        return stage("warning", f"API viva indisponivel para comparacao: {exc}")
    if not isinstance(payload, dict):
        return stage("warning", "API viva retornou payload nao-objeto.")
    return stage(
        "ok",
        "API viva respondeu ao dashboard summary.",
        user_id=payload.get("user_id"),
        thesis_open_operations=len(payload.get("thesis_open_operations") or []),
        has_ops_health=isinstance(payload.get("ops_health"), dict),
    )


def overall_status(stages: dict[str, dict[str, Any]]) -> str:
    statuses = [str(item.get("status")) for item in stages.values()]
    if "fail" in statuses:
        return "fail"
    if "blocked" in statuses:
        return "blocked"
    if "warning" in statuses:
        return "warning"
    return "ok"


def recommended_actions(stages: dict[str, dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    if stages["scheduler"]["status"] == "fail":
        actions.append("Executar: powershell -File scripts/repair_grao_tasks.ps1")
    if stages["market_feed"]["status"] == "blocked":
        actions.append("Atualizar feed B3/Cripto antes de esperar novas teses atuais.")
    if stages["current_thesis_generator"]["status"] == "blocked":
        actions.append(
            "Nao forcar publicacao: o bloqueio protege contra tese atual com dado velho."
        )
    if stages["dashboard_seed"]["status"] == "fail":
        actions.append("Regenerar dashboard_seed.json via run_current_thesis_by_front_job.py.")
    return actions


def build_message(status_value: str, stages: dict[str, dict[str, Any]]) -> str:
    if status_value == "ok":
        return "Ciclo operacional saudavel. O laboratorio publicou dados atuais dentro do contrato."
    if status_value == "blocked":
        return (
            "O ciclo executou verificacoes, mas os numeros podem nao mudar porque o feed "
            "nao esta fresco ou o gerador bloqueou teses atuais."
        )
    if status_value == "fail":
        return "Ha falha operacional que impede confianca end-to-end no ciclo."
    return "Ciclo operacional com avisos; revisar detalhes antes de interpretar numeros parados."


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Grao Ops Health",
        "",
        f"- `generated_at`: {payload['generated_at']}",
        f"- `status`: {payload['status']}",
        f"- `message`: {payload['message']}",
        "",
        "## Stages",
    ]
    stages = payload.get("stages") if isinstance(payload.get("stages"), dict) else {}
    for name, details in stages.items():
        if not isinstance(details, dict):
            continue
        lines.extend(
            [
                "",
                f"### {name}",
                f"- `status`: {details.get('status')}",
                f"- `message`: {details.get('message')}",
            ]
        )
        for key in (
            "generated_at",
            "run_at",
            "age_days",
            "thesis_count",
            "thesis_open_operations",
            "inserted",
            "duplicates_ignored",
            "parse_errors",
        ):
            if key in details:
                lines.append(f"- `{key}`: {details.get(key)}")
    actions = payload.get("recommended_actions")
    if isinstance(actions, list) and actions:
        lines.extend(["", "## Recommended Actions"])
        lines.extend(f"- {item}" for item in actions)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dashboard_seed(payload: dict[str, Any]) -> None:
    path = DATA_DIR / "dashboard_seed.json"
    seed = load_json(path)
    if seed is None:
        return
    seed["ops_health"] = payload
    path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    now = utc_now()
    stages = {
        "preflight": preflight_stage(),
        "scheduler": scheduler_stage(user_id=args.user_id, skip=args.skip_scheduler),
        "b3_daily_job": b3_daily_stage(now=now),
        "market_feed": market_feed_stage(
            now=now,
            max_b3_age_days=args.max_b3_age_days,
            max_crypto_age_days=args.max_crypto_age_days,
        ),
        "current_thesis_generator": current_thesis_stage(),
        "dashboard_seed": dashboard_seed_stage(now=now),
        "api": api_stage(args.api_url),
    }
    status_value = overall_status(stages)
    payload = {
        "generated_at": now.isoformat(),
        "user_id": args.user_id,
        "status": status_value,
        "message": build_message(status_value, stages),
        "stages": stages,
        "recommended_actions": recommended_actions(stages),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "ops_health_latest.json"
    md_path = DATA_DIR / "ops_health_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(payload, md_path)
    if args.write_dashboard_seed:
        write_dashboard_seed(payload)

    print(f"Arquivo gerado: {json_path}")
    print(f"Arquivo gerado: {md_path}")
    print(f"Ops health: status={status_value} | message={payload['message']}")
    if status_value == "fail":
        raise SystemExit(1)
    if status_value == "blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

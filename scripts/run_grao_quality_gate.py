from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTEND_DIST = REPO_ROOT / "services" / "api" / "frontend_dist"


class QualityGateFailure(RuntimeError):
    """Raised when a quality gate check finds a user-visible regression."""


def _read_text(path: Path) -> str:
    if not path.exists():
        raise QualityGateFailure(f"Arquivo esperado nao existe: {path}")
    return path.read_text(encoding="utf-8")


def _to_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        clean = value.strip().replace(".", "")
        if clean.isdigit():
            return int(clean)
    return None


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _frontend_entry_asset(frontend_dist: Path) -> Path:
    html = _read_text(frontend_dist / "index.html")
    match = re.search(r'src=["\']/(?P<asset>assets/index-[^"\']+\.js)["\']', html)
    if match is None:
        raise QualityGateFailure("index.html nao aponta para um bundle JS assets/index-*.js")
    asset = frontend_dist / match.group("asset")
    if not asset.exists():
        raise QualityGateFailure(f"Bundle apontado no index.html nao existe: {asset}")
    return asset


def inspect_frontend_bundle(frontend_dist: Path | str = DEFAULT_FRONTEND_DIST) -> dict[str, Any]:
    dist = Path(frontend_dist)
    entry_asset = _frontend_entry_asset(dist)
    bundle = _read_text(entry_asset)
    violations: list[str] = []

    forbidden_initial_patterns = [
        "()=>Hn(_n(xn))",
        "=>Hn(_n(xn))",
        "useState)(()=>Hn(_n(xn)))",
    ]
    if any(pattern in bundle for pattern in forbidden_initial_patterns):
        violations.append(
            "A tela inicializa com mock dashboard antes da API oficial responder."
        )

    if "a(Hn(_n(xn),`fallback`))" in bundle or "a(Hn(_n(xn),\"fallback\"))" in bundle:
        violations.append("Fallback de erro ainda injeta mock dashboard.")

    unsafe_dashboard_fallback = (
        "function Yz(e){return Wz.reduce((t,n)=>(t[n]=e?.[n]??xn[n],t),{})}"
    )
    if unsafe_dashboard_fallback in bundle:
        violations.append(
            "Fallback parcial ainda usa dashboardSummary mock quando a API falha."
        )

    if "total_tested:1727" in bundle or '"total_tested":1727' in bundle:
        violations.append("Literal legado total_tested=1727 encontrado no bundle.")

    if violations:
        raise QualityGateFailure("mock dashboard inseguro: " + " ".join(violations))

    initial_source = "empty" if "()=>Hn(_n({}))" in bundle else "unknown"
    return {
        "entry_asset": entry_asset.relative_to(dist).as_posix(),
        "initial_dashboard_source": initial_source,
        "legacy_1727_literal_present": False,
    }


def inspect_dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    overview = _dict(payload.get("thesis_history_overview"))
    historical = _dict(payload.get("historical_analysis_summary"))
    ops_health = _dict(payload.get("ops_health"))
    operations = _list(payload.get("thesis_open_operations"))

    total_tested = _to_int(overview.get("total_tested"))
    historical_count = _to_int(historical.get("thesis_count"))

    if total_tested is None or total_tested <= 0:
        raise QualityGateFailure("thesis_history_overview.total_tested ausente ou zerado")

    if historical_count is not None and historical_count > 0 and historical_count != total_tested:
        raise QualityGateFailure(
            "Contagens inconsistentes: "
            f"thesis_history_overview.total_tested={total_tested} "
            f"historical_analysis_summary.thesis_count={historical_count}"
        )

    health_status = str(ops_health.get("status") or "").strip().lower()
    if health_status and health_status != "ok":
        raise QualityGateFailure(f"ops_health.status nao esta ok: {health_status}")

    real_estate_ops = [
        row
        for row in operations
        if isinstance(row, dict) and str(row.get("front") or "").strip().lower() == "imoveis"
    ]
    missing_analysis = [
        row.get("thesis_id") or row.get("action") or index
        for index, row in enumerate(real_estate_ops)
        if not isinstance(row.get("real_estate_analysis"), dict)
    ]
    if missing_analysis:
        raise QualityGateFailure(
            "Teses de imoveis sem real_estate_analysis: "
            + ", ".join(str(item) for item in missing_analysis)
        )

    return {
        "total_tested": total_tested,
        "historical_thesis_count": historical_count,
        "open_operations": len(operations),
        "real_estate_operations": len(real_estate_ops),
        "ops_health": health_status or "missing",
    }


def _fetch_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "grao-quality-gate/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise QualityGateFailure(f"Falha ao buscar {url}: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise QualityGateFailure(f"Resposta nao-JSON em {url}") from exc
    if not isinstance(payload, dict):
        raise QualityGateFailure(f"Resposta JSON em {url} nao e objeto")
    return payload


def inspect_dashboard_url(
    url: str,
    *,
    attempts: int = 3,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    if attempts <= 0:
        raise QualityGateFailure("attempts precisa ser maior que zero")

    readings: list[dict[str, Any]] = []
    for index in range(attempts):
        payload = _fetch_json(url, timeout_seconds)
        readings.append(inspect_dashboard_payload(payload))
        if index < attempts - 1:
            time.sleep(0.5)

    totals = {reading["total_tested"] for reading in readings}
    if len(totals) != 1:
        raise QualityGateFailure(
            "total_tested oscilou entre chamadas: "
            + ", ".join(str(item) for item in sorted(totals))
        )

    return {
        "url": url,
        "attempts": attempts,
        "readings": readings,
        "stable_total_tested": totals.pop(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gate de qualidade do Grao Invest antes de publicar ou validar UI.",
    )
    parser.add_argument("--frontend-dist", type=Path, default=DEFAULT_FRONTEND_DIST)
    parser.add_argument("--dashboard-url", default="")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--json", action="store_true", help="Imprime relatorio em JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report: dict[str, Any] = {"status": "ok"}

    try:
        report["frontend"] = inspect_frontend_bundle(args.frontend_dist)
        if args.dashboard_url:
            report["dashboard"] = inspect_dashboard_url(
                args.dashboard_url,
                attempts=args.attempts,
                timeout_seconds=args.timeout_seconds,
            )
    except QualityGateFailure as exc:
        report["status"] = "fail"
        report["error"] = str(exc)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"QUALITY GATE FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("QUALITY GATE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

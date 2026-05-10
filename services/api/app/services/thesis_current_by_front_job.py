from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.db import DATA_DIR
from app.services.crypto_universe import default_crypto_instruments
from app.services.thesis_current_monitor import (
    load_latest_current_thesis_monitor,
    persist_current_thesis_monitor_snapshot,
    run_current_thesis_monitor,
)
from app.services.utils import DISCLAIMER
from sqlalchemy.orm import Session

DEFAULT_B3_INSTRUMENTS = [
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

DEFAULT_CRYPTO_INSTRUMENTS = default_crypto_instruments(limit=10)
_NO_FRESH_MARKET_DATA_TOKEN = "nao ha dados de mercado frescos"
_STALE_FRONT_REUSED_NOTE = "Dados de mercado sem frescor; mantendo ultimo monitor valido desta frente."


@dataclass(frozen=True)
class FrontConfig:
    front_id: str
    label: str
    instruments: list[str]


@dataclass(frozen=True)
class FrontRunResult:
    front_id: str
    label: str
    instruments: list[str]
    payload: dict[str, object] | None
    error: str = ""


def utc_iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def default_front_configs() -> list[FrontConfig]:
    return [
        FrontConfig(
            front_id="acoes_b3",
            label="Acoes B3",
            instruments=list(DEFAULT_B3_INSTRUMENTS),
        ),
        FrontConfig(
            front_id="cripto",
            label="Cripto",
            instruments=list(DEFAULT_CRYPTO_INSTRUMENTS),
        ),
    ]


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _summary_dict(payload: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else {}


def _data_quality_dict(payload: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    quality = payload.get("data_quality")
    return quality if isinstance(quality, dict) else {}


def _scan_scope_dict(payload: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    scope = payload.get("scan_scope")
    return scope if isinstance(scope, dict) else {}


def _thesis_list(payload: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    theses = payload.get("theses")
    if not isinstance(theses, list):
        return []
    return [item for item in theses if isinstance(item, dict)]


def _candidate_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _scan_fronts(payload: dict[str, object] | None) -> dict[str, dict[str, object]]:
    scope = _scan_scope_dict(payload)
    fronts = scope.get("fronts")
    if not isinstance(fronts, dict):
        return {}
    return {
        str(front_id): front_info
        for front_id, front_info in fronts.items()
        if isinstance(front_info, dict)
    }


def _summary_from_theses(theses: list[dict[str, object]]) -> dict[str, object]:
    target_hits = sum(
        1 for item in theses if str(item.get("monitor_status") or "").lower() == "target_hit"
    )
    stop_alerts = sum(
        1 for item in theses if str(item.get("monitor_status") or "").lower() == "stop_alert"
    )
    monitoring_count = sum(
        1 for item in theses if str(item.get("monitor_status") or "").lower() == "monitoring"
    )
    executive_status_counts: dict[str, int] = {}
    for item in theses:
        status = str(item.get("executive_status") or "").lower()
        if not status:
            revaluation = item.get("operation_revaluation")
            revaluation_dict = revaluation if isinstance(revaluation, dict) else {}
            status = str(revaluation_dict.get("executive_status") or "").lower()
        if status:
            executive_status_counts[status] = executive_status_counts.get(status, 0) + 1

    avg_unrealized = (
        round(
            sum(_safe_float(item.get("unrealized_financial_pct")) for item in theses)
            / len(theses),
            4,
        )
        if theses
        else 0.0
    )
    needs_attention_count = (
        executive_status_counts.get("atencao", 0)
        + executive_status_counts.get("invalidada", 0)
        + executive_status_counts.get("revisar_saida", 0)
    )
    return {
        "target_hits": target_hits,
        "stop_alerts": stop_alerts,
        "monitoring_count": monitoring_count,
        "avg_unrealized_financial_pct": avg_unrealized,
        "executive_status_counts": executive_status_counts,
        "needs_attention_count": needs_attention_count,
    }


def _data_quality_summary(
    *,
    generated_at: str,
    thesis_count: int,
    front_errors: dict[str, str],
    reused_fronts: list[str],
) -> dict[str, object]:
    if thesis_count == 0 and front_errors:
        return {
            "status": "no_fresh_market_data",
            "reason": "no_fresh_market_data",
            "generated_at": generated_at,
            "message": "Nenhuma frente tem dados frescos para publicar teses atuais.",
        }
    if reused_fronts:
        return {
            "status": "partial",
            "reason": "stale_front_reused",
            "generated_at": generated_at,
            "message": "Uma ou mais frentes foram preservadas do ultimo snapshot valido.",
            "reused_fronts": reused_fronts,
        }
    if front_errors:
        return {
            "status": "partial",
            "reason": "front_errors",
            "generated_at": generated_at,
            "message": "Algumas frentes ficaram fora por falta de dados frescos.",
        }
    return {
        "status": "fresh",
        "reason": "",
        "generated_at": generated_at,
        "message": "Monitor atual gerado com dados frescos.",
    }


def trim_payload_theses_for_front(
    payload: dict[str, object],
    *,
    max_theses: int,
) -> dict[str, object]:
    theses = _thesis_list(payload)
    scope = dict(_scan_scope_dict(payload))
    if max_theses <= 0:
        selected: list[dict[str, object]] = []
        selected_ids: set[int] = set()
    else:
        selected = []
        seen_instruments: set[str] = set()
        selected_ids: set[int] = set()
        for item in theses:
            instrument = str(item.get("instrument") or "").upper()
            if instrument and instrument in seen_instruments:
                continue
            selected.append(item)
            selected_ids.add(id(item))
            if instrument:
                seen_instruments.add(instrument)
            if len(selected) >= max_theses:
                break

        if len(selected) < max_theses:
            for item in theses:
                if id(item) in selected_ids:
                    continue
                selected.append(item)
                if len(selected) >= max_theses:
                    break

    trimmed = dict(payload)
    trimmed["theses"] = selected
    trimmed["thesis_count"] = len(selected)
    trimmed["summary"] = _summary_from_theses(selected)
    overflow_candidates = [item for item in theses if id(item) not in selected_ids]
    existing_scanner = _candidate_list(scope.get("scanner_candidates"))
    combined_scanner: list[dict[str, object]] = []
    seen_scanner_ids: set[str] = set()
    for item in [*overflow_candidates, *existing_scanner]:
        thesis_id = str(item.get("thesis_id") or "")
        signature = thesis_id or f"{item.get('instrument')}:{item.get('latest_event_time')}"
        if signature in seen_scanner_ids:
            continue
        seen_scanner_ids.add(signature)
        combined_scanner.append(item)
    scope["scanner_candidates"] = combined_scanner
    scope["scanner_candidate_count"] = len(combined_scanner)
    trimmed["scan_scope"] = scope
    return trimmed


def _is_no_fresh_market_data_error(message: str) -> bool:
    return _NO_FRESH_MARKET_DATA_TOKEN in message.strip().lower()


def _infer_front_id(item: dict[str, object]) -> str:
    front_id = str(item.get("asset_front") or "").strip().lower()
    if front_id in {"acoes_b3", "cripto", "imoveis"}:
        return front_id
    instrument = str(item.get("instrument") or "").strip().upper()
    if instrument.endswith("USDT"):
        return "cripto"
    return "acoes_b3"


def _build_reused_front_payload(
    previous_payload: dict[str, object] | None,
    *,
    front: FrontConfig,
    generated_at: str,
) -> dict[str, object] | None:
    if not isinstance(previous_payload, dict):
        return None

    previous_front_scope = _scan_fronts(previous_payload).get(front.front_id, {})
    previous_theses = [
        dict(item)
        for item in _thesis_list(previous_payload)
        if _infer_front_id(item) == front.front_id
    ]
    if not previous_theses:
        return None

    scanner_candidates = _candidate_list(previous_front_scope.get("scanner_candidates"))
    if not scanner_candidates:
        top_level_scanner = _candidate_list(_scan_scope_dict(previous_payload).get("scanner_candidates"))
        scanner_candidates = [
            dict(item)
            for item in top_level_scanner
            if _infer_front_id(item) == front.front_id
        ]

    summary = _summary_from_theses(previous_theses)
    summary["notes"] = [_STALE_FRONT_REUSED_NOTE]
    return {
        "generated_at": generated_at,
        "user_id": _safe_int(previous_payload.get("user_id")) or 0,
        "horizon_bars": _safe_int(previous_payload.get("horizon_bars")) or 8,
        "recent_bars_window": _safe_int(previous_payload.get("recent_bars_window")) or 7,
        "thesis_count": len(previous_theses),
        "scan_scope": {
            "instruments": previous_front_scope.get("instruments") or front.instruments,
            "tick_count": _safe_int(previous_front_scope.get("tick_count")),
            "candidate_count": _safe_int(previous_front_scope.get("candidate_count")),
            "policy_candidate_count": _safe_int(previous_front_scope.get("policy_candidate_count")),
            "current_candidate_count": _safe_int(previous_front_scope.get("current_candidate_count")),
            "scanner_candidate_count": len(scanner_candidates),
            "scanner_candidates": scanner_candidates,
        },
        "summary": summary,
        "data_quality": {
            "status": "stale_reused",
            "reason": "no_fresh_market_data",
            "generated_at": generated_at,
            "source_generated_at": previous_payload.get("generated_at"),
            "message": f"{front.label} sem tick fresco; mantendo ultimo monitor valido.",
            "reused": True,
        },
        "theses": previous_theses,
        "disclaimer": previous_payload.get("disclaimer", DISCLAIMER),
    }


def merge_front_monitor_payloads(
    *,
    user_id: int,
    horizon_bars: int,
    recent_bars_window: int,
    generated_at: str,
    front_results: list[FrontRunResult],
) -> dict[str, object]:
    merged_theses: list[dict[str, object]] = []
    scanner_candidates: list[dict[str, object]] = []
    front_scope: dict[str, dict[str, object]] = {}
    front_errors: dict[str, str] = {}
    reused_fronts: list[str] = []
    instruments: list[str] = []
    tick_count = 0
    candidate_count = 0
    policy_candidate_count = 0
    current_candidate_count = 0
    executive_status_counts: dict[str, int] = {}

    for result in front_results:
        instruments.extend(result.instruments)
        payload = result.payload
        scope = _scan_scope_dict(payload)
        summary = _summary_dict(payload)
        data_quality = _data_quality_dict(payload)
        theses = _thesis_list(payload)
        front_scanner_candidates = _candidate_list(scope.get("scanner_candidates"))

        if result.error:
            front_errors[result.front_id] = result.error
        if str(data_quality.get("status") or "").lower() == "stale_reused":
            reused_fronts.append(result.front_id)

        front_scope[result.front_id] = {
            "label": result.label,
            "instruments": result.instruments,
            "thesis_count": len(theses),
            "tick_count": _safe_int(scope.get("tick_count")),
            "candidate_count": _safe_int(scope.get("candidate_count")),
            "policy_candidate_count": _safe_int(scope.get("policy_candidate_count")),
            "current_candidate_count": _safe_int(scope.get("current_candidate_count")),
            "scanner_candidate_count": len(front_scanner_candidates),
            "scanner_candidates": front_scanner_candidates,
            "data_quality": data_quality,
            "error": result.error,
        }

        tick_count += _safe_int(scope.get("tick_count"))
        candidate_count += _safe_int(scope.get("candidate_count"))
        policy_candidate_count += _safe_int(scope.get("policy_candidate_count"))
        current_candidate_count += _safe_int(scope.get("current_candidate_count"))

        status_counts = summary.get("executive_status_counts")
        if isinstance(status_counts, dict):
            for key, value in status_counts.items():
                status = str(key)
                current_count = executive_status_counts.get(status, 0)
                executive_status_counts[status] = current_count + _safe_int(value)

        for item in theses:
            enriched = dict(item)
            enriched["asset_front"] = result.front_id
            enriched["front_label"] = result.label
            merged_theses.append(enriched)
        for item in front_scanner_candidates:
            enriched = dict(item)
            enriched["asset_front"] = result.front_id
            enriched["front_label"] = result.label
            scanner_candidates.append(enriched)

    target_hits = sum(
        1 for item in merged_theses if str(item.get("monitor_status") or "").lower() == "target_hit"
    )
    stop_alerts = sum(
        1 for item in merged_theses if str(item.get("monitor_status") or "").lower() == "stop_alert"
    )
    monitoring_count = sum(
        1 for item in merged_theses if str(item.get("monitor_status") or "").lower() == "monitoring"
    )
    avg_unrealized = (
        round(
            sum(_safe_float(item.get("unrealized_financial_pct")) for item in merged_theses)
            / len(merged_theses),
            4,
        )
        if merged_theses
        else 0.0
    )
    needs_attention_count = (
        executive_status_counts.get("atencao", 0)
        + executive_status_counts.get("invalidada", 0)
        + executive_status_counts.get("revisar_saida", 0)
    )

    return {
        "generated_at": generated_at,
        "user_id": user_id,
        "horizon_bars": horizon_bars,
        "recent_bars_window": recent_bars_window,
        "thesis_count": len(merged_theses),
        "scan_scope": {
            "fronts": front_scope,
            "instruments": instruments,
            "tick_count": tick_count,
            "candidate_count": candidate_count,
            "policy_candidate_count": policy_candidate_count,
            "current_candidate_count": current_candidate_count,
            "scanner_candidate_count": len(scanner_candidates),
            "scanner_candidates": scanner_candidates,
        },
        "summary": {
            "target_hits": target_hits,
            "stop_alerts": stop_alerts,
            "monitoring_count": monitoring_count,
            "avg_unrealized_financial_pct": avg_unrealized,
            "executive_status_counts": executive_status_counts,
            "needs_attention_count": needs_attention_count,
            "front_errors": front_errors,
        },
        "data_quality": _data_quality_summary(
            generated_at=generated_at,
            thesis_count=len(merged_theses),
            front_errors=front_errors,
            reused_fronts=reused_fronts,
        ),
        "theses": merged_theses,
        "disclaimer": DISCLAIMER,
    }


def build_current_by_front_job_markdown(payload: dict[str, object]) -> str:
    scan_scope = payload.get("scan_scope")
    scope = scan_scope if isinstance(scan_scope, dict) else {}
    fronts_raw = scope.get("fronts")
    fronts = fronts_raw if isinstance(fronts_raw, dict) else {}
    summary_raw = payload.get("summary")
    summary = summary_raw if isinstance(summary_raw, dict) else {}
    theses = _thesis_list(payload)

    lines = [
        "# Current Thesis By Front Job",
        "",
        f"- `generated_at`: {payload.get('generated_at', '-')}",
        f"- `user_id`: {payload.get('user_id', '-')}",
        f"- `thesis_count`: {payload.get('thesis_count', 0)}",
        f"- `target_hits`: {summary.get('target_hits', 0)}",
        f"- `stop_alerts`: {summary.get('stop_alerts', 0)}",
        f"- `monitoring_count`: {summary.get('monitoring_count', 0)}",
        f"- `avg_unrealized_financial_pct`: {summary.get('avg_unrealized_financial_pct', 0)}",
        "",
        "## Frentes",
    ]

    if fronts:
        for front_id, front_info_raw in fronts.items():
            front_info = front_info_raw if isinstance(front_info_raw, dict) else {}
            lines.extend(
                [
                    "",
                    f"### {front_info.get('label', front_id)}",
                    f"- `front_id`: {front_id}",
                    f"- `thesis_count`: {front_info.get('thesis_count', 0)}",
                    f"- `candidate_count`: {front_info.get('candidate_count', 0)}",
                    f"- `current_candidate_count`: {front_info.get('current_candidate_count', 0)}",
                    f"- `error`: {front_info.get('error', '') or '-'}",
                ]
            )
    else:
        lines.append("- Nenhuma frente processada.")

    lines.extend(["", "## Teses"])
    if not theses:
        lines.append("- Sem teses atuais no recorte.")
    else:
        for item in theses:
            lines.extend(
                [
                    "",
                    f"- `front`: {item.get('front_label', item.get('asset_front', '-'))}",
                    f"- `thesis_id`: {item.get('thesis_id', '-')}",
                    f"- `instrument`: {item.get('instrument', '-')}",
                    f"- `monitor_status`: {item.get('monitor_status', '-')}",
                    (
                        f"- `unrealized_financial_pct`: "
                        f"{item.get('unrealized_financial_pct', '-')}"
                    ),
                ]
            )
    return "\n".join(lines)


def run_current_thesis_by_front_job(
    db: Session,
    *,
    user_id: int,
    fronts: list[FrontConfig] | None = None,
    horizon_bars: int = 8,
    thesis_count_per_front: int = 8,
    recent_bars_window: int = 30,
    max_latest_age_days: int = 0,
    oversample_factor: int = 5,
    generated_at: str | None = None,
) -> dict[str, object]:
    selected_fronts = fronts or default_front_configs()
    results: list[FrontRunResult] = []
    generated_at_value = generated_at or utc_iso_now()
    previous_payload = (
        load_latest_current_thesis_monitor(
            db,
            user_id=user_id,
            include_bundled_bootstrap=False,
        )
        if hasattr(db, "scalars")
        else None
    )
    internal_thesis_count = max(
        thesis_count_per_front,
        thesis_count_per_front * max(1, oversample_factor),
    )

    for front in selected_fronts:
        try:
            payload = run_current_thesis_monitor(
                db,
                user_id=user_id,
                instruments=front.instruments,
                horizon_bars=horizon_bars,
                thesis_count=internal_thesis_count,
                recent_bars_window=recent_bars_window,
                distinct_instruments=True,
                prefer_recent=True,
                max_latest_age_days=max_latest_age_days,
            )
            trimmed_payload = trim_payload_theses_for_front(
                dict(payload),
                max_theses=thesis_count_per_front,
            )
            results.append(
                FrontRunResult(
                    front_id=front.front_id,
                    label=front.label,
                    instruments=front.instruments,
                    payload=trimmed_payload,
                    error="",
                )
            )
        except ValueError as exc:
            reused_payload = None
            if _is_no_fresh_market_data_error(str(exc)):
                reused_payload = _build_reused_front_payload(
                    previous_payload,
                    front=front,
                    generated_at=generated_at_value,
                )
            if reused_payload is not None:
                results.append(
                    FrontRunResult(
                        front_id=front.front_id,
                        label=front.label,
                        instruments=front.instruments,
                        payload=reused_payload,
                        error="",
                    )
                )
                continue
            results.append(
                FrontRunResult(
                    front_id=front.front_id,
                    label=front.label,
                    instruments=front.instruments,
                    payload=None,
                    error=str(exc),
                )
            )

    merged = merge_front_monitor_payloads(
        user_id=user_id,
        horizon_bars=horizon_bars,
        recent_bars_window=recent_bars_window,
        generated_at=generated_at_value,
        front_results=results,
    )
    persist_current_thesis_monitor_snapshot(db, merged, user_id=user_id)
    return merged


def write_current_by_front_outputs(payload: dict[str, object]) -> dict[str, str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "current_thesis_by_front_latest.json"
    md_path = DATA_DIR / "current_thesis_by_front_latest.md"
    latest_md_path = DATA_DIR / "current_thesis_monitor_latest.md"

    import json

    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    markdown = build_current_by_front_job_markdown(payload)
    md_path.write_text(markdown, encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")
    return {
        "json_file": str(json_path),
        "markdown_file": str(md_path),
        "latest_markdown_file": str(latest_md_path),
    }

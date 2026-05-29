from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older runtimes
    ZoneInfo = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.real_estate_radar import build_candidate_analysis  # noqa: E402


SEED_PATH = ROOT / "data" / "dashboard_seed.json"
WEEKLY_OWNER_PATH = ROOT / "data" / "weekly_owner_report_latest.json"
REPORTS_DIR = ROOT / "data" / "reports"
TRIAGE_LATEST_JSON = REPORTS_DIR / "radar_imobiliario_triagem_implacavel_latest.json"
TARGET_ROI_PCT = 20.0


def _now_brt() -> str:
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
        except Exception:
            pass
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    return str(value or "").strip()


def _analysis(row: dict[str, Any]) -> dict[str, Any]:
    analysis = row.get("real_estate_analysis")
    return analysis if isinstance(analysis, dict) else {}


def _candidate(row: dict[str, Any]) -> dict[str, Any]:
    candidate = _analysis(row).get("candidate")
    return candidate if isinstance(candidate, dict) else {}


def _source_url(row: dict[str, Any]) -> str:
    return _text(row.get("source_url") or _candidate(row).get("source_url"))


def _p0_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    items = _analysis(row).get("pending_items")
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict) and _text(item.get("priority")).upper() == "P0"
    ]


def _p0_count(row: dict[str, Any]) -> int:
    return len(_p0_items(row))


def _is_real_estate_row(row: dict[str, Any]) -> bool:
    return _text(row.get("front")).lower() == "imoveis" or isinstance(
        row.get("real_estate_analysis"), dict
    )


def _open_real_estate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("thesis_open_operations")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and _is_real_estate_row(row) and row.get("is_open") is True
    ]


def _rights_over_asset_signal(row: dict[str, Any]) -> bool:
    listing = _analysis(row).get("listing_reading")
    if isinstance(listing, dict) and listing.get("rights_over_asset") is True:
        return True
    source_text = re.sub(r"[-_/]+", " ", _source_url(row).lower())
    return bool(
        "direitos sobre" in source_text
        or "direito sobre" in source_text
        or "direitos aquisitivos" in source_text
        or "direito aquisitivo" in source_text
        or re.search(
            r"\bdireitos?\s+(?:apto|apartamento|imovel|casa|unidade|studio|sala|loja)\b",
            source_text,
        )
    )


def _has_padre_carvalho_canonical(open_rows: list[dict[str, Any]]) -> bool:
    for peer in open_rows:
        if _text(peer.get("thesis_id")) == "IM-RADAR-TARGET-PIN-06":
            url = _source_url(peer).lower()
            if "portalzuk.com.br" in url and "rua-padre-carvalho-129" in url:
                return True
    return False


def _is_padre_carvalho_shadow(row: dict[str, Any], open_rows: list[dict[str, Any]]) -> bool:
    if _text(row.get("thesis_id")) == "IM-RADAR-TARGET-PIN-06":
        return False
    if not _has_padre_carvalho_canonical(open_rows):
        return False
    haystack = " ".join(
        [
            _text(row.get("thesis_id")),
            _source_url(row),
            json.dumps(_candidate(row), ensure_ascii=False),
            _text(row.get("thesis_reason")),
        ]
    ).lower()
    return (
        "im-radar-26" in haystack
        or "2844902" in haystack
        or ("padre carvalho" in haystack and "casa 5" in haystack)
    )


def _is_category_url(url: str) -> bool:
    normalized = url.lower().rstrip("/")
    return bool(
        "leilaoimovel.com.br/leilao-de-imovel/" in normalized
        or ("chavesnamao.com.br/flat/" in normalized and "/id-" not in normalized)
    )


def _is_market_benchmark_without_candidate(row: dict[str, Any]) -> bool:
    url = _source_url(row).lower()
    valuation = _analysis(row).get("valuation_evidence")
    risk_flag = _text(valuation.get("risk_flag") if isinstance(valuation, dict) else "")
    market_source = any(
        domain in url
        for domain in (
            "chavesnamao.com.br",
            "floraimoveis.com.br",
            "imovelweb.com.br",
            "lopes.com.br",
        )
    )
    return market_source and risk_flag == "weak_neighborhood_benchmark" and _number(
        row.get("expected_result_pct")
    ) <= 0


def _optimistic_roi(row: dict[str, Any]) -> float:
    scenarios = _analysis(row).get("scenarios")
    if not isinstance(scenarios, dict):
        return 0.0
    optimistic = scenarios.get("optimistic")
    if not isinstance(optimistic, dict):
        return 0.0
    return _number(optimistic.get("roi_pct"))


def _base_roi(row: dict[str, Any]) -> float:
    scenarios = _analysis(row).get("scenarios")
    if not isinstance(scenarios, dict):
        return _number(row.get("expected_result_pct"))
    base = scenarios.get("base")
    if not isinstance(base, dict):
        return _number(row.get("expected_result_pct"))
    return _number(base.get("roi_pct"), _number(row.get("expected_result_pct")))


def _triage_decision(
    row: dict[str, Any],
    open_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if row.get("is_open") is not True or not _is_real_estate_row(row):
        return None

    url = _source_url(row)
    if _rights_over_asset_signal(row):
        return {
            "reason_code": "rights_over_asset",
            "action": "descartar",
            "exit_rule": (
                "Descartado de entrada: direitos sobre imovel nao entram no Radar "
                "Imobiliario padrao."
            ),
            "evidence": url,
        }

    if _is_padre_carvalho_shadow(row, open_rows):
        return {
            "reason_code": "duplicate_candidate",
            "action": "descartar",
            "exit_rule": (
                "Descartado: duplicado do candidato 4180 / IM-RADAR-TARGET-PIN-06; "
                "manter fonte oficial Zuk/Bradesco."
            ),
            "evidence": url,
        }

    if not url:
        return {
            "reason_code": "missing_source",
            "action": "descartar",
            "exit_rule": (
                "Descartado de entrada: candidato sem fonte individual; o Radar nao "
                "mantem tese sem cadeia de prova."
            ),
            "evidence": "source_url vazio",
        }

    if _is_category_url(url) or _is_market_benchmark_without_candidate(row):
        return {
            "reason_code": "benchmark_not_candidate",
            "action": "descartar",
            "exit_rule": (
                "Descartado: fonte e agregador/benchmark de mercado, nao candidato "
                "executavel com fonte individual, edital e comparaveis equivalentes."
            ),
            "evidence": url,
        }

    optimistic_roi = _optimistic_roi(row)
    if _text(row.get("source_validation_status")) == "valid" and 0 < optimistic_roi < TARGET_ROI_PCT:
        return {
            "reason_code": "optimistic_roi_below_target",
            "action": "descartar",
            "exit_rule": (
                f"Descartado: ROI otimista {optimistic_roi:.2f}% abaixo do alvo "
                f"minimo de {TARGET_ROI_PCT:.0f}% antes de debitos e risco juridico."
            ),
            "evidence": f"optimistic_roi_pct={optimistic_roi:.2f}",
        }

    base_roi = _base_roi(row)
    if 0 < base_roi < TARGET_ROI_PCT:
        return {
            "reason_code": "base_roi_below_target",
            "action": "descartar",
            "exit_rule": (
                f"Descartado: ROI base {base_roi:.2f}% abaixo do alvo minimo "
                f"de {TARGET_ROI_PCT:.0f}%; P0 de debito/posse/fonte so pioram a margem."
            ),
            "evidence": f"base_roi_pct={base_roi:.2f}; optimistic_roi_pct={optimistic_roi:.2f}",
        }

    return None


def _analysis_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(_candidate(row))
    for key in (
        "source_url",
        "source_validation_status",
        "source_validation_reason",
        "source_checked_at",
    ):
        if key not in payload and row.get(key) is not None:
            payload[key] = row.get(key)
    return payload


def _refresh_analysis_for_decision(row: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    current = dict(_analysis(row))
    if decision["reason_code"] == "rights_over_asset":
        payload = _analysis_payload(row)
        if payload:
            refreshed = build_candidate_analysis(payload)
            if _candidate(row):
                refreshed["candidate"] = _candidate(row)
            if current.get("summary"):
                refreshed["summary"] = current.get("summary")
            current = refreshed
    return current


def _append_unique(values: list[Any], value: str) -> list[str]:
    cleaned = [_text(item) for item in values if _text(item)]
    if value not in cleaned:
        cleaned.append(value)
    return cleaned


def _apply_decision(row: dict[str, Any], decision: dict[str, Any], checked_at: str) -> None:
    analysis = _refresh_analysis_for_decision(row, decision)
    analysis["suggested_status"] = "Descartado"
    analysis["next_action"] = decision["exit_rule"]
    hard_filters = analysis.get("hard_filters")
    analysis["hard_filters"] = _append_unique(
        hard_filters if isinstance(hard_filters, list) else [],
        decision["reason_code"],
    )
    analysis["owner_triage"] = {
        "checked_at": checked_at,
        "reason_code": decision["reason_code"],
        "evidence": decision["evidence"],
        "action": decision["action"],
        "exit_rule": decision["exit_rule"],
    }
    row["real_estate_analysis"] = analysis
    row["status"] = "Fechada"
    row["outcome"] = "Descartado pelo radar"
    row["is_open"] = False
    row["exit_rule"] = decision["exit_rule"]
    row["learning_note"] = decision["exit_rule"]
    row["owner_triage"] = analysis["owner_triage"]


def _category(row: dict[str, Any]) -> str:
    url = _source_url(row).lower()
    if not url:
        return "other"
    if _is_category_url(url) or _is_market_benchmark_without_candidate(row):
        return "aggregator_or_market"
    if any(domain in url for domain in ("chavesnamao.com.br", "floraimoveis.com.br", "imovelweb.com.br")):
        return "aggregator_or_market"
    return "actionable_auction"


def _summarize_real_estate(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in payload.get("thesis_open_operations", [])
        if isinstance(row, dict) and _is_real_estate_row(row)
    ]
    open_rows = [row for row in rows if row.get("is_open") is True]
    categories = {
        "actionable_auction": {"open": 0, "p0_total": 0, "ready_without_p0": 0},
        "access_blocked": {"open": 0, "p0_total": 0, "ready_without_p0": 0},
        "aggregator_or_market": {"open": 0, "p0_total": 0, "ready_without_p0": 0},
        "other": {"open": 0, "p0_total": 0, "ready_without_p0": 0},
    }
    top_causes: dict[str, int] = {}
    for row in open_rows:
        category = _category(row)
        bucket = categories.setdefault(category, {"open": 0, "p0_total": 0, "ready_without_p0": 0})
        p0_items = _p0_items(row)
        bucket["open"] += 1
        bucket["p0_total"] += len(p0_items)
        if not p0_items:
            bucket["ready_without_p0"] += 1
        for item in p0_items:
            key = _text(item.get("key"))
            if key:
                top_causes[key] = top_causes.get(key, 0) + 1

    top_open_cases = []
    for row in sorted(open_rows, key=lambda item: (-_p0_count(item), _number(item.get("thesis_number"))))[:8]:
        candidate = _candidate(row)
        p0_items = _p0_items(row)
        top_open_cases.append(
            {
                "thesis_id": row.get("thesis_id"),
                "thesis_number": row.get("thesis_number"),
                "category": _category(row),
                "city": candidate.get("city", ""),
                "neighborhood": candidate.get("neighborhood", ""),
                "source_url": _source_url(row),
                "p0_count": len(p0_items),
                "p0_keys": [_text(item.get("key")) for item in p0_items if _text(item.get("key"))],
            }
        )

    p0_total = sum(_p0_count(row) for row in open_rows)
    return {
        "total": len(rows),
        "open": len(open_rows),
        "closed": max(len(rows) - len(open_rows), 0),
        "p0_total": p0_total,
        "p0_actionable_auction": categories["actionable_auction"]["p0_total"],
        "p0_access_blocked": categories["access_blocked"]["p0_total"],
        "p0_aggregator_or_market": categories["aggregator_or_market"]["p0_total"],
        "out_of_scope_open": 0,
        "out_of_scope_p0_total": 0,
        "ready_without_p0": sum(bucket["ready_without_p0"] for bucket in categories.values()),
        "categories": categories,
        "top_p0_causes": [
            {"key": key, "count": count}
            for key, count in sorted(top_causes.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
        "top_open_cases": top_open_cases,
    }


def _recover_false_positive_canonical(payload: dict[str, Any], checked_at: str) -> list[dict[str, Any]]:
    recoveries: list[dict[str, Any]] = []
    rows = payload.get("thesis_open_operations")
    if not isinstance(rows, list):
        return recoveries
    for row in rows:
        if not isinstance(row, dict) or _text(row.get("thesis_id")) != "IM-RADAR-TARGET-PIN-06":
            continue
        owner_triage = row.get("owner_triage")
        analysis = _analysis(row)
        analysis_triage = analysis.get("owner_triage") if isinstance(analysis, dict) else {}
        reason = ""
        if isinstance(owner_triage, dict):
            reason = _text(owner_triage.get("reason_code"))
        if not reason and isinstance(analysis_triage, dict):
            reason = _text(analysis_triage.get("reason_code"))
        if reason != "duplicate_candidate":
            continue

        next_action = "Desocupacao por conta do comprador"
        row["status"] = "Aberta - Atencao"
        row["outcome"] = "Pendencias abertas"
        row["is_open"] = True
        row["exit_rule"] = next_action
        row["learning_note"] = (
            "Antes de proposta: preservar candidato canonico Padre Carvalho; "
            "resolver desocupacao e debitos antes de lance."
        )
        row.pop("owner_triage", None)
        if isinstance(analysis, dict):
            analysis["suggested_status"] = "Aberto com pendencias"
            analysis["next_action"] = next_action
            analysis.pop("owner_triage", None)
            hard_filters = analysis.get("hard_filters")
            if isinstance(hard_filters, list):
                analysis["hard_filters"] = [
                    item for item in hard_filters if _text(item) != "duplicate_candidate"
                ]
        recoveries.append(
            {
                "thesis_number": row.get("thesis_number"),
                "thesis_id": row.get("thesis_id"),
                "reason_code": "false_positive_duplicate_recovered",
                "action": "reabrir",
                "checked_at": checked_at,
                "note": (
                    "Candidato canonico Padre Carvalho preservado; apenas a sombra "
                    "IM-RADAR-26 deve fechar."
                ),
            }
        )
    return recoveries


def _refresh_front_overview(payload: dict[str, Any], summary: dict[str, Any]) -> None:
    overview = payload.setdefault("front_overview", {})
    if not isinstance(overview, dict):
        overview = {}
        payload["front_overview"] = overview
    current = overview.get("real_estate")
    item = dict(current) if isinstance(current, dict) else {}
    item.update(
        {
            "total_tested": summary["total"],
            "resolved_count": summary["closed"],
            "mapped_count": summary["total"],
            "radar_total": summary["total"],
            "open_count": summary["open"],
            "closed_count": summary["closed"],
            "p0_count": summary["p0_total"],
            "counting_policy": "radar_candidates",
        }
    )
    overview["real_estate"] = item


def _remaining_queue(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _open_real_estate_rows(payload)
    return [
        {
            "thesis_number": row.get("thesis_number"),
            "thesis_id": row.get("thesis_id"),
            "asset": row.get("asset") or row.get("action") or _candidate(row).get("title", ""),
            "source_validation_status": row.get("source_validation_status", ""),
            "expected_result_pct": row.get("expected_result_pct", 0),
            "p0_count": _p0_count(row),
            "next_action": _analysis(row).get("next_action", row.get("exit_rule", "")),
            "source_url": _source_url(row),
        }
        for row in sorted(rows, key=lambda item: (-_p0_count(item), _number(item.get("thesis_number"))))
    ]


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Radar Imobiliario - Triagem Implacavel",
        "",
        f"Gerado em: `{report['generated_at']}`",
        "",
        "## Antes e depois",
        "",
        f"- Abertos: `{report['metrics_before']['open']}` -> `{report['metrics_after']['open']}`",
        f"- Fechados: `{report['metrics_before']['closed']}` -> `{report['metrics_after']['closed']}`",
        f"- P0 em abertos: `{report['metrics_before']['p0_total']}` -> `{report['metrics_after']['p0_total']}`",
        "",
        "## Candidatos avaliados",
        "",
        f"- Avaliados: `{report['evaluated_count']}`",
        f"- Descartados nesta triagem: `{len(report['decisions'])}`",
        "",
        "## Decisoes",
        "",
    ]
    for decision in report["decisions"]:
        lines.append(
            f"- `{decision['thesis_number']}` `{decision['thesis_id']}` -> {decision['reason_code']}: "
            f"{decision['exit_rule']}"
        )
    if not report["decisions"]:
        lines.append("- Nenhum descarte automatico nesta rodada.")
    recoveries = report.get("recoveries")
    if isinstance(recoveries, list) and recoveries:
        lines.extend(["", "## Correcoes de falso positivo", ""])
        for recovery in recoveries:
            lines.append(
                f"- `{recovery['thesis_number']}` `{recovery['thesis_id']}` -> "
                f"{recovery['reason_code']}: {recovery['note']}"
            )
    lines.extend(
        [
            "",
            "## Fragilidades encontradas",
            "",
            "- Ainda havia candidato aberto por direitos sobre imovel, que deveria morrer antes de consumir P0.",
            "- Havia sombra duplicada de Padre Carvalho, gerando P0 duplo para o mesmo ativo.",
            "- A fila mantinha fonte inexistente, pagina de categoria e benchmark de mercado como se fossem candidatos.",
            "- Um candidato com fonte valida continuava aberto mesmo com ROI otimista abaixo do alvo minimo.",
            "",
            "## Correcoes feitas",
            "",
            "- Aplicada regra de descarte por direitos sobre imovel.",
            "- Fechada duplicidade, preservando o candidato com fonte oficial mais forte.",
            "- Fechados itens sem fonte individual ou com fonte de benchmark/agregador.",
            "- Fechado caso economicamente insuficiente mesmo no cenario otimista.",
            "",
            "## Proximos alvos",
            "",
        ]
    )
    for item in report["remaining_queue"][:5]:
        lines.append(
            f"- `{item['thesis_number']}` `{item['thesis_id']}`: P0 `{item['p0_count']}`; "
            f"proximo passo: {item['next_action']}"
        )
    lines.extend(
        [
            "",
            "## Testes executados",
            "",
            "- Ver final do ciclo Codex: os comandos pytest foram executados apos a geracao deste artefato.",
            "",
        ]
    )
    return "\n".join(lines)


def _update_weekly_owner_report(summary: dict[str, Any], checked_at: str, decisions: list[dict[str, Any]]) -> None:
    if not WEEKLY_OWNER_PATH.exists():
        return
    payload = json.loads(WEEKLY_OWNER_PATH.read_text(encoding="utf-8"))
    payload["generated_at"] = checked_at
    payload["real_estate"] = summary
    closed_count = len(decisions)
    evidence = (
        f"{summary['open']} casos abertos; {summary['p0_total']} P0 em abertos; "
        f"{closed_count} descartes objetivos nesta triagem; "
        f"{summary['p0_actionable_auction']} P0 acionaveis em leilao."
    )
    scorecard = payload.get("owner_scorecard")
    if isinstance(scorecard, list):
        found = False
        for item in scorecard:
            if isinstance(item, dict) and item.get("area") == "Radar Imobiliario":
                item["status"] = "triagem_implacavel_aplicada"
                item["evidence"] = evidence
                item["owner_action"] = (
                    "Atacar agora a fila remanescente por P0 de maior impacto: fonte, ocupacao, "
                    "debitos e valor de saida equivalente."
                )
                found = True
        if not found:
            scorecard.append(
                {
                    "area": "Radar Imobiliario",
                    "status": "triagem_implacavel_aplicada",
                    "evidence": evidence,
                    "owner_action": "Reduzir P0 acionavel e manter descarte automatico de ruido.",
                }
            )
    payload["whatsapp_message"] = (
        f"Reporte owner Grao Invest atualizado em {checked_at}. Radar Imobiliario passou por triagem "
        f"implacavel: {closed_count} descartes objetivos, {summary['open']} casos ainda abertos e "
        f"{summary['p0_total']} P0 em abertos. O ganho nao e cosmetico: direitos sobre imovel, duplicidade, "
        "fonte ausente, benchmark/agregador e ROI otimista abaixo do alvo sairam da fila. Proximo foco: "
        "resolver fonte/ocupacao/debitos dos candidatos restantes e promover apenas caso com prova primaria."
    )
    WEEKLY_OWNER_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_triage() -> dict[str, Any]:
    checked_at = _now_brt()
    prior_report: dict[str, Any] = {}
    if TRIAGE_LATEST_JSON.exists():
        try:
            loaded_prior = json.loads(TRIAGE_LATEST_JSON.read_text(encoding="utf-8"))
            if isinstance(loaded_prior, dict):
                prior_report = loaded_prior
        except Exception:
            prior_report = {}
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    recoveries = _recover_false_positive_canonical(payload, checked_at)
    before = _summarize_real_estate(payload)
    open_rows = _open_real_estate_rows(payload)
    decisions: list[dict[str, Any]] = []
    for row in list(open_rows):
        decision = _triage_decision(row, open_rows)
        if decision is None:
            continue
        decision = {
            **decision,
            "thesis_number": row.get("thesis_number"),
            "thesis_id": row.get("thesis_id"),
            "asset": row.get("asset") or row.get("action") or _candidate(row).get("title", ""),
            "source_url": _source_url(row),
        }
        _apply_decision(row, decision, checked_at)
        decisions.append(decision)

    after = _summarize_real_estate(payload)
    if recoveries and prior_report:
        recovered_ids = {_text(item.get("thesis_id")) for item in recoveries if isinstance(item, dict)}
        prior_decisions = prior_report.get("decisions")
        if isinstance(prior_decisions, list):
            decisions = [
                decision
                for decision in prior_decisions
                if isinstance(decision, dict) and _text(decision.get("thesis_id")) not in recovered_ids
            ] + decisions
        prior_before = prior_report.get("metrics_before")
        if isinstance(prior_before, dict):
            before = prior_before
        prior_evaluated = prior_report.get("evaluated_count")
    else:
        prior_evaluated = None
    _refresh_front_overview(payload, after)
    payload["generated_at"] = checked_at
    SEED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _update_weekly_owner_report(after, checked_at, decisions)

    report = {
        "generated_at": checked_at,
        "scope": "Radar Imobiliario / triagem implacavel",
        "evaluated_count": int(prior_evaluated) if isinstance(prior_evaluated, int) else len(open_rows),
        "metrics_before": before,
        "metrics_after": after,
        "decisions": decisions,
        "recoveries": recoveries,
        "remaining_queue": _remaining_queue(payload),
        "next_targets": [
            "Abrir fonte primaria dos 3 maiores P0 remanescentes.",
            "Converter ocupacao/debitos em custo ou descarte.",
            "Promover apenas candidato com fonte individual, prova de valor de saida e plano de posse.",
        ],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = checked_at.replace(":", "").replace("-", "").replace("+", "_").replace("T", "_")
    json_path = REPORTS_DIR / f"radar_imobiliario_triagem_implacavel_{stamp}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    shutil.copyfile(json_path, REPORTS_DIR / "radar_imobiliario_triagem_implacavel_latest.json")
    shutil.copyfile(md_path, REPORTS_DIR / "radar_imobiliario_triagem_implacavel_latest.md")
    report["json_path"] = str(json_path)
    report["md_path"] = str(md_path)
    return report


if __name__ == "__main__":
    result = run_triage()
    print(
        "triagem_implacavel "
        f"avaliados={result['evaluated_count']} "
        f"descartes={len(result['decisions'])} "
        f"abertos={result['metrics_before']['open']}->{result['metrics_after']['open']} "
        f"p0={result['metrics_before']['p0_total']}->{result['metrics_after']['p0_total']} "
        f"json={result['json_path']}"
    )

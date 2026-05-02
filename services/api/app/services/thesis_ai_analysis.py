from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import httpx
from app.models import FundamentalSnapshot, IndicatorSnapshot, MarketTick, NewsArticle, Signal
from app.services.asset_classes import asset_class_label, classify_instrument, normalize_instrument
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

EDUCATIONAL_DISCLAIMER = "Conteudo educacional; nao e recomendacao de investimento."
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
type MacroFetcher = Callable[[], dict[str, Any]]


def build_thesis_ai_analysis(
    db: Session,
    *,
    user_id: int,
    instrument: str,
    question: str | None = None,
    horizon_days: int = 20,
    macro_fetcher: MacroFetcher | None = None,
) -> dict[str, Any]:
    symbol = normalize_instrument(instrument)
    if not symbol:
        raise ValueError("Instrumento obrigatorio para analise IA da tese")

    fetcher = macro_fetcher or fetch_bcb_macro_context
    macro_context = _safe_macro_context(fetcher)
    context = _build_internal_context(
        db,
        user_id=user_id,
        instrument=symbol,
        horizon_days=horizon_days,
    )
    fallback = _local_fallback_analysis(context, macro_context, question=question)

    if not os.getenv("OPENAI_API_KEY"):
        return fallback

    try:
        ai_payload = call_openai_structured_analysis(
            context=context,
            macro_context=macro_context,
            question=question,
            horizon_days=horizon_days,
        )
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return fallback

    normalized = _normalize_analysis_payload(
        ai_payload,
        fallback=fallback,
        macro_context=macro_context,
    )
    normalized["provider"] = "openai"
    return normalized


def fetch_bcb_macro_context(timeout: float = 4.0) -> dict[str, Any]:
    series = {
        "Selic meta": {"code": 432, "unit": "% a.a."},
        "IPCA mensal": {"code": 433, "unit": "%"},
        "USD/BRL": {"code": 1, "unit": "BRL"},
    }
    items: list[dict[str, Any]] = []
    failures: list[str] = []

    for name, config in series.items():
        url = (
            "https://api.bcb.gov.br/dados/serie/"
            f"bcdata.sgs.{config['code']}/dados/ultimos/1?formato=json"
        )
        try:
            response = httpx.get(url, timeout=timeout)
            response.raise_for_status()
            rows = response.json()
            if not rows:
                failures.append(f"{name}: vazio")
                continue
            latest = rows[-1]
            items.append(
                {
                    "name": name,
                    "value": _safe_float(latest.get("valor")),
                    "date": str(latest.get("data") or ""),
                    "source": "BCB SGS",
                    "unit": config["unit"],
                }
            )
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
            failures.append(f"{name}: {exc}")

    if not items:
        return {
            "status": "unavailable",
            "reason": "; ".join(failures) or "BCB sem dados no momento",
            "items": [],
        }
    return {
        "status": "available" if not failures else "partial",
        "reason": "; ".join(failures),
        "items": items,
    }


def call_openai_structured_analysis(
    *,
    context: dict[str, Any],
    macro_context: dict[str, Any],
    question: str | None,
    horizon_days: int,
) -> dict[str, Any]:
    access_token = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    request_body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "Voce e um analista educacional de renda variavel para investidores "
                    "brasileiros. Explique tese, evidencias, riscos, gatilhos e condicoes "
                    "de saida sem dar recomendacao personalizada. Seja curto, objetivo e "
                    "sempre inclua o disclaimer educacional."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "horizon_days": horizon_days,
                        "internal_context": context,
                        "macro_context": macro_context,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "reasoning": {"effort": "low"},
        "store": False,
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "thesis_ai_analysis",
                "strict": True,
                "schema": _analysis_json_schema(),
            },
        },
    }
    response = httpx.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=request_body,
        timeout=timeout,
    )
    response.raise_for_status()
    output_text = _extract_response_text(response.json())
    return json.loads(output_text)


def _build_internal_context(
    db: Session,
    *,
    user_id: int,
    instrument: str,
    horizon_days: int,
) -> dict[str, Any]:
    latest_ticks = list(
        db.scalars(
            select(MarketTick)
            .where(MarketTick.instrument == instrument)
            .order_by(desc(MarketTick.event_time), desc(MarketTick.id))
            .limit(5)
        )
    )
    latest_signal = db.scalar(
        select(Signal)
        .where(Signal.user_id == user_id)
        .where(Signal.instrument == instrument)
        .order_by(desc(Signal.availability_time), desc(Signal.id))
        .limit(1)
    )
    latest_indicator = db.scalar(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.instrument == instrument)
        .order_by(desc(IndicatorSnapshot.availability_time), desc(IndicatorSnapshot.id))
        .limit(1)
    )
    latest_fundamental = db.scalar(
        select(FundamentalSnapshot)
        .where(FundamentalSnapshot.instrument == instrument)
        .order_by(desc(FundamentalSnapshot.availability_time), desc(FundamentalSnapshot.id))
        .limit(1)
    )
    latest_news = list(
        db.scalars(
            select(NewsArticle)
            .where(NewsArticle.instrument == instrument)
            .order_by(desc(NewsArticle.published_at), desc(NewsArticle.id))
            .limit(3)
        )
    )
    asset_class = classify_instrument(instrument)
    return {
        "instrument": instrument,
        "asset_class": asset_class,
        "asset_class_label": asset_class_label(asset_class),
        "horizon_days": horizon_days,
        "ticks": [
            {
                "event_time": tick.event_time,
                "price": tick.price,
                "volume": tick.volume,
                "provider": tick.provider,
            }
            for tick in latest_ticks
        ],
        "signal": _signal_payload(latest_signal),
        "indicator": _indicator_payload(latest_indicator),
        "fundamental": _fundamental_payload(latest_fundamental),
        "news": [
            {
                "headline": article.headline,
                "source_name": article.source_name,
                "published_at": article.published_at,
                "credibility_score": article.credibility_score,
                "anti_hype_score": article.anti_hype_score,
            }
            for article in latest_news
        ],
    }


def _local_fallback_analysis(
    context: dict[str, Any],
    macro_context: dict[str, Any],
    *,
    question: str | None,
) -> dict[str, Any]:
    instrument = str(context["instrument"])
    asset_class = str(context["asset_class"])
    signal = context.get("signal") or {}
    indicator = context.get("indicator") or {}
    fundamental = context.get("fundamental") or {}
    ticks = list(context.get("ticks") or [])
    news = list(context.get("news") or [])

    confidence = _clamp(float(signal.get("confidence") or 0.55), 0.2, 0.85)
    latest_price = ticks[0]["price"] if ticks else None
    evidence = _fallback_evidence(signal, indicator, fundamental, ticks, news)
    risks = _fallback_risks(asset_class, macro_context, indicator)
    triggers = _fallback_triggers(indicator, signal)
    exit_conditions = _fallback_exit_conditions(signal)
    summary = f"{instrument}: leitura educacional de tese com confianca {confidence:.0%}."
    if latest_price is not None:
        summary += f" Ultimo preco observado: {float(latest_price):.2f}."
    if question:
        summary += f" Foco da pergunta: {question[:120]}."

    return {
        "instrument": instrument,
        "asset_class": asset_class,
        "summary": summary,
        "thesis": _fallback_thesis(instrument, signal, indicator, fundamental),
        "evidence": evidence,
        "risks": risks,
        "triggers": triggers,
        "exit_conditions": exit_conditions,
        "macro_context": _normalize_macro_context(macro_context),
        "confidence_score": round(confidence, 4),
        "education_disclaimer": EDUCATIONAL_DISCLAIMER,
        "sources": _fallback_sources(context, macro_context),
        "provider": "local_fallback",
        "horizon_days": context["horizon_days"],
    }


def _analysis_json_schema() -> dict[str, Any]:
    string_array = {"type": "array", "items": {"type": "string"}}
    macro_item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"},
            "date": {"type": "string"},
            "source": {"type": "string"},
            "unit": {"type": "string"},
        },
        "required": ["name", "value", "date", "source", "unit"],
        "additionalProperties": False,
    }
    macro_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "reason": {"type": "string"},
            "items": {"type": "array", "items": macro_item},
        },
        "required": ["status", "reason", "items"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "instrument": {"type": "string"},
            "asset_class": {"type": "string"},
            "summary": {"type": "string"},
            "thesis": {"type": "string"},
            "evidence": string_array,
            "risks": string_array,
            "triggers": string_array,
            "exit_conditions": string_array,
            "macro_context": macro_schema,
            "confidence_score": {"type": "number"},
            "education_disclaimer": {"type": "string"},
            "sources": string_array,
        },
        "required": [
            "instrument",
            "asset_class",
            "summary",
            "thesis",
            "evidence",
            "risks",
            "triggers",
            "exit_conditions",
            "macro_context",
            "confidence_score",
            "education_disclaimer",
            "sources",
        ],
        "additionalProperties": False,
    }


def _normalize_analysis_payload(
    payload: dict[str, Any],
    *,
    fallback: dict[str, Any],
    macro_context: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(fallback)
    for key in [
        "instrument",
        "asset_class",
        "summary",
        "thesis",
        "evidence",
        "risks",
        "triggers",
        "exit_conditions",
        "confidence_score",
        "education_disclaimer",
        "sources",
    ]:
        value = payload.get(key)
        if value not in (None, "", []):
            normalized[key] = value
    normalized["macro_context"] = _normalize_macro_context(
        payload.get("macro_context") or macro_context
    )
    normalized["confidence_score"] = round(
        _clamp(float(normalized.get("confidence_score") or 0.55), 0.0, 1.0),
        4,
    )
    disclaimer = str(normalized.get("education_disclaimer") or "")
    if "nao e recomendacao" not in disclaimer.lower():
        normalized["education_disclaimer"] = EDUCATIONAL_DISCLAIMER
    return normalized


def _extract_response_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return str(response_payload["output_text"])
    for output_item in response_payload.get("output") or []:
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content") or []:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") == "output_text" and isinstance(
                content_item.get("text"),
                str,
            ):
                return str(content_item["text"])
    raise KeyError("Resposta OpenAI sem output_text")


def _safe_macro_context(fetcher: MacroFetcher) -> dict[str, Any]:
    try:
        return _normalize_macro_context(fetcher())
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc), "items": []}


def _normalize_macro_context(raw: dict[str, Any]) -> dict[str, Any]:
    items = raw.get("items") if isinstance(raw, dict) else []
    normalized_items: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "name": str(item.get("name") or ""),
                    "value": _safe_float(item.get("value")),
                    "date": str(item.get("date") or ""),
                    "source": str(item.get("source") or "BCB SGS"),
                    "unit": str(item.get("unit") or ""),
                }
            )
    return {
        "status": str(raw.get("status") or "unavailable"),
        "reason": str(raw.get("reason") or ""),
        "items": normalized_items,
    }


def _signal_payload(signal: Signal | None) -> dict[str, Any] | None:
    if signal is None:
        return None
    return {
        "signal_type": signal.signal_type,
        "confidence": signal.confidence,
        "rationale": signal.rationale[:600],
        "anti_hype_score": signal.anti_hype_score,
        "signal_status": signal.signal_status,
        "reference_time": signal.reference_time,
    }


def _indicator_payload(snapshot: IndicatorSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "sma_5": snapshot.sma_5,
        "sma_10": snapshot.sma_10,
        "sma_20": snapshot.sma_20,
        "rsi_14": snapshot.rsi_14,
        "volatility_10": snapshot.volatility_10,
        "momentum_5": snapshot.momentum_5,
        "macd": snapshot.macd,
    }


def _fundamental_payload(snapshot: FundamentalSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "pe_ratio": snapshot.pe_ratio,
        "pb_ratio": snapshot.pb_ratio,
        "ev_ebitda": snapshot.ev_ebitda,
        "dividend_yield": snapshot.dividend_yield,
        "roe": snapshot.roe,
        "net_margin": snapshot.net_margin,
        "revenue_growth": snapshot.revenue_growth,
        "payout_ratio": snapshot.payout_ratio,
    }


def _fallback_thesis(
    instrument: str,
    signal: dict[str, Any],
    indicator: dict[str, Any],
    fundamental: dict[str, Any],
) -> str:
    signal_type = signal.get("signal_type") or "sem sinal ativo"
    rsi = indicator.get("rsi_14")
    roe = fundamental.get("roe")
    parts = [f"A tese para {instrument} parte de {signal_type}."]
    if rsi is not None:
        parts.append(f"RSI em {float(rsi):.1f} ajuda a medir esticamento ou folego.")
    if roe is not None:
        parts.append(f"ROE em {float(roe):.1f}% entra como filtro fundamental.")
    parts.append("A decisao final deve passar por perfil, tamanho de posicao e stop.")
    return " ".join(parts)


def _fallback_evidence(
    signal: dict[str, Any],
    indicator: dict[str, Any],
    fundamental: dict[str, Any],
    ticks: list[Any],
    news: list[Any],
) -> list[str]:
    evidence: list[str] = []
    if signal:
        evidence.append(
            f"Sinal interno {signal.get('signal_type')} com confianca "
            f"{float(signal.get('confidence') or 0.0):.0%}."
        )
    if indicator:
        evidence.append(
            f"Indicadores: RSI {float(indicator.get('rsi_14') or 0):.1f}, "
            f"momentum {float(indicator.get('momentum_5') or 0):.2%}."
        )
    if fundamental:
        evidence.append(
            f"Fundamentos: P/L {float(fundamental.get('pe_ratio') or 0):.1f}, "
            f"ROE {float(fundamental.get('roe') or 0):.1f}%."
        )
    if len(ticks) >= 2:
        evidence.append(
            f"Preco recente saiu de {float(ticks[-1]['price']):.2f} "
            f"para {float(ticks[0]['price']):.2f}."
        )
    if news:
        evidence.append(f"Noticia recente: {str(news[0].get('headline') or '')[:140]}.")
    return evidence or ["Sem dados suficientes; use como checklist de investigacao."]


def _fallback_risks(
    asset_class: str,
    macro_context: dict[str, Any],
    indicator: dict[str, Any],
) -> list[str]:
    risks = ["Volatilidade de mercado pode invalidar a tese antes do horizonte."]
    if asset_class in {"fii", "stock", "bdr", "etf"}:
        risks.append(
            "Liquidez, concentracao setorial e eventos corporativos podem distorcer o sinal."
        )
    if macro_context.get("status") in {"available", "partial"}:
        risks.append(
            "Juros, inflacao e cambio podem alterar preco justo e fluxo para renda variavel."
        )
    if float(indicator.get("rsi_14") or 0) > 70:
        risks.append("RSI elevado sugere risco de entrada esticada.")
    return risks


def _fallback_triggers(
    indicator: dict[str, Any],
    signal: dict[str, Any],
) -> list[str]:
    triggers = ["Reavaliar se surgir noticia material ou mudanca brusca de volume."]
    if indicator:
        triggers.append(
            "Acompanhar perda/recuperacao das medias curtas contra a media de 20 periodos."
        )
    if signal:
        triggers.append("Comparar novo sinal com a confianca e o racional do sinal atual.")
    return triggers


def _fallback_exit_conditions(signal: dict[str, Any]) -> list[str]:
    conditions = [
        "Sair ou reduzir risco se o racional original deixar de ser valido.",
        "Definir stop antes da entrada e respeitar limite de perda por operacao.",
    ]
    if signal:
        conditions.append("Revisar a tese quando a confianca do sinal cair ou for substituida.")
    return conditions


def _fallback_sources(context: dict[str, Any], macro_context: dict[str, Any]) -> list[str]:
    sources = ["sinais internos", "ticks de mercado"]
    if context.get("fundamental"):
        sources.append("fundamentos internos point-in-time")
    if context.get("news"):
        sources.append("noticias ingeridas")
    if macro_context.get("items"):
        sources.append("BCB SGS")
    return sources


def _safe_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(str(value).replace(",", "."))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

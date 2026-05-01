from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import FundamentalSnapshot, MarketTick
from app.schemas import FundamentalIngestRequest
from app.services.audit import record_audit_event
from app.services.fundamentals import ingest_fundamentals
from app.services.utils import isoformat, utc_now
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

YAHOO_SOURCE_NAME = "Yahoo Finance QuoteSummary"
YAHOO_SOURCE_TYPE = "market_data_api"
YAHOO_PROVIDER_NAME = "yahoo"
YAHOO_MODULES = "defaultKeyStatistics,financialData,summaryDetail,price"
BRAPI_SOURCE_NAME = "Brapi Quote API"
BRAPI_SOURCE_TYPE = "market_data_api"
BRAPI_PROVIDER_NAME = "brapi"
AUTO_PROVIDER_NAME = "auto"
MAX_FUNDAMENTALS_SYNC_INSTRUMENTS = 4000

_NEUTRAL_FIELD_VALUES: dict[str, float] = {
    "pe_ratio": 18.0,
    "pb_ratio": 2.5,
    "ev_ebitda": 12.0,
    "dividend_yield": 3.0,
    "roe": 10.0,
    "net_margin": 6.0,
    "revenue_growth": 3.0,
    "payout_ratio": 50.0,
}
_PREFERRED_EQUITY_TICKER = re.compile(r"^[A-Z]{4}[3-6]$")


class ExternalFundamentalInstrumentResult(TypedDict):
    status: str
    provider_symbol: str
    fundamental_id: int | None
    reference_time: str | None
    availability_time: str | None
    completeness_pct: float
    missing_fields: list[str]
    version_tag: str | None
    error: str | None


class ExternalFundamentalSyncResult(TypedDict):
    source: str
    provider_name: str
    requested_instruments: int
    selected_instruments: list[str]
    inserted: int
    duplicates_ignored: int
    failed: int
    by_instrument: dict[str, ExternalFundamentalInstrumentResult]


class _ProviderPayload(TypedDict):
    provider_name: str
    provider_symbol: str
    source_name: str
    source_type: str
    version_prefix: str
    raw_payload: dict[str, object]


class FundamentalCoverageRow(TypedDict):
    instrument: str
    has_fundamentals: bool
    snapshot_count: int
    latest_reference_time: str | None
    latest_availability_time: str | None
    latest_version_tag: str | None
    latest_source_name: str | None
    latest_market_event_time: str | None
    staleness_days: int | None


class FundamentalCoverageSnapshot(TypedDict):
    generated_at: str
    total_market_instruments: int
    market_instruments_with_fundamentals: int
    total_fundamental_instruments: int
    missing_fundamental_instruments: int
    coverage_pct: float
    rows: list[FundamentalCoverageRow]


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _previous_quarter_end(value: datetime) -> datetime:
    month = value.month
    year = value.year
    if month <= 3:
        return datetime(year - 1, 12, 31, tzinfo=UTC)
    if month <= 6:
        return datetime(year, 3, 31, tzinfo=UTC)
    if month <= 9:
        return datetime(year, 6, 30, tzinfo=UTC)
    return datetime(year, 9, 30, tzinfo=UTC)


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        raw = value.get("raw")
        if isinstance(raw, (int, float)):
            return float(raw)
    return None


def _epoch_to_datetime(value: object) -> datetime | None:
    epoch = _to_float(value)
    if epoch is None or epoch <= 0:
        return None
    return datetime.fromtimestamp(int(epoch), tz=UTC)


def _to_percentage(value: float | None) -> float | None:
    if value is None:
        return None
    if -1.5 <= value <= 1.5:
        return value * 100.0
    return value


def _nested(module_payload: dict[str, object], module: str, key: str) -> object | None:
    module_value = module_payload.get(module)
    if not isinstance(module_value, dict):
        return None
    return module_value.get(key)


def _normalize_snapshot(
    *,
    instrument: str,
    provider_symbol: str,
    raw_payload: dict[str, object],
    captured_at: datetime,
    source_name: str,
    source_type: str,
    version_prefix: str,
) -> tuple[FundamentalIngestRequest, list[str], float]:
    reference_time = _epoch_to_datetime(
        _nested(raw_payload, "defaultKeyStatistics", "lastFiscalYearEnd")
    )
    if reference_time is None:
        reference_time = _previous_quarter_end(captured_at)
    else:
        reference_time = datetime(
            reference_time.year,
            reference_time.month,
            reference_time.day,
            tzinfo=UTC,
        )

    pe_ratio = _to_float(_nested(raw_payload, "defaultKeyStatistics", "trailingPE"))
    pb_ratio = _to_float(_nested(raw_payload, "defaultKeyStatistics", "priceToBook"))
    ev_ebitda = _to_float(_nested(raw_payload, "defaultKeyStatistics", "enterpriseToEbitda"))
    dividend_yield = _to_percentage(
        _to_float(_nested(raw_payload, "summaryDetail", "dividendYield"))
    )
    roe = _to_percentage(_to_float(_nested(raw_payload, "financialData", "returnOnEquity")))
    net_margin = _to_percentage(_to_float(_nested(raw_payload, "financialData", "profitMargins")))
    revenue_growth = _to_percentage(
        _to_float(_nested(raw_payload, "financialData", "revenueGrowth"))
    )
    payout_ratio = _to_percentage(
        _to_float(_nested(raw_payload, "defaultKeyStatistics", "payoutRatio"))
    )

    values: dict[str, float | None] = {
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "ev_ebitda": ev_ebitda,
        "dividend_yield": dividend_yield,
        "roe": roe,
        "net_margin": net_margin,
        "revenue_growth": revenue_growth,
        "payout_ratio": payout_ratio,
    }
    missing_fields: list[str] = []
    normalized_values: dict[str, float] = {}
    for field_name, field_value in values.items():
        if field_value is None:
            missing_fields.append(field_name)
            normalized_values[field_name] = _NEUTRAL_FIELD_VALUES[field_name]
            continue
        normalized_values[field_name] = field_value

    normalized_values["pe_ratio"] = max(0.0, normalized_values["pe_ratio"])
    normalized_values["pb_ratio"] = max(0.0, normalized_values["pb_ratio"])
    normalized_values["ev_ebitda"] = max(0.0, normalized_values["ev_ebitda"])
    normalized_values["dividend_yield"] = max(0.0, normalized_values["dividend_yield"])
    normalized_values["payout_ratio"] = min(1000.0, max(0.0, normalized_values["payout_ratio"]))
    normalized_values["roe"] = min(1000.0, max(-1000.0, normalized_values["roe"]))
    normalized_values["net_margin"] = min(1000.0, max(-1000.0, normalized_values["net_margin"]))
    normalized_values["revenue_growth"] = min(
        1000.0,
        max(-1000.0, normalized_values["revenue_growth"]),
    )

    completeness_pct = round(((8 - len(missing_fields)) / 8) * 100.0, 4)
    version_basis = (
        f"{instrument.upper()}|{provider_symbol}|{reference_time.date().isoformat()}|"
        f"{normalized_values['pe_ratio']:.4f}|{normalized_values['pb_ratio']:.4f}|"
        f"{normalized_values['ev_ebitda']:.4f}|{normalized_values['dividend_yield']:.4f}|"
        f"{normalized_values['roe']:.4f}|{normalized_values['net_margin']:.4f}|"
        f"{normalized_values['revenue_growth']:.4f}|{normalized_values['payout_ratio']:.4f}|"
        f"{','.join(sorted(missing_fields))}"
    )
    version_hash = hashlib.sha1(version_basis.encode("utf-8")).hexdigest()[:12]
    version_tag = f"{version_prefix}-v1-{reference_time.date().isoformat()}-{version_hash}"

    availability_time = _epoch_to_datetime(_nested(raw_payload, "price", "regularMarketTime"))
    if availability_time is None:
        availability_time = captured_at
    if availability_time < reference_time:
        availability_time = reference_time

    request = FundamentalIngestRequest(
        instrument=instrument.upper(),
        source_name=source_name,
        source_type=source_type,
        reference_time=reference_time,
        availability_time=availability_time,
        pe_ratio=round(normalized_values["pe_ratio"], 6),
        pb_ratio=round(normalized_values["pb_ratio"], 6),
        ev_ebitda=round(normalized_values["ev_ebitda"], 6),
        dividend_yield=round(normalized_values["dividend_yield"], 6),
        roe=round(normalized_values["roe"], 6),
        net_margin=round(normalized_values["net_margin"], 6),
        revenue_growth=round(normalized_values["revenue_growth"], 6),
        payout_ratio=round(normalized_values["payout_ratio"], 6),
        version_tag=version_tag,
    )
    return request, missing_fields, completeness_pct


def _yahoo_symbol(instrument: str) -> str:
    return f"{instrument.upper()}.SA"


def _fetch_yahoo_quote_summary(provider_symbol: str) -> dict[str, object]:
    params = urlencode({"modules": YAHOO_MODULES})
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{provider_symbol}?{params}"
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ValueError(f"Provider yahoo retornou HTTP {exc.code}.") from exc
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("Provider yahoo retornou payload invalido.")
    quote_summary = parsed.get("quoteSummary")
    if not isinstance(quote_summary, dict):
        raise ValueError("Provider yahoo retornou quoteSummary ausente.")
    error_payload = quote_summary.get("error")
    if isinstance(error_payload, dict):
        description = error_payload.get("description")
        if isinstance(description, str) and description.strip():
            raise ValueError(f"Provider yahoo retornou erro: {description}")
    result = quote_summary.get("result")
    if not isinstance(result, list) or not result:
        raise ValueError("Provider yahoo retornou resultado vazio para o ativo.")
    first = result[0]
    if not isinstance(first, dict):
        raise ValueError("Provider yahoo retornou resultado invalido para o ativo.")
    return cast(dict[str, object], first)


def _parse_market_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _load_brapi_token() -> str:
    token = os.getenv("BRAPI_TOKEN", "").strip()
    if token:
        return token

    repo_root = Path(__file__).resolve().parents[4]
    candidates = (
        repo_root / "token.txt",
        repo_root / ".token_brapi",
        repo_root.parent / "token.txt",
    )
    for candidate in candidates:
        try:
            if not candidate.exists():
                continue
            loaded = candidate.read_text(encoding="utf-8").strip()
            if loaded:
                return loaded
        except OSError:
            continue
    return ""


def _fetch_brapi_quote_summary(instrument: str) -> dict[str, object]:
    symbol = instrument.upper()
    params: dict[str, str] = {"fundamental": "true"}
    brapi_token = _load_brapi_token()
    if brapi_token:
        params["token"] = brapi_token
    url = f"https://brapi.dev/api/quote/{symbol}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "AI-Investment-Advisor-MVP/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code == 401 and not brapi_token:
            raise ValueError(
                "Provider brapi retornou 401 sem token. Configure BRAPI_TOKEN "
                "para cobertura ampla de ativos."
            ) from exc
        raise ValueError(f"Provider brapi retornou HTTP {exc.code}.") from exc
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("Provider brapi retornou payload invalido.")
    results = parsed.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError("Provider brapi retornou resultado vazio para o ativo.")
    first = results[0]
    if not isinstance(first, dict):
        raise ValueError("Provider brapi retornou resultado invalido para o ativo.")

    market_time = _parse_market_time(first.get("regularMarketTime"))
    reference_time = _previous_quarter_end(market_time or utc_now())
    return {
        "defaultKeyStatistics": {
            "trailingPE": {"raw": first.get("priceEarnings")},
            "lastFiscalYearEnd": {"raw": int(reference_time.timestamp())},
        },
        "summaryDetail": {},
        "financialData": {},
        "price": {
            "regularMarketTime": {
                "raw": int((market_time or utc_now()).timestamp()),
            }
        },
    }


def _provider_payload(
    provider_name: str,
    instrument: str,
) -> _ProviderPayload:
    provider = provider_name.lower().strip()
    if provider == YAHOO_PROVIDER_NAME:
        provider_symbol = _yahoo_symbol(instrument)
        return {
            "provider_name": YAHOO_PROVIDER_NAME,
            "provider_symbol": provider_symbol,
            "source_name": YAHOO_SOURCE_NAME,
            "source_type": YAHOO_SOURCE_TYPE,
            "version_prefix": YAHOO_PROVIDER_NAME,
            "raw_payload": _fetch_yahoo_quote_summary(provider_symbol),
        }
    if provider == BRAPI_PROVIDER_NAME:
        symbol = instrument.upper()
        return {
            "provider_name": BRAPI_PROVIDER_NAME,
            "provider_symbol": symbol,
            "source_name": BRAPI_SOURCE_NAME,
            "source_type": BRAPI_SOURCE_TYPE,
            "version_prefix": BRAPI_PROVIDER_NAME,
            "raw_payload": _fetch_brapi_quote_summary(symbol),
        }
    if provider == AUTO_PROVIDER_NAME:
        try:
            return _provider_payload(YAHOO_PROVIDER_NAME, instrument)
        except Exception as yahoo_exc:
            try:
                return _provider_payload(BRAPI_PROVIDER_NAME, instrument)
            except Exception as brapi_exc:
                raise ValueError(
                    "Falha no provider auto (yahoo + brapi): "
                    f"yahoo={yahoo_exc}; brapi={brapi_exc}"
                ) from brapi_exc
    raise ValueError("Provider de fundamentos nao suportado. Use 'auto', 'yahoo' ou 'brapi'.")


def _resolve_requested_instruments(
    db: Session,
    *,
    instruments: list[str] | None,
    only_missing: bool,
    max_instruments: int,
) -> tuple[int, list[str]]:
    if max_instruments <= 0:
        raise ValueError("max_instruments deve ser maior que zero.")
    if max_instruments > MAX_FUNDAMENTALS_SYNC_INSTRUMENTS:
        raise ValueError(
            "max_instruments acima do limite permitido "
            f"({MAX_FUNDAMENTALS_SYNC_INSTRUMENTS})."
        )

    if instruments is None:
        market_rows = list(
            db.scalars(
                select(MarketTick.instrument)
                .distinct()
                .order_by(MarketTick.instrument.asc())
            )
        )
        requested = [
            item.upper()
            for item in market_rows
            if _PREFERRED_EQUITY_TICKER.fullmatch(item.upper()) is not None
        ]
    else:
        requested = list(dict.fromkeys(item.upper() for item in instruments if item.strip()))
    if not requested:
        raise ValueError("Nao ha instrumentos elegiveis para sincronizacao de fundamentos.")

    selected = requested
    if only_missing:
        fundamental_instruments = set(
            db.scalars(select(FundamentalSnapshot.instrument).distinct())
        )
        selected = [item for item in requested if item not in fundamental_instruments]
    selected = selected[:max_instruments]
    return len(requested), selected


def sync_external_fundamentals(
    db: Session,
    *,
    user_id: int,
    provider_name: str,
    instruments: list[str] | None,
    only_missing: bool,
    max_instruments: int,
) -> ExternalFundamentalSyncResult:
    provider = provider_name.lower().strip()
    if provider not in {AUTO_PROVIDER_NAME, YAHOO_PROVIDER_NAME, BRAPI_PROVIDER_NAME}:
        raise ValueError("Provider de fundamentos nao suportado. Use 'auto', 'yahoo' ou 'brapi'.")

    requested_count, selected_instruments = _resolve_requested_instruments(
        db,
        instruments=instruments,
        only_missing=only_missing,
        max_instruments=max_instruments,
    )

    inserted = 0
    duplicates_ignored = 0
    failed = 0
    by_instrument: dict[str, ExternalFundamentalInstrumentResult] = {}
    capture_time = utc_now()

    for instrument in selected_instruments:
        provider_symbol = instrument
        try:
            provider_payload = _provider_payload(provider, instrument)
            provider_symbol = provider_payload["provider_symbol"]
            request, missing_fields, completeness_pct = _normalize_snapshot(
                instrument=instrument,
                provider_symbol=provider_symbol,
                raw_payload=provider_payload["raw_payload"],
                captured_at=capture_time,
                source_name=provider_payload["source_name"],
                source_type=provider_payload["source_type"],
                version_prefix=provider_payload["version_prefix"],
            )

            existing = db.scalar(
                select(FundamentalSnapshot)
                .where(FundamentalSnapshot.instrument == request.instrument.upper())
                .where(FundamentalSnapshot.source_name == request.source_name)
                .where(FundamentalSnapshot.source_type == request.source_type)
                .where(FundamentalSnapshot.reference_time == isoformat(request.reference_time))
                .where(
                    FundamentalSnapshot.availability_time
                    == isoformat(request.availability_time)
                )
                .where(FundamentalSnapshot.version_tag == request.version_tag)
                .order_by(desc(FundamentalSnapshot.id))
                .limit(1)
            )

            snapshot = ingest_fundamentals(db, request)
            if existing is None:
                inserted += 1
                status = "inserted"
            else:
                duplicates_ignored += 1
                status = "duplicate"
            by_instrument[instrument] = {
                "status": status,
                "provider_symbol": provider_symbol,
                "fundamental_id": snapshot.id,
                "reference_time": snapshot.reference_time,
                "availability_time": snapshot.availability_time,
                "completeness_pct": completeness_pct,
                "missing_fields": missing_fields,
                "version_tag": snapshot.version_tag,
                "error": None,
            }
        except Exception as exc:
            failed += 1
            by_instrument[instrument] = {
                "status": "failed",
                "provider_symbol": provider_symbol,
                "fundamental_id": None,
                "reference_time": None,
                "availability_time": None,
                "completeness_pct": 0.0,
                "missing_fields": [],
                "version_tag": None,
                "error": str(exc),
            }

    payload: ExternalFundamentalSyncResult = {
        "source": (
            "Auto (Yahoo->Brapi)"
            if provider == AUTO_PROVIDER_NAME
            else YAHOO_SOURCE_NAME
            if provider == YAHOO_PROVIDER_NAME
            else BRAPI_SOURCE_NAME
        ),
        "provider_name": provider,
        "requested_instruments": requested_count,
        "selected_instruments": selected_instruments,
        "inserted": inserted,
        "duplicates_ignored": duplicates_ignored,
        "failed": failed,
        "by_instrument": by_instrument,
    }
    record_audit_event(
        db,
        "fundamentals.external.sync_completed",
        dict(payload),
        user_id,
    )
    return payload


def fundamentals_coverage_snapshot(
    db: Session,
    *,
    max_rows: int = 200,
    only_missing: bool = False,
) -> FundamentalCoverageSnapshot:
    if max_rows <= 0:
        raise ValueError("max_rows deve ser maior que zero.")
    market_instruments = list(
        db.scalars(select(MarketTick.instrument).distinct().order_by(MarketTick.instrument.asc()))
    )
    market_set = set(market_instruments)

    latest_market_event = {
        row[0]: cast(str, row[1])
        for row in db.execute(
            select(MarketTick.instrument, func.max(MarketTick.event_time)).group_by(
                MarketTick.instrument
            )
        ).all()
    }

    all_fundamentals = list(
        db.scalars(
            select(FundamentalSnapshot).order_by(
                FundamentalSnapshot.instrument.asc(),
                desc(FundamentalSnapshot.availability_time),
                desc(FundamentalSnapshot.id),
            )
        )
    )
    fundamental_instruments = {row.instrument for row in all_fundamentals}
    latest_by_instrument: dict[str, FundamentalSnapshot] = {}
    counts_by_instrument: dict[str, int] = {}
    for fundamental in all_fundamentals:
        counts_by_instrument[fundamental.instrument] = (
            counts_by_instrument.get(fundamental.instrument, 0) + 1
        )
        if fundamental.instrument not in latest_by_instrument:
            latest_by_instrument[fundamental.instrument] = fundamental

    rows: list[FundamentalCoverageRow] = []
    now = utc_now()
    for instrument in sorted(market_set):
        snapshot = latest_by_instrument.get(instrument)
        has_fundamentals = snapshot is not None
        if only_missing and has_fundamentals:
            continue
        staleness_days: int | None = None
        if snapshot is not None:
            availability = _parse_iso_datetime(snapshot.availability_time)
            staleness_days = max(0, (now - availability).days)
        rows.append(
            {
                "instrument": instrument,
                "has_fundamentals": has_fundamentals,
                "snapshot_count": counts_by_instrument.get(instrument, 0),
                "latest_reference_time": snapshot.reference_time if snapshot is not None else None,
                "latest_availability_time": (
                    snapshot.availability_time if snapshot is not None else None
                ),
                "latest_version_tag": snapshot.version_tag if snapshot is not None else None,
                "latest_source_name": snapshot.source_name if snapshot is not None else None,
                "latest_market_event_time": latest_market_event.get(instrument),
                "staleness_days": staleness_days,
            }
        )

    rows.sort(key=lambda item: (item["has_fundamentals"], item["instrument"]))
    limited_rows = rows[:max_rows]
    market_with_fundamentals = len(market_set.intersection(fundamental_instruments))
    total_market = len(market_set)
    coverage_pct = 0.0
    if total_market > 0:
        coverage_pct = round((market_with_fundamentals / total_market) * 100.0, 4)

    return {
        "generated_at": isoformat(now),
        "total_market_instruments": total_market,
        "market_instruments_with_fundamentals": market_with_fundamentals,
        "total_fundamental_instruments": len(fundamental_instruments),
        "missing_fundamental_instruments": max(0, total_market - market_with_fundamentals),
        "coverage_pct": coverage_pct,
        "rows": limited_rows,
    }

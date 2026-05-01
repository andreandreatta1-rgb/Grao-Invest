from __future__ import annotations

import io
import os
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict, cast
from urllib.request import Request, urlopen

from app.models import MarketTick
from app.services.audit import record_audit_event
from app.services.utils import isoformat, utc_now
from sqlalchemy import select
from sqlalchemy.orm import Session

EXPECTED_COTAHIST_LINE_LENGTH = 245
B3_PROVIDER_NAME = "b3-cotahist"
MAX_VALIDATION_PORTFOLIO_SIZE = 40
MAX_UNIVERSE_INSTRUMENTS = 4000
DEFAULT_ALLOWED_BDI_CODES = {"02"}
DEFAULT_ALLOWED_MARKET_TYPES = {"010"}
DEFAULT_SMALL_PORTFOLIO = [
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


class ExternalTickRow(TypedDict):
    instrument: str
    provider: str
    event_time: datetime
    price: float
    volume: int
    currency: str
    source_payload_id: str


class B3FormatValidation(TypedDict):
    expected_line_length: int
    total_quote_rows: int
    matched_rows: int
    invalid_line_rows: int
    price_encoding: str


class B3RangeFormatValidation(TypedDict):
    expected_line_length: int
    matched_rows: int
    invalid_line_rows: int
    price_encoding: str


class B3SyncResult(TypedDict):
    candidates_after_limit: int
    inserted: int
    duplicates_ignored: int
    ingested_by_instrument: dict[str, int]


class B3RangeSyncResult(TypedDict):
    inserted: int
    duplicates_ignored: int
    ingested_by_instrument: dict[str, int]


class B3SyncPayload(TypedDict):
    source: str
    provider: str
    year: int
    portfolio: list[str]
    max_days_per_instrument: int
    format_validation: B3FormatValidation
    sync_result: B3SyncResult
    sync_scope: NotRequired[str]
    filters: NotRequired[dict[str, object]]
    discovered_universe_size: NotRequired[int]


class B3SyncRangePayload(TypedDict):
    source: str
    provider: str
    years: list[int]
    portfolio: list[str]
    max_days_per_instrument_per_year: int
    format_validation: B3RangeFormatValidation
    sync_result: B3RangeSyncResult
    yearly_breakdown: list[B3SyncPayload]
    sync_scope: NotRequired[str]
    filters: NotRequired[dict[str, object]]
    discovered_universe_size: NotRequired[int]


def cotahist_url_for_year(year: int) -> str:
    return f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"


def _load_local_cotahist_zip(year: int) -> bytes | None:
    filename = f"COTAHIST_A{year}.ZIP"
    repo_root = Path(__file__).resolve().parents[4]
    candidate_roots = [repo_root, repo_root.parent]
    for root in candidate_roots:
        candidate = root / filename
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_bytes()
        except OSError:
            continue
    return None


def download_cotahist_zip(year: int, timeout_seconds: int = 90) -> bytes:
    local_payload = _load_local_cotahist_zip(year)
    if local_payload is not None:
        return local_payload

    url = cotahist_url_for_year(year)
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (AI-Investment-Advisor-MVP)"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
        return cast(bytes, payload)
    except Exception:
        return _download_cotahist_zip_with_powershell(url, timeout_seconds)


def _download_cotahist_zip_with_powershell(url: str, timeout_seconds: int) -> bytes:
    if os.name != "nt":
        raise ValueError("Fallback PowerShell disponivel apenas em ambiente Windows.")
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "cotahist.zip")
        script = (
            "$ProgressPreference='SilentlyContinue'; "
            f"Invoke-WebRequest -Uri '{url}' -OutFile '{output_path}' -TimeoutSec {timeout_seconds}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not os.path.exists(output_path):
            stderr = result.stderr.strip()
            raise ValueError(f"Falha no download via PowerShell: {stderr}")
        with open(output_path, "rb") as file:
            return file.read()


def _parse_price_to_float(raw_value: str) -> float:
    return int(raw_value) / 100


def _parse_cotahist_event_time(raw_date: str) -> datetime:
    return datetime.strptime(raw_date, "%Y%m%d").replace(tzinfo=UTC)


def _open_cotahist_text(zip_payload: bytes) -> io.TextIOWrapper:
    archive = zipfile.ZipFile(io.BytesIO(zip_payload))
    candidates = [
        name
        for name in archive.namelist()
        if name.upper().startswith("COTAHIST_") and name.upper().endswith(".TXT")
    ]
    if not candidates:
        archive.close()
        raise ValueError("Arquivo ZIP da B3 nao contem COTAHIST em formato TXT.")
    raw_stream = archive.open(candidates[0], "r")
    text_stream = io.TextIOWrapper(raw_stream, encoding="latin1")
    text_stream._archive = archive  # type: ignore[attr-defined]
    text_stream._raw_stream = raw_stream  # type: ignore[attr-defined]
    return text_stream


def _close_cotahist_text(stream: io.TextIOWrapper) -> None:
    raw_stream = getattr(stream, "_raw_stream", None)
    archive = getattr(stream, "_archive", None)
    stream.close()
    if raw_stream is not None:
        raw_stream.close()
    if archive is not None:
        archive.close()


def _is_equity_spot_quote(
    *,
    instrument: str,
    bdi_code: str,
    market_type: str,
    allowed_bdi_codes: set[str],
    allowed_market_types: set[str],
) -> bool:
    if not instrument or len(instrument) > 12:
        return False
    if bdi_code not in allowed_bdi_codes:
        return False
    if market_type not in allowed_market_types:
        return False
    has_letter = any(char.isalpha() for char in instrument)
    has_digit = any(char.isdigit() for char in instrument)
    return has_letter and has_digit


def sync_b3_cotahist_portfolio(
    db: Session,
    *,
    user_id: int,
    year: int,
    instruments: list[str] | None,
    max_days_per_instrument: int,
    include_all_equities: bool = False,
    max_instruments: int | None = None,
    allowed_bdi_codes: set[str] | None = None,
    allowed_market_types: set[str] | None = None,
) -> B3SyncPayload:
    if max_days_per_instrument <= 0:
        raise ValueError("max_days_per_instrument deve ser maior que zero.")
    bdi_codes = allowed_bdi_codes or DEFAULT_ALLOWED_BDI_CODES
    market_types = allowed_market_types or DEFAULT_ALLOWED_MARKET_TYPES
    selected_set: set[str]
    if include_all_equities:
        selected_set = set()
        if max_instruments is not None and max_instruments <= 0:
            raise ValueError("max_instruments deve ser maior que zero quando informado.")
        if max_instruments is not None and max_instruments > MAX_UNIVERSE_INSTRUMENTS:
            raise ValueError(
                f"max_instruments limitado a {MAX_UNIVERSE_INSTRUMENTS} instrumentos."
            )
    else:
        selected_instruments = (
            [item.upper() for item in instruments if item.strip()]
            if instruments
            else DEFAULT_SMALL_PORTFOLIO
        )
        selected_set = set(selected_instruments)
        if not selected_set:
            raise ValueError("Informe ao menos um instrumento para sincronizacao.")
        if len(selected_set) > MAX_VALIDATION_PORTFOLIO_SIZE:
            raise ValueError(
                f"Carteira de validacao limitada a {MAX_VALIDATION_PORTFOLIO_SIZE} ativos."
            )

    try:
        zip_payload = download_cotahist_zip(year)
    except Exception as exc:
        raise ValueError(f"Falha ao baixar COTAHIST da B3 para {year}: {exc}") from exc

    rows_by_instrument: dict[str, list[ExternalTickRow]] = (
        {instrument: [] for instrument in selected_set}
        if not include_all_equities
        else {}
    )
    total_quote_rows = 0
    matched_rows = 0
    invalid_line_rows = 0
    text_stream = _open_cotahist_text(zip_payload)
    try:
        for raw_line in text_stream:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if line.startswith("00") or line.startswith("99"):
                continue
            if not line.startswith("01"):
                continue
            total_quote_rows += 1
            if len(line) < EXPECTED_COTAHIST_LINE_LENGTH:
                invalid_line_rows += 1
                continue

            instrument = line[12:24].strip().upper()
            bdi_code = line[10:12]
            market_type = line[24:27]
            if include_all_equities:
                if not _is_equity_spot_quote(
                    instrument=instrument,
                    bdi_code=bdi_code,
                    market_type=market_type,
                    allowed_bdi_codes=bdi_codes,
                    allowed_market_types=market_types,
                ):
                    continue
                if instrument not in rows_by_instrument:
                    if max_instruments is not None and len(rows_by_instrument) >= max_instruments:
                        continue
                    rows_by_instrument[instrument] = []
            elif instrument not in selected_set:
                continue

            close_raw = line[108:121]
            quantity_raw = line[152:170]
            try:
                close_price = _parse_price_to_float(close_raw)
                quantity = int(quantity_raw)
                event_time = _parse_cotahist_event_time(line[2:10])
            except ValueError:
                invalid_line_rows += 1
                continue
            if close_price <= 0:
                invalid_line_rows += 1
                continue

            matched_rows += 1
            source_payload_id = f"b3-cotahist:{line[2:10]}:{instrument}"
            rows_by_instrument[instrument].append(
                ExternalTickRow(
                    instrument=instrument,
                    provider=B3_PROVIDER_NAME,
                    event_time=event_time,
                    price=round(close_price, 4),
                    volume=quantity,
                    currency="BRL",
                    source_payload_id=source_payload_id,
                )
            )
    finally:
        _close_cotahist_text(text_stream)
    if include_all_equities:
        selected_set = set(rows_by_instrument)
        if not selected_set:
            raise ValueError(
                "Nenhum instrumento elegivel encontrado no filtro "
                "do universo para o ano solicitado."
            )

    limited_rows: list[ExternalTickRow] = []
    for instrument, rows in rows_by_instrument.items():
        rows.sort(key=lambda item: str(item["event_time"]))
        selected_rows = rows[-max_days_per_instrument:]
        rows_by_instrument[instrument] = selected_rows
        limited_rows.extend(selected_rows)
    limited_rows.sort(key=lambda item: (str(item["event_time"]), str(item["instrument"])))

    inserted = 0
    duplicates_ignored = 0
    ingested_by_instrument = {instrument: 0 for instrument in selected_set}
    for row in limited_rows:
        existing = db.scalar(
            select(MarketTick)
            .where(MarketTick.instrument == row["instrument"])
            .where(MarketTick.provider == B3_PROVIDER_NAME)
            .where(MarketTick.source_payload_id == row["source_payload_id"])
            .order_by(MarketTick.id.desc())
            .limit(1)
        )
        if existing is not None:
            duplicates_ignored += 1
            continue
        tick = MarketTick(
            instrument=row["instrument"],
            provider=B3_PROVIDER_NAME,
            event_time=isoformat(row["event_time"]),
            ingest_time=isoformat(utc_now()),
            price=row["price"],
            volume=row["volume"],
            currency=row["currency"],
            source_payload_id=row["source_payload_id"],
        )
        db.add(tick)
        inserted += 1
        ingested_by_instrument[tick.instrument] = ingested_by_instrument.get(
            tick.instrument,
            0,
        ) + 1
    db.commit()

    response: B3SyncPayload = {
        "source": "B3.COTAHIST",
        "provider": B3_PROVIDER_NAME,
        "year": year,
        "portfolio": sorted(selected_set),
        "max_days_per_instrument": max_days_per_instrument,
        "format_validation": {
            "expected_line_length": EXPECTED_COTAHIST_LINE_LENGTH,
            "total_quote_rows": total_quote_rows,
            "matched_rows": matched_rows,
            "invalid_line_rows": invalid_line_rows,
            "price_encoding": "inteiro com 2 casas decimais (valor/100)",
        },
        "sync_result": {
            "candidates_after_limit": len(limited_rows),
            "inserted": inserted,
            "duplicates_ignored": duplicates_ignored,
            "ingested_by_instrument": ingested_by_instrument,
        },
    }
    if include_all_equities:
        response["sync_scope"] = "universe"
        response["discovered_universe_size"] = len(selected_set)
        response["filters"] = {
            "allowed_bdi_codes": sorted(bdi_codes),
            "allowed_market_types": sorted(market_types),
            "max_instruments": max_instruments,
        }
    record_audit_event(
        db,
        (
            "market.external.b3.sync_universe_completed"
            if include_all_equities
            else "market.external.b3.sync_completed"
        ),
        {
            "year": year,
            "portfolio": sorted(selected_set),
            "inserted": inserted,
            "duplicates_ignored": duplicates_ignored,
            "sync_scope": response.get("sync_scope", "portfolio"),
        },
        user_id,
    )
    return response


def sync_b3_cotahist_portfolio_range(
    db: Session,
    *,
    user_id: int,
    start_year: int,
    end_year: int,
    instruments: list[str] | None,
    max_days_per_instrument_per_year: int,
    include_all_equities: bool = False,
    max_instruments: int | None = None,
    allowed_bdi_codes: set[str] | None = None,
    allowed_market_types: set[str] | None = None,
) -> B3SyncRangePayload:
    if start_year > end_year:
        raise ValueError("start_year nao pode ser maior que end_year.")
    if max_days_per_instrument_per_year <= 0:
        raise ValueError("max_days_per_instrument_per_year deve ser maior que zero.")
    if (end_year - start_year) > 10:
        raise ValueError("Faixa de anos limitada a no maximo 11 anos por execucao.")
    yearly_results: list[B3SyncPayload] = []
    aggregate_inserted = 0
    aggregate_duplicates = 0
    aggregate_matched = 0
    aggregate_invalid = 0
    years = list(range(start_year, end_year + 1))
    portfolio_set: set[str] = set()
    per_instrument_totals: dict[str, int] = {}

    for year in years:
        result = sync_b3_cotahist_portfolio(
            db,
            user_id=user_id,
            year=year,
            instruments=instruments,
            max_days_per_instrument=max_days_per_instrument_per_year,
            include_all_equities=include_all_equities,
            max_instruments=max_instruments,
            allowed_bdi_codes=allowed_bdi_codes,
            allowed_market_types=allowed_market_types,
        )
        yearly_results.append(result)
        aggregate_inserted += int(result["sync_result"]["inserted"])
        aggregate_duplicates += int(result["sync_result"]["duplicates_ignored"])
        aggregate_matched += int(result["format_validation"]["matched_rows"])
        aggregate_invalid += int(result["format_validation"]["invalid_line_rows"])
        portfolio_set.update(result["portfolio"])
        by_instrument = result["sync_result"]["ingested_by_instrument"]
        for instrument, qty in by_instrument.items():
            per_instrument_totals[instrument] = per_instrument_totals.get(instrument, 0) + int(qty)

    payload: B3SyncRangePayload = {
        "source": "B3.COTAHIST",
        "provider": B3_PROVIDER_NAME,
        "years": years,
        "portfolio": sorted(portfolio_set),
        "max_days_per_instrument_per_year": max_days_per_instrument_per_year,
        "format_validation": {
            "expected_line_length": EXPECTED_COTAHIST_LINE_LENGTH,
            "matched_rows": aggregate_matched,
            "invalid_line_rows": aggregate_invalid,
            "price_encoding": "inteiro com 2 casas decimais (valor/100)",
        },
        "sync_result": {
            "inserted": aggregate_inserted,
            "duplicates_ignored": aggregate_duplicates,
            "ingested_by_instrument": per_instrument_totals,
        },
        "yearly_breakdown": yearly_results,
    }
    if include_all_equities:
        discovered_size = len(portfolio_set)
        payload["sync_scope"] = "universe"
        payload["discovered_universe_size"] = discovered_size
        payload["filters"] = {
            "allowed_bdi_codes": sorted(allowed_bdi_codes or DEFAULT_ALLOWED_BDI_CODES),
            "allowed_market_types": sorted(allowed_market_types or DEFAULT_ALLOWED_MARKET_TYPES),
            "max_instruments": max_instruments,
        }
    record_audit_event(
        db,
        (
            "market.external.b3.sync_universe_range_completed"
            if include_all_equities
            else "market.external.b3.sync_range_completed"
        ),
        {
            "years": years,
            "portfolio": sorted(portfolio_set),
            "inserted": aggregate_inserted,
            "duplicates_ignored": aggregate_duplicates,
            "sync_scope": payload.get("sync_scope", "portfolio"),
        },
        user_id,
    )
    return payload


def sync_b3_cotahist_universe_range(
    db: Session,
    *,
    user_id: int,
    start_year: int,
    end_year: int,
    max_days_per_instrument_per_year: int,
    max_instruments: int | None = None,
    allowed_bdi_codes: list[str] | None = None,
    allowed_market_types: list[str] | None = None,
) -> B3SyncRangePayload:
    bdi_codes = (
        {code.strip() for code in allowed_bdi_codes if code.strip()}
        if allowed_bdi_codes
        else DEFAULT_ALLOWED_BDI_CODES
    )
    market_types = (
        {code.strip() for code in allowed_market_types if code.strip()}
        if allowed_market_types
        else DEFAULT_ALLOWED_MARKET_TYPES
    )
    if not bdi_codes:
        raise ValueError("allowed_bdi_codes nao pode ser vazio.")
    if not market_types:
        raise ValueError("allowed_market_types nao pode ser vazio.")
    return sync_b3_cotahist_portfolio_range(
        db,
        user_id=user_id,
        start_year=start_year,
        end_year=end_year,
        instruments=None,
        max_days_per_instrument_per_year=max_days_per_instrument_per_year,
        include_all_equities=True,
        max_instruments=max_instruments,
        allowed_bdi_codes=bdi_codes,
        allowed_market_types=market_types,
    )

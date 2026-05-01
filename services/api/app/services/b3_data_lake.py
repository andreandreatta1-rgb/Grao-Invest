from __future__ import annotations

import csv
import json
import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from app.services.b3_external import DEFAULT_SMALL_PORTFOLIO, EXPECTED_COTAHIST_LINE_LENGTH
from app.services.utils import isoformat, utc_now

_COTAHIST_PRIORITY_BY_GRANULARITY = {
    "annual": 1,
    "monthly": 2,
    "daily": 3,
}

_COTAHIST_BRONZE_FIELDS = [
    "trade_date",
    "instrument",
    "bdi_code",
    "market_type",
    "company_name",
    "specification_code",
    "currency",
    "open_price",
    "high_price",
    "low_price",
    "average_price",
    "close_price",
    "best_bid_price",
    "best_ask_price",
    "trade_count",
    "trade_quantity",
    "trade_volume",
    "vwap",
    "isin",
    "distribution_id",
    "source_file",
    "source_granularity",
]

_COTAHIST_SILVER_FIELDS = [
    "trade_date",
    "instrument",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "average_price",
    "trade_count",
    "trade_quantity",
    "trade_volume",
    "vwap",
    "source_file",
    "source_granularity",
]

_CAMBIO_RETROATIVO_FIELDS = [
    "currency",
    "trade_date",
    "settlement_date",
    "min_rate",
    "max_rate",
    "close_rate",
    "tcam_rate",
    "contracted_usd",
    "contracted_brl",
    "settled_usd",
    "settled_brl",
    "trade_count",
    "stress_scenario_pct",
    "opening_rate",
    "source_file",
]

_CAMBIO_POR_CANAL_FIELDS = [
    "trade_date",
    "settlement_days",
    "contracted_usd_otc",
    "contracted_brl_otc",
    "contracted_usd_electronic",
    "contracted_brl_electronic",
    "contracted_usd_total",
    "contracted_brl_total",
    "trade_count_otc",
    "trade_count_electronic",
    "trade_count_total",
    "min_rate_otc",
    "avg_rate_otc",
    "max_rate_otc",
    "min_rate_electronic",
    "avg_rate_electronic",
    "max_rate_electronic",
    "source_file",
]

_CAMBIO_MEDIA_FIELDS = [
    "reference_month",
    "contracted_usd_avg_electronic",
    "contracted_brl_avg_electronic",
    "contracted_usd_avg_otc",
    "contracted_brl_avg_otc",
    "contracted_usd_avg_total",
    "contracted_brl_avg_total",
    "source_file",
]

_CAMBIO_PARAMETROS_FIELDS = [
    "trade_date",
    "settlement_date",
    "opening_rate",
    "stress_scenario_pct",
    "source_file",
]

_CAMBIO_API_RETROATIVO_FIELDS = [
    "trade_date",
    "settlement_date",
    "last_rate",
    "settled_usd",
    "settled_brl",
    "contracted_usd_total",
    "contracted_brl_total",
    "trade_count_total",
    "otc_rate_avg",
    "otc_rate_min",
    "otc_rate_max",
    "otc_contracted_usd",
    "otc_contracted_brl",
    "source_file",
]

_CAMBIO_API_RESUMOS_FIELDS = [
    "hour_bucket",
    "settlement_date",
    "trade_count_total",
    "rate_avg",
    "rate_min",
    "rate_max",
    "contracted_brl_total",
    "contracted_usd_total",
    "source_file",
]

_CAMBIO_API_PARAMETROS_FIELDS = [
    "trade_date",
    "settlement_date",
    "opening_rate",
    "stress_scenario_pct",
    "source_file",
]

_RENDA_FIXA_FIELDS = [
    "dataset",
    "trade_date",
    "n_operations",
    "volume_brl",
    "source_file",
]

_PESQUISA_PREGAO_FIELDS = [
    "layout_code",
    "file_name",
    "size_bytes",
    "source_file",
]


def run_b3_bronze_silver_pipeline(
    *,
    source_root: Path,
    output_root: Path,
    instruments: list[str] | None = None,
    include_all_instruments: bool = False,
    max_rows_per_cotahist_file: int | None = None,
    pesquisa_root: Path | None = None,
) -> dict[str, Any]:
    instrument_set: set[str]
    if include_all_instruments:
        instrument_set = set()
    else:
        selected = instruments or DEFAULT_SMALL_PORTFOLIO
        instrument_set = {item.strip().upper() for item in selected if item.strip()}
        if not instrument_set:
            raise ValueError("Informe ao menos um instrumento ou ative include_all_instruments.")

    output_root.mkdir(parents=True, exist_ok=True)
    bronze_root = output_root / "bronze"
    silver_root = output_root / "silver"
    bronze_root.mkdir(parents=True, exist_ok=True)
    silver_root.mkdir(parents=True, exist_ok=True)

    cotahist_summary = _process_cotahist(
        source_root=source_root,
        bronze_root=bronze_root,
        silver_root=silver_root,
        instrument_filter=instrument_set if not include_all_instruments else None,
        max_rows_per_file=max_rows_per_cotahist_file,
    )
    cambio_summary = _process_cambio(
        source_root=source_root,
        bronze_root=bronze_root,
        silver_root=silver_root,
    )
    renda_fixa_summary = _process_renda_fixa(
        source_root=source_root,
        bronze_root=bronze_root,
        silver_root=silver_root,
    )
    pesquisa_summary = _process_pesquisa_pregao_manifest(
        pesquisa_root=pesquisa_root,
        bronze_root=bronze_root,
    )

    return {
        "pipeline": {
            "source_root": str(source_root),
            "output_root": str(output_root),
            "run_at": isoformat(utc_now()),
            "include_all_instruments": include_all_instruments,
            "selected_instruments": sorted(instrument_set),
            "max_rows_per_cotahist_file": max_rows_per_cotahist_file,
        },
        "datasets": {
            "cotahist": cotahist_summary,
            "cambio": cambio_summary,
            "renda_fixa": renda_fixa_summary,
            "pesquisa_pregao": pesquisa_summary,
        },
    }


def _process_cotahist(
    *,
    source_root: Path,
    bronze_root: Path,
    silver_root: Path,
    instrument_filter: set[str] | None,
    max_rows_per_file: int | None,
) -> dict[str, Any]:
    extracted_root = source_root / "extracted"
    files = sorted(extracted_root.rglob("COTAHIST_*.TXT")) if extracted_root.exists() else []

    bronze_dir = bronze_root / "cotahist"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    silver_path = silver_root / "market_daily.csv"
    stage_db_path = silver_root / "_cotahist_stage.sqlite3"
    if stage_db_path.exists():
        stage_db_path.unlink()

    conn = sqlite3.connect(stage_db_path)
    try:
        _init_cotahist_stage(conn)
        processed_files: list[dict[str, Any]] = []
        total_rows_bronze = 0
        total_rows_matched = 0
        total_invalid_rows = 0
        total_filtered_out = 0

        for source_file in files:
            source_label = str(source_file.relative_to(source_root).as_posix())
            source_granularity = _cotahist_granularity(source_file.name)
            source_priority = _COTAHIST_PRIORITY_BY_GRANULARITY[source_granularity]
            bronze_file = bronze_dir / f"{_slugify(source_label)}.csv"

            source_rows = 0
            source_matched = 0
            source_invalid = 0
            source_filtered_out = 0

            with (
                source_file.open("r", encoding="latin1", newline="") as input_file,
                bronze_file.open("w", encoding="utf-8", newline="") as output_file,
            ):
                writer = csv.DictWriter(output_file, fieldnames=_COTAHIST_BRONZE_FIELDS)
                writer.writeheader()
                for raw_line in input_file:
                    line = raw_line.rstrip("\n")
                    if not line or line.startswith("00") or line.startswith("99"):
                        continue
                    source_rows += 1
                    parsed = _parse_cotahist_line(line=line)
                    if parsed is None:
                        source_invalid += 1
                        continue
                    instrument = cast(str, parsed["instrument"])
                    if instrument_filter is not None and instrument not in instrument_filter:
                        source_filtered_out += 1
                        continue
                    source_matched += 1
                    parsed["source_file"] = source_label
                    parsed["source_granularity"] = source_granularity
                    writer.writerow(parsed)
                    _upsert_cotahist_silver_row(
                        conn,
                        row=parsed,
                        source_priority=source_priority,
                    )
                    if max_rows_per_file is not None and source_matched >= max_rows_per_file:
                        break

            processed_files.append(
                {
                    "source_file": source_label,
                    "bronze_file": str(bronze_file),
                    "source_granularity": source_granularity,
                    "rows_seen": source_rows,
                    "rows_matched": source_matched,
                    "rows_invalid": source_invalid,
                    "rows_filtered_out": source_filtered_out,
                }
            )
            total_rows_bronze += source_rows
            total_rows_matched += source_matched
            total_invalid_rows += source_invalid
            total_filtered_out += source_filtered_out

        silver_rows = _export_cotahist_silver(conn, silver_path)
    finally:
        conn.close()
        if stage_db_path.exists():
            stage_db_path.unlink()

    return {
        "input_files": len(files),
        "rows_seen": total_rows_bronze,
        "rows_matched": total_rows_matched,
        "rows_invalid": total_invalid_rows,
        "rows_filtered_out": total_filtered_out,
        "silver_rows": silver_rows,
        "silver_file": str(silver_path),
        "processed_files": processed_files,
    }


def _init_cotahist_stage(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cotahist_silver (
            trade_date TEXT NOT NULL,
            instrument TEXT NOT NULL,
            open_price REAL NOT NULL,
            high_price REAL NOT NULL,
            low_price REAL NOT NULL,
            close_price REAL NOT NULL,
            average_price REAL NOT NULL,
            trade_count INTEGER NOT NULL,
            trade_quantity INTEGER NOT NULL,
            trade_volume REAL NOT NULL,
            vwap REAL NOT NULL,
            source_file TEXT NOT NULL,
            source_granularity TEXT NOT NULL,
            priority INTEGER NOT NULL,
            PRIMARY KEY (trade_date, instrument)
        )
        """
    )
    conn.commit()


def _upsert_cotahist_silver_row(
    conn: sqlite3.Connection,
    *,
    row: dict[str, Any],
    source_priority: int,
) -> None:
    conn.execute(
        """
        INSERT INTO cotahist_silver (
            trade_date,
            instrument,
            open_price,
            high_price,
            low_price,
            close_price,
            average_price,
            trade_count,
            trade_quantity,
            trade_volume,
            vwap,
            source_file,
            source_granularity,
            priority
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, instrument) DO UPDATE SET
            open_price = excluded.open_price,
            high_price = excluded.high_price,
            low_price = excluded.low_price,
            close_price = excluded.close_price,
            average_price = excluded.average_price,
            trade_count = excluded.trade_count,
            trade_quantity = excluded.trade_quantity,
            trade_volume = excluded.trade_volume,
            vwap = excluded.vwap,
            source_file = excluded.source_file,
            source_granularity = excluded.source_granularity,
            priority = excluded.priority
        WHERE excluded.priority >= cotahist_silver.priority
        """,
        (
            row["trade_date"],
            row["instrument"],
            row["open_price"],
            row["high_price"],
            row["low_price"],
            row["close_price"],
            row["average_price"],
            row["trade_count"],
            row["trade_quantity"],
            row["trade_volume"],
            row["vwap"],
            row["source_file"],
            row["source_granularity"],
            source_priority,
        ),
    )


def _export_cotahist_silver(conn: sqlite3.Connection, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = conn.execute(
        """
        SELECT
            trade_date,
            instrument,
            open_price,
            high_price,
            low_price,
            close_price,
            average_price,
            trade_count,
            trade_quantity,
            trade_volume,
            vwap,
            source_file,
            source_granularity
        FROM cotahist_silver
        ORDER BY trade_date, instrument
        """
    )
    rows = cursor.fetchall()
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(_COTAHIST_SILVER_FIELDS)
        for row in rows:
            writer.writerow(row)
    return len(rows)


def _parse_cotahist_line(*, line: str) -> dict[str, Any] | None:
    if not line.startswith("01") or len(line) < EXPECTED_COTAHIST_LINE_LENGTH:
        return None

    trade_date = _parse_date_yyyymmdd(line[2:10])
    if trade_date is None:
        return None
    instrument = line[12:24].strip().upper()
    if not instrument:
        return None

    open_price = _parse_cotahist_scaled_int(line[56:69])
    high_price = _parse_cotahist_scaled_int(line[69:82])
    low_price = _parse_cotahist_scaled_int(line[82:95])
    average_price = _parse_cotahist_scaled_int(line[95:108])
    close_price = _parse_cotahist_scaled_int(line[108:121])
    best_bid_price = _parse_cotahist_scaled_int(line[121:134])
    best_ask_price = _parse_cotahist_scaled_int(line[134:147])
    trade_count = _parse_int_raw_digits(line[147:152])
    trade_quantity = _parse_int_raw_digits(line[152:170])
    trade_volume = _parse_cotahist_scaled_int(line[170:188])

    numeric_values = (
        open_price,
        high_price,
        low_price,
        average_price,
        close_price,
        best_bid_price,
        best_ask_price,
        trade_volume,
    )
    if any(value is None for value in numeric_values):
        return None
    if trade_count is None or trade_quantity is None:
        return None

    vwap = (
        round(cast(float, trade_volume) / trade_quantity, 6)
        if trade_quantity > 0
        else cast(float, close_price)
    )

    return {
        "trade_date": trade_date,
        "instrument": instrument,
        "bdi_code": line[10:12].strip(),
        "market_type": line[24:27].strip(),
        "company_name": line[27:39].strip(),
        "specification_code": line[39:49].strip(),
        "currency": line[52:56].strip(),
        "open_price": cast(float, open_price),
        "high_price": cast(float, high_price),
        "low_price": cast(float, low_price),
        "average_price": cast(float, average_price),
        "close_price": cast(float, close_price),
        "best_bid_price": cast(float, best_bid_price),
        "best_ask_price": cast(float, best_ask_price),
        "trade_count": trade_count,
        "trade_quantity": trade_quantity,
        "trade_volume": cast(float, trade_volume),
        "vwap": vwap,
        "isin": line[230:242].strip(),
        "distribution_id": line[242:245].strip(),
    }


def _process_cambio(
    *,
    source_root: Path,
    bronze_root: Path,
    silver_root: Path,
) -> dict[str, Any]:
    extracted_root = source_root / "cambio" / "extracted"
    api_root = source_root / "cambio" / "api_snapshots"
    files = sorted(extracted_root.rglob("*.txt")) if extracted_root.exists() else []

    bronze_dir = bronze_root / "cambio"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    silver_rows: dict[str, list[dict[str, Any]]] = {
        "cambio_retroativo_por_dia.csv": [],
        "cambio_dados_por_canal.csv": [],
        "cambio_volumes_medias.csv": [],
        "cambio_parametros_abertura.csv": [],
        "cambio_api_retroativo.csv": [],
        "cambio_api_resumos.csv": [],
        "cambio_api_parametros.csv": [],
    }

    processed_files: list[dict[str, Any]] = []
    total_rows = 0

    for source_file in files:
        source_label = str(source_file.relative_to(source_root).as_posix())
        source_slug = _slugify(source_file.stem)
        bronze_file = bronze_dir / f"{_slugify(source_label)}.csv"

        with source_file.open("r", encoding="latin1", newline="") as raw_file:
            reader = csv.reader(raw_file, delimiter=";")
            try:
                header = next(reader)
            except StopIteration:
                continue

            raw_rows: list[list[str]] = []
            for row in reader:
                if _is_row_empty(row):
                    continue
                raw_rows.append([item.strip() for item in row])

            max_cols = max((len(row) for row in raw_rows), default=0)
            normalized_header = _normalize_header(
                header=header,
                min_columns=max_cols,
            )
            with bronze_file.open("w", encoding="utf-8", newline="") as out_file:
                writer = csv.DictWriter(
                    out_file,
                    fieldnames=[*normalized_header, "source_file"],
                )
                writer.writeheader()

                row_count = 0
                for row in raw_rows:
                    clean_row = _normalize_row(row, len(normalized_header))
                    row_count += 1
                    row_payload = {
                        key: clean_row[idx] for idx, key in enumerate(normalized_header)
                    }
                    row_payload["source_file"] = source_label
                    writer.writerow(row_payload)

                    _append_cambio_silver_rows(
                        silver_rows=silver_rows,
                        source_slug=source_slug,
                        source_file=source_label,
                        row=clean_row,
                    )

        processed_files.append(
            {
                "source_file": source_label,
                "bronze_file": str(bronze_file),
                "rows": row_count,
            }
        )
        total_rows += row_count

    api_files = sorted(api_root.glob("*.json")) if api_root.exists() else []
    api_rows = _append_cambio_api_rows(
        silver_rows=silver_rows,
        api_files=api_files,
        source_root=source_root,
    )

    outputs: list[dict[str, Any]] = []
    for file_name, rows in silver_rows.items():
        fields = _silver_fields_for_cambio(file_name)
        output_path = silver_root / file_name
        _write_rows_to_csv(output_path=output_path, rows=rows, fieldnames=fields)
        outputs.append(
            {
                "silver_file": str(output_path),
                "rows": len(rows),
            }
        )

    return {
        "input_files": len(files),
        "api_files": len(api_files),
        "rows_seen": total_rows,
        "api_rows": api_rows,
        "processed_files": processed_files,
        "silver_outputs": outputs,
    }


def _append_cambio_silver_rows(
    *,
    silver_rows: dict[str, list[dict[str, Any]]],
    source_slug: str,
    source_file: str,
    row: list[str],
) -> None:
    if "retroativo_por_dia" in source_slug and len(row) >= 14:
        silver_rows["cambio_retroativo_por_dia.csv"].append(
            {
                "currency": row[0].strip().upper(),
                "trade_date": _parse_date_yyyymmdd(row[1]) or "",
                "settlement_date": _parse_date_yyyymmdd(row[2]) or "",
                "min_rate": _parse_locale_number(row[3]),
                "max_rate": _parse_locale_number(row[4]),
                "close_rate": _parse_locale_number(row[5]),
                "tcam_rate": _parse_locale_number(row[6]),
                "contracted_usd": _parse_locale_number(row[7]),
                "contracted_brl": _parse_locale_number(row[8]),
                "settled_usd": _parse_locale_number(row[9]),
                "settled_brl": _parse_locale_number(row[10]),
                "trade_count": _parse_locale_int(row[11]),
                "stress_scenario_pct": _parse_locale_number(row[12]),
                "opening_rate": _parse_locale_number(row[13]),
                "source_file": source_file,
            }
        )
        return

    if "dados_por_canal_de_negociacao" in source_slug and len(row) >= 17:
        silver_rows["cambio_dados_por_canal.csv"].append(
            {
                "trade_date": _parse_date_yyyymmdd(row[0]) or "",
                "settlement_days": _parse_locale_int(row[1]),
                "contracted_usd_otc": _parse_locale_number(row[2]),
                "contracted_brl_otc": _parse_locale_number(row[3]),
                "contracted_usd_electronic": _parse_locale_number(row[4]),
                "contracted_brl_electronic": _parse_locale_number(row[5]),
                "contracted_usd_total": _parse_locale_number(row[6]),
                "contracted_brl_total": _parse_locale_number(row[7]),
                "trade_count_otc": _parse_locale_int(row[8]),
                "trade_count_electronic": _parse_locale_int(row[9]),
                "trade_count_total": _parse_locale_int(row[10]),
                "min_rate_otc": _parse_locale_number(row[11]),
                "avg_rate_otc": _parse_locale_number(row[12]),
                "max_rate_otc": _parse_locale_number(row[13]),
                "min_rate_electronic": _parse_locale_number(row[14]),
                "avg_rate_electronic": _parse_locale_number(row[15]),
                "max_rate_electronic": _parse_locale_number(row[16]),
                "source_file": source_file,
            }
        )
        return

    if "volumes_contratados_medias_diarias" in source_slug and len(row) >= 7:
        silver_rows["cambio_volumes_medias.csv"].append(
            {
                "reference_month": _parse_month_abbrev(row[0]) or row[0].strip(),
                "contracted_usd_avg_electronic": _parse_locale_number(row[1]),
                "contracted_brl_avg_electronic": _parse_locale_number(row[2]),
                "contracted_usd_avg_otc": _parse_locale_number(row[3]),
                "contracted_brl_avg_otc": _parse_locale_number(row[4]),
                "contracted_usd_avg_total": _parse_locale_number(row[5]),
                "contracted_brl_avg_total": _parse_locale_number(row[6]),
                "source_file": source_file,
            }
        )
        return

    if "parametros_de_abertura" in source_slug and len(row) >= 4:
        silver_rows["cambio_parametros_abertura.csv"].append(
            {
                "trade_date": _parse_date_yyyymmdd(row[0]) or "",
                "settlement_date": _parse_date_yyyymmdd(row[1]) or "",
                "opening_rate": _parse_locale_number(row[2]),
                "stress_scenario_pct": _parse_locale_number(row[3]),
                "source_file": source_file,
            }
        )


def _append_cambio_api_rows(
    *,
    silver_rows: dict[str, list[dict[str, Any]]],
    api_files: list[Path],
    source_root: Path,
) -> int:
    total_rows = 0
    for api_file in api_files:
        source_file = str(api_file.relative_to(source_root).as_posix())
        try:
            payload = json.loads(api_file.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        name = api_file.name.lower()
        if "retroativo_getlist" in name:
            results = payload.get("results")
            if isinstance(results, list):
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    transactions = result.get("transactions")
                    if not isinstance(transactions, list):
                        continue
                    for tx in transactions:
                        if not isinstance(tx, dict):
                            continue
                        otc = tx.get("otc")
                        otc_dict = otc if isinstance(otc, dict) else {}
                        silver_rows["cambio_api_retroativo.csv"].append(
                            {
                                "trade_date": _parse_date_flexible(tx.get("dataContratacao")) or "",
                                "settlement_date": _parse_date_flexible(
                                    tx.get("dataLiquidacao")
                                )
                                or "",
                                "last_rate": _parse_locale_number(tx.get("valorUltimaTaxa")),
                                "settled_usd": _parse_locale_number(
                                    tx.get("valorLiquidadoMoedaEstrangeira")
                                ),
                                "settled_brl": _parse_locale_number(
                                    tx.get("valorLiquidadoMoedaBase")
                                ),
                                "contracted_usd_total": _parse_locale_number(
                                    tx.get("valorNegociadoMoedaEstrangeiraDiaTotal")
                                ),
                                "contracted_brl_total": _parse_locale_number(
                                    tx.get("valorNegociadoMoedaBaseDiaTotal")
                                ),
                                "trade_count_total": _parse_locale_int(
                                    tx.get("quantidadeRegistroDiaTotal")
                                ),
                                "otc_rate_avg": _parse_locale_number(
                                    otc_dict.get("valorTaxaMedia")
                                ),
                                "otc_rate_min": _parse_locale_number(
                                    otc_dict.get("valorMenorTaxa")
                                ),
                                "otc_rate_max": _parse_locale_number(
                                    otc_dict.get("valorMaiorTaxa")
                                ),
                                "otc_contracted_usd": _parse_locale_number(
                                    otc_dict.get("valorNegociadoMoedaEstrangeira")
                                ),
                                "otc_contracted_brl": _parse_locale_number(
                                    otc_dict.get("valorNegociadoMoedaBase")
                                ),
                                "source_file": source_file,
                            }
                        )
                        total_rows += 1
        elif "resumos_getlist" in name:
            summaries = payload.get("summaries")
            if isinstance(summaries, list):
                for item in summaries:
                    if not isinstance(item, dict):
                        continue
                    silver_rows["cambio_api_resumos.csv"].append(
                        {
                            "hour_bucket": _as_text(item.get("dataContratacao")),
                            "settlement_date": _parse_date_flexible(
                                item.get("dataLiquidacao")
                            )
                            or "",
                            "trade_count_total": _parse_locale_int(
                                item.get("quantidadeTotalRegistro")
                            ),
                            "rate_avg": _parse_locale_number(item.get("valorTaxaMedia")),
                            "rate_min": _parse_locale_number(item.get("valorMenorTaxa")),
                            "rate_max": _parse_locale_number(item.get("valorMaiorTaxa")),
                            "contracted_brl_total": _parse_locale_number(
                                item.get("valorTotalNegociadoMoedaBase")
                            ),
                            "contracted_usd_total": _parse_locale_number(
                                item.get("valorTotalNegociadoMoedaEstrangeira")
                            ),
                            "source_file": source_file,
                        }
                    )
                    total_rows += 1
        elif "parametros_getlist" in name:
            results = payload.get("results")
            if isinstance(results, list):
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    silver_rows["cambio_api_parametros.csv"].append(
                        {
                            "trade_date": _parse_date_flexible(item.get("dataContratacao")) or "",
                            "settlement_date": _parse_date_flexible(
                                item.get("dataLiquidacao")
                            )
                            or "",
                            "opening_rate": _parse_locale_number(item.get("valTaxaAbertura")),
                            "stress_scenario_pct": _parse_locale_number(
                                item.get("valCenarioStress")
                            ),
                            "source_file": source_file,
                        }
                    )
                    total_rows += 1
    return total_rows


def _silver_fields_for_cambio(file_name: str) -> list[str]:
    if file_name == "cambio_retroativo_por_dia.csv":
        return _CAMBIO_RETROATIVO_FIELDS
    if file_name == "cambio_dados_por_canal.csv":
        return _CAMBIO_POR_CANAL_FIELDS
    if file_name == "cambio_volumes_medias.csv":
        return _CAMBIO_MEDIA_FIELDS
    if file_name == "cambio_parametros_abertura.csv":
        return _CAMBIO_PARAMETROS_FIELDS
    if file_name == "cambio_api_retroativo.csv":
        return _CAMBIO_API_RETROATIVO_FIELDS
    if file_name == "cambio_api_resumos.csv":
        return _CAMBIO_API_RESUMOS_FIELDS
    if file_name == "cambio_api_parametros.csv":
        return _CAMBIO_API_PARAMETROS_FIELDS
    raise ValueError(f"Arquivo de cambio nao mapeado: {file_name}")


def _process_renda_fixa(
    *,
    source_root: Path,
    bronze_root: Path,
    silver_root: Path,
) -> dict[str, Any]:
    raw_root = source_root / "renda_fixa" / "raw"
    files = sorted(raw_root.glob("*.csv")) if raw_root.exists() else []

    bronze_dir = bronze_root / "renda_fixa"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    silver_rows: list[dict[str, Any]] = []
    processed_files: list[dict[str, Any]] = []

    for source_file in files:
        source_label = str(source_file.relative_to(source_root).as_posix())
        bronze_file = bronze_dir / f"{_slugify(source_label)}.csv"
        dataset = "outros"
        if "_estoque_" in source_file.name.lower():
            dataset = "estoque"
        elif "_volume_" in source_file.name.lower():
            dataset = "volume"

        with source_file.open("r", encoding="latin1", newline="") as input_file:
            reader = csv.reader(input_file, delimiter=";")
            try:
                header = next(reader)
            except StopIteration:
                continue
            normalized_header = _normalize_header(header)
            row_count = 0

            with bronze_file.open("w", encoding="utf-8", newline="") as output_file:
                writer = csv.DictWriter(
                    output_file,
                    fieldnames=[*normalized_header, "source_file"],
                )
                writer.writeheader()

                for row in reader:
                    clean_row = _normalize_row(row, len(normalized_header))
                    if _is_row_empty(clean_row):
                        continue
                    row_count += 1
                    writer.writerow(
                        {
                            **{
                                key: clean_row[idx] for idx, key in enumerate(normalized_header)
                            },
                            "source_file": source_label,
                        }
                    )

                    if dataset == "estoque" and len(clean_row) >= 2:
                        silver_rows.append(
                            {
                                "dataset": dataset,
                                "trade_date": _parse_date_ddmmyyyy(clean_row[0]) or "",
                                "n_operations": "",
                                "volume_brl": _parse_locale_number(clean_row[1]),
                                "source_file": source_label,
                            }
                        )
                    elif dataset == "volume" and len(clean_row) >= 3:
                        silver_rows.append(
                            {
                                "dataset": dataset,
                                "trade_date": _parse_date_ddmmyyyy(clean_row[0]) or "",
                                "n_operations": _parse_locale_int(clean_row[1]),
                                "volume_brl": _parse_locale_number(clean_row[2]),
                                "source_file": source_label,
                            }
                        )

        processed_files.append(
            {
                "source_file": source_label,
                "bronze_file": str(bronze_file),
                "rows": row_count,
            }
        )

    silver_path = silver_root / "renda_fixa_series.csv"
    _write_rows_to_csv(output_path=silver_path, rows=silver_rows, fieldnames=_RENDA_FIXA_FIELDS)

    return {
        "input_files": len(files),
        "silver_rows": len(silver_rows),
        "silver_file": str(silver_path),
        "processed_files": processed_files,
    }


def _process_pesquisa_pregao_manifest(
    *,
    pesquisa_root: Path | None,
    bronze_root: Path,
) -> dict[str, Any]:
    if pesquisa_root is None:
        return {
            "enabled": False,
            "input_files": 0,
        }

    extracted_root = pesquisa_root / "extracted"
    if not extracted_root.exists():
        return {
            "enabled": True,
            "input_files": 0,
            "manifest_file": "",
        }

    xml_files = sorted(extracted_root.rglob("*.xml"))
    bronze_dir = bronze_root / "pesquisa_pregao"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = bronze_dir / "files_manifest.csv"

    rows: list[dict[str, Any]] = []
    for xml_file in xml_files:
        name = xml_file.name
        layout_code = name.split("_", maxsplit=1)[0] if "_" in name else ""
        rows.append(
            {
                "layout_code": layout_code,
                "file_name": name,
                "size_bytes": xml_file.stat().st_size,
                "source_file": str(xml_file.relative_to(pesquisa_root).as_posix()),
            }
        )

    _write_rows_to_csv(output_path=manifest_path, rows=rows, fieldnames=_PESQUISA_PREGAO_FIELDS)
    return {
        "enabled": True,
        "input_files": len(xml_files),
        "manifest_file": str(manifest_path),
    }


def _normalize_header(header: list[str], *, min_columns: int = 0) -> list[str]:
    trimmed = list(header)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    if min_columns > len(trimmed):
        trimmed.extend("" for _ in range(min_columns - len(trimmed)))
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for idx, col in enumerate(trimmed):
        base = _slugify(col) or f"col_{idx + 1:02d}"
        occurrence = seen.get(base, 0) + 1
        seen[base] = occurrence
        normalized.append(base if occurrence == 1 else f"{base}_{occurrence}")
    return normalized


def _normalize_row(row: list[str], expected_len: int) -> list[str]:
    clean = [item.strip() for item in row]
    if len(clean) < expected_len:
        clean = [*clean, *("" for _ in range(expected_len - len(clean)))]
    elif len(clean) > expected_len:
        clean = clean[:expected_len]
    return clean


def _is_row_empty(row: Iterable[str]) -> bool:
    return not any(item.strip() for item in row)


def _write_rows_to_csv(
    *,
    output_path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _cotahist_granularity(file_name: str) -> str:
    match = re.search(r"COTAHIST_([AMD])", file_name.upper())
    if match is None:
        return "annual"
    code = match.group(1)
    if code == "D":
        return "daily"
    if code == "M":
        return "monthly"
    return "annual"


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return slug


def _parse_cotahist_scaled_int(raw: str) -> float | None:
    digits = raw.strip()
    if not digits or not digits.isdigit():
        return None
    return int(digits) / 100


def _parse_int_raw_digits(raw: str) -> int | None:
    digits = raw.strip()
    if not digits or not digits.isdigit():
        return None
    return int(digits)


def _parse_date_yyyymmdd(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _parse_date_ddmmyyyy(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _parse_month_abbrev(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%b-%y").strftime("%Y-%m")
    except ValueError:
        return None


def _parse_date_flexible(raw: Any) -> str | None:
    if raw is None:
        return None
    text = _as_text(raw).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return _parse_date_yyyymmdd(text)
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        return _parse_date_ddmmyyyy(text)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return None


def _parse_locale_number(raw: Any) -> float | str:
    if raw is None:
        return ""
    text = _as_text(raw).strip()
    if not text:
        return ""
    candidate = text.replace("\u00a0", "")
    if "," in candidate:
        candidate = candidate.replace(".", "").replace(",", ".")
    elif candidate.count(".") > 1:
        candidate = candidate.replace(".", "")
    try:
        return float(candidate)
    except ValueError:
        return ""


def _parse_locale_int(raw: Any) -> int | str:
    if raw is None:
        return ""
    text = _as_text(raw).strip()
    if not text:
        return ""
    candidate = text.replace("\u00a0", "").replace(".", "")
    if "," in candidate:
        try:
            return int(float(candidate.replace(",", ".")))
        except ValueError:
            return ""
    try:
        return int(candidate)
    except ValueError:
        return ""


def _as_text(value: Any) -> str:
    return str(value)

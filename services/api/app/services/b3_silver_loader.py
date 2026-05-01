from __future__ import annotations

import csv
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.db import DATA_DIR


@dataclass(slots=True)
class B3SilverLoadSummary:
    csv_path: str
    database_path: str
    provider: str
    rows_seen: int
    rows_parsed: int
    inserted: int
    duplicates_ignored: int
    parse_errors: int
    truncated_existing_rows: int
    run_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "csv_path": self.csv_path,
            "database_path": self.database_path,
            "provider": self.provider,
            "rows_seen": self.rows_seen,
            "rows_parsed": self.rows_parsed,
            "inserted": self.inserted,
            "duplicates_ignored": self.duplicates_ignored,
            "parse_errors": self.parse_errors,
            "truncated_existing_rows": self.truncated_existing_rows,
            "run_at": self.run_at,
        }


def load_b3_silver_market_daily(
    *,
    csv_path: Path,
    database_path: Path | None = None,
    provider: str = "b3-cotahist-lake",
    currency: str = "BRL",
    batch_size: int = 5_000,
    truncate_provider_before_load: bool = False,
    max_rows: int | None = None,
    flush_max_retries: int = 30,
) -> B3SilverLoadSummary:
    if batch_size <= 0:
        raise ValueError("batch_size deve ser maior que zero.")
    if max_rows is not None and max_rows <= 0:
        raise ValueError("max_rows deve ser maior que zero quando informado.")
    if flush_max_retries <= 0:
        raise ValueError("flush_max_retries deve ser maior que zero.")
    if not csv_path.exists():
        raise ValueError(f"Arquivo de entrada nao encontrado: {csv_path}")

    db_path = database_path or (DATA_DIR / "app.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(UTC).replace(microsecond=0).isoformat()
    rows_seen = 0
    rows_parsed = 0
    parse_errors = 0
    inserted = 0
    truncated = 0
    pending: list[tuple[object, ...]] = []

    with sqlite3.connect(db_path, timeout=120.0) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 120000")
        _ensure_market_ticks_table(conn)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_market_ticks_provider_source_payload
            ON market_ticks(provider, source_payload_id)
            """
        )

        if truncate_provider_before_load:
            cursor = conn.execute("DELETE FROM market_ticks WHERE provider = ?", (provider,))
            truncated = int(cursor.rowcount if cursor.rowcount is not None else 0)
            conn.commit()

        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for raw_row in reader:
                rows_seen += 1
                if max_rows is not None and rows_seen > max_rows:
                    break
                parsed = _parse_market_daily_row(
                    row=raw_row,
                    provider=provider,
                    currency=currency,
                    ingest_time=now_iso,
                )
                if parsed is None:
                    parse_errors += 1
                    continue
                rows_parsed += 1
                pending.append(parsed)

                if len(pending) >= batch_size:
                    inserted += _flush_batch(
                        conn=conn,
                        batch=pending,
                        max_retries=flush_max_retries,
                    )
                    pending.clear()

        if pending:
            inserted += _flush_batch(
                conn=conn,
                batch=pending,
                max_retries=flush_max_retries,
            )
            pending.clear()

    duplicates = max(rows_parsed - inserted, 0)
    return B3SilverLoadSummary(
        csv_path=str(csv_path),
        database_path=str(db_path),
        provider=provider,
        rows_seen=rows_seen,
        rows_parsed=rows_parsed,
        inserted=inserted,
        duplicates_ignored=duplicates,
        parse_errors=parse_errors,
        truncated_existing_rows=truncated,
        run_at=now_iso,
    )


def _flush_batch(
    *,
    conn: sqlite3.Connection,
    batch: list[tuple[object, ...]],
    max_retries: int,
) -> int:
    query = """
        INSERT INTO market_ticks (
            instrument,
            provider,
            event_time,
            ingest_time,
            price,
            volume,
            currency,
            source_payload_id
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM market_ticks
            WHERE provider = ? AND source_payload_id = ?
            LIMIT 1
        )
    """
    for attempt in range(1, max_retries + 1):
        try:
            before = conn.total_changes
            conn.executemany(query, batch)
            conn.commit()
            return conn.total_changes - before
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            if attempt >= max_retries:
                raise
            sleep_seconds = min(0.5 * attempt, 8.0)
            time.sleep(sleep_seconds)
    return 0


def _parse_market_daily_row(
    *,
    row: dict[str, str],
    provider: str,
    currency: str,
    ingest_time: str,
) -> tuple[object, ...] | None:
    instrument = row.get("instrument", "").strip().upper()
    trade_date = row.get("trade_date", "").strip()
    close_price_raw = row.get("close_price", "").strip()
    quantity_raw = row.get("trade_quantity", "").strip()
    if not instrument or not trade_date or not close_price_raw:
        return None
    try:
        close_price = float(close_price_raw)
        quantity = int(float(quantity_raw)) if quantity_raw else 0
    except ValueError:
        return None

    if close_price <= 0:
        return None
    event_time = f"{trade_date}T00:00:00+00:00"
    source_payload_id = f"{provider}:{trade_date}:{instrument}"
    return (
        instrument,
        provider,
        event_time,
        ingest_time,
        close_price,
        quantity,
        currency,
        source_payload_id,
        provider,
        source_payload_id,
    )


def _ensure_market_ticks_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            provider TEXT NOT NULL,
            event_time TEXT NOT NULL,
            ingest_time TEXT NOT NULL,
            price REAL NOT NULL,
            volume INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'BRL',
            source_payload_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_market_ticks_instrument ON market_ticks(instrument)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_market_ticks_event_time ON market_ticks(event_time)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_market_ticks_ingest_time ON market_ticks(ingest_time)
        """
    )
    conn.commit()

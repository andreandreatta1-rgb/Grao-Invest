from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from app.services.b3_silver_loader import load_b3_silver_market_daily


def _write_market_daily(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_load_b3_silver_market_daily_is_idempotent(tmp_path: Path) -> None:
    csv_path = tmp_path / "market_daily.csv"
    db_path = tmp_path / "app.db"
    _write_market_daily(
        csv_path,
        rows=[
            {
                "trade_date": "2026-04-20",
                "instrument": "PETR4",
                "open_price": "34.10",
                "high_price": "35.00",
                "low_price": "33.95",
                "close_price": "34.80",
                "average_price": "34.60",
                "trade_count": "1200",
                "trade_quantity": "1000000",
                "trade_volume": "34600000",
                "vwap": "34.60",
                "source_file": "extracted/COTAHIST_D20042026/COTAHIST_D20042026.TXT",
                "source_granularity": "daily",
            },
            {
                "trade_date": "2026-04-20",
                "instrument": "VALE3",
                "open_price": "61.10",
                "high_price": "62.00",
                "low_price": "60.50",
                "close_price": "61.80",
                "average_price": "61.20",
                "trade_count": "980",
                "trade_quantity": "800000",
                "trade_volume": "48960000",
                "vwap": "61.20",
                "source_file": "extracted/COTAHIST_D20042026/COTAHIST_D20042026.TXT",
                "source_granularity": "daily",
            },
        ],
    )

    first = load_b3_silver_market_daily(
        csv_path=csv_path,
        database_path=db_path,
        provider="b3-cotahist-lake",
        batch_size=2,
    )
    assert first.rows_seen == 2
    assert first.inserted == 2
    assert first.duplicates_ignored == 0
    assert first.parse_errors == 0

    second = load_b3_silver_market_daily(
        csv_path=csv_path,
        database_path=db_path,
        provider="b3-cotahist-lake",
        batch_size=2,
    )
    assert second.rows_seen == 2
    assert second.inserted == 0
    assert second.duplicates_ignored == 2
    assert second.parse_errors == 0

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0]
    assert count == 2


def test_load_b3_silver_market_daily_can_truncate_provider(tmp_path: Path) -> None:
    csv_path = tmp_path / "market_daily.csv"
    db_path = tmp_path / "app.db"
    _write_market_daily(
        csv_path,
        rows=[
            {
                "trade_date": "2026-04-20",
                "instrument": "PETR4",
                "open_price": "34.10",
                "high_price": "35.00",
                "low_price": "33.95",
                "close_price": "34.80",
                "average_price": "34.60",
                "trade_count": "1200",
                "trade_quantity": "1000000",
                "trade_volume": "34600000",
                "vwap": "34.60",
                "source_file": "x",
                "source_granularity": "daily",
            }
        ],
    )

    load_b3_silver_market_daily(
        csv_path=csv_path,
        database_path=db_path,
        provider="b3-cotahist-lake",
    )
    reload_summary = load_b3_silver_market_daily(
        csv_path=csv_path,
        database_path=db_path,
        provider="b3-cotahist-lake",
        truncate_provider_before_load=True,
    )
    assert reload_summary.truncated_existing_rows == 1
    assert reload_summary.inserted == 1

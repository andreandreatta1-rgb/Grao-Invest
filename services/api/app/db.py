from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path
import tempfile

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parents[3]


def _default_data_dir() -> Path:
    explicit = os.getenv("DATA_DIR")
    if explicit:
        return Path(explicit)
    if os.getenv("VERCEL"):
        return Path(tempfile.gettempdir()) / "grao-invest-data"
    return BASE_DIR / "data"


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


DATA_DIR = _default_data_dir().resolve()
default_sqlite_url = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", default_sqlite_url))

if DATABASE_URL.startswith("sqlite"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

engine_kwargs: dict[str, object] = {"future": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,
    }
    # SQLite + long-lived websocket connections can exhaust QueuePool.
    # Use NullPool so each session has an independent short-lived connection.
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
class Base(DeclarativeBase):
    pass


if engine.url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.close()


def run_startup_migrations() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    migrations: dict[str, dict[str, str]] = {
        "indicator_snapshots": {
            "sma_20": "REAL DEFAULT 0.0",
            "ema_12": "REAL DEFAULT 0.0",
            "ema_26": "REAL DEFAULT 0.0",
            "volatility_10": "REAL DEFAULT 0.0",
            "momentum_5": "REAL DEFAULT 0.0",
            "macd": "REAL DEFAULT 0.0",
        },
        "signals": {
            "anti_hype_score": "REAL DEFAULT 50.0",
            "xai_payload": "TEXT DEFAULT '{}'",
            "signal_status": "TEXT DEFAULT 'active'",
            "expires_at": "TEXT",
            "expiry_reason": "TEXT",
        },
        "paper_orders": {
            "risk_status": "TEXT DEFAULT 'accepted'",
            "risk_notes": "TEXT DEFAULT ''",
        },
        "risk_decisions": {
            "portfolio_exposure": "REAL DEFAULT 0.0",
            "projected_exposure": "REAL DEFAULT 0.0",
        },
    }
    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            table_exists = connection.execute(
                text(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = :table_name LIMIT 1"
                ),
                {"table_name": table_name},
            ).scalar_one_or_none()
            if table_exists is None:
                continue
            existing = {
                str(row[1])
                for row in connection.execute(text(f"PRAGMA table_info({table_name})")).all()
            }
            for column_name, definition in columns.items():
                if column_name in existing:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
                    )
                )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_market_ticks_provider_ingest_id "
                "ON market_ticks(provider, ingest_time, id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_market_ticks_instrument_ingest_id "
                "ON market_ticks(instrument, ingest_time, id)"
            )
        )


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

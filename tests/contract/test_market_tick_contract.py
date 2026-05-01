from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tests.contract.schema_assertions import assert_payload_matches_schema


def test_market_tick_schema_contract() -> None:
    schema = json.loads(
        Path("specs/events/market_tick.schema.json").read_text(encoding="utf-8")
    )
    assert schema["title"] == "MarketTickV1"
    assert schema["properties"]["event_type"]["const"] == "market.tick.normalized.v1"
    assert "event_time" in schema["required"]
    assert "ingest_time" in schema["required"]


def test_market_tick_endpoint_payload_matches_schema(client) -> None:
    schema = json.loads(
        Path("specs/events/market_tick.schema.json").read_text(encoding="utf-8")
    )
    response = client.post(
        "/api/market/ticks/ingest",
        json={
            "instrument": "PETR4",
            "provider": "demo-primary",
            "event_time": datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
            "price": 39.10,
            "volume": 1500,
            "currency": "BRL",
            "source_payload_id": "contract-tick-001",
        },
    )
    assert response.status_code == 200
    assert_payload_matches_schema(response.json(), schema)


def test_market_tick_ingest_is_idempotent_by_source_payload(client) -> None:
    payload = {
        "instrument": "PETR4",
        "provider": "demo-primary",
        "event_time": datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
        "price": 39.10,
        "volume": 1500,
        "currency": "BRL",
        "source_payload_id": "contract-idempotent-001",
    }
    first = client.post("/api/market/ticks/ingest", json=payload)
    second = client.post("/api/market/ticks/ingest", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    ticks = client.get(
        "/api/market/ticks/PETR4",
        params={"as_of": datetime(2100, 1, 1, tzinfo=UTC).isoformat()},
    )
    assert ticks.status_code == 200
    sources = [item["source_payload_id"] for item in ticks.json()]
    assert sources.count("contract-idempotent-001") == 1

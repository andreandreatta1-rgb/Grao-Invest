from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.contract.schema_assertions import assert_payload_matches_schema


def test_fundamental_snapshot_schema_contract() -> None:
    schema = json.loads(
        Path("specs/events/fundamental_snapshot.schema.json").read_text(encoding="utf-8")
    )
    assert schema["title"] == "FundamentalSnapshotV1"
    assert schema["properties"]["event_type"]["const"] == "fundamental.snapshot.normalized.v1"
    assert "availability_time" in schema["required"]
    assert "version_tag" in schema["required"]


def _fundamental_payload() -> dict[str, object]:
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    return {
        "instrument": "PETR4",
        "source_name": "CVM",
        "source_type": "regulatory",
        "reference_time": (base_time - timedelta(days=20)).isoformat(),
        "availability_time": (base_time - timedelta(days=1)).isoformat(),
        "pe_ratio": 9.8,
        "pb_ratio": 1.5,
        "ev_ebitda": 7.1,
        "dividend_yield": 5.2,
        "roe": 16.0,
        "net_margin": 13.0,
        "revenue_growth": 8.0,
        "payout_ratio": 39.0,
        "version_tag": "itr-2026q1-v1",
    }


def test_fundamental_snapshot_endpoint_payload_matches_schema(client) -> None:
    schema = json.loads(
        Path("specs/events/fundamental_snapshot.schema.json").read_text(encoding="utf-8")
    )
    response = client.post("/api/fundamentals/ingest", json=_fundamental_payload())
    assert response.status_code == 200
    assert_payload_matches_schema(response.json(), schema)


def test_fundamental_snapshot_ingest_is_idempotent_by_versioned_key(client) -> None:
    payload = _fundamental_payload()
    first = client.post("/api/fundamentals/ingest", json=payload)
    second = client.post("/api/fundamentals/ingest", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["fundamental_id"] == second.json()["fundamental_id"]

    lookup = client.get(
        "/api/fundamentals/PETR4",
        params={"as_of": datetime(2100, 1, 1, tzinfo=UTC).isoformat()},
    )
    assert lookup.status_code == 200
    assert lookup.json()["version_tag"] == payload["version_tag"]

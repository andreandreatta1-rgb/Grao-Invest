from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "SenhaForte123!"


def _build_cotahist_line(
    *,
    date_yyyymmdd: str,
    ticker: str,
    close_price: float,
    quantity: int,
    bdi_code: str = "02",
    market_type: str = "010",
) -> str:
    line = [" "] * 245

    def put(start: int, end: int, value: str) -> None:
        text = value[: end - start].ljust(end - start)
        line[start:end] = list(text)

    def put_num(start: int, end: int, number: int) -> None:
        text = str(number).rjust(end - start, "0")
        line[start:end] = list(text)

    put(0, 2, "01")
    put(2, 10, date_yyyymmdd)
    put(10, 12, bdi_code)
    put(12, 24, ticker.upper())
    put(24, 27, market_type)
    put(27, 39, ticker.upper())
    put(39, 49, "ON")
    put(49, 52, "")
    put(52, 56, "R$")
    price_int = int(round(close_price * 100))
    put_num(56, 69, price_int)
    put_num(69, 82, price_int)
    put_num(82, 95, price_int)
    put_num(95, 108, price_int)
    put_num(108, 121, price_int)
    put_num(121, 134, price_int)
    put_num(134, 147, price_int)
    put_num(147, 152, 10)
    put_num(152, 170, quantity)
    put_num(170, 188, int(quantity * close_price * 100))
    put_num(188, 201, 0)
    put_num(201, 202, 0)
    put(202, 210, date_yyyymmdd[4:] + date_yyyymmdd[:4])
    put_num(210, 217, 1000)
    put_num(217, 230, 0)
    put(230, 242, f"BR{ticker.upper():<10}"[:12])
    put_num(242, 245, 999)
    return "".join(line)


def _build_cotahist_zip(lines: list[str], *, year: int) -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"COTAHIST_A{year}.TXT", "\n".join(lines) + "\n")
    return payload.getvalue()


def _signup_and_authenticate(client: TestClient, email: str) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Universe Lab",
            "full_name": "User Universe",
            "email": email,
            "password": DEFAULT_PASSWORD,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert signup_response.status_code == 200
    user_id = signup_response.json()["user_id"]
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return user_id


def test_b3_sync_universe_range_discovers_equities(client, monkeypatch) -> None:
    from app.services import b3_external

    user_id = _signup_and_authenticate(client, "universe-range@example.com")
    zip_2024 = _build_cotahist_zip(
        [
            "00COTAHIST.2024BOVESPA 20241230".ljust(245),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="PETR4",
                close_price=35.2,
                quantity=120000,
            ),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="VALE3",
                close_price=61.3,
                quantity=210000,
            ),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="PETRA123",
                close_price=1.8,
                quantity=5000,
                bdi_code="78",
            ),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="DOLFUT",
                close_price=5100.0,
                quantity=100,
                market_type="070",
            ),
            "99COTAHIST.2024BOVESPA 20241230".ljust(245),
        ],
        year=2024,
    )
    zip_2025 = _build_cotahist_zip(
        [
            "00COTAHIST.2025BOVESPA 20251230".ljust(245),
            _build_cotahist_line(
                date_yyyymmdd="20250120",
                ticker="B3SA3",
                close_price=13.7,
                quantity=230000,
            ),
            _build_cotahist_line(
                date_yyyymmdd="20250121",
                ticker="PETR4",
                close_price=37.1,
                quantity=150000,
            ),
            "99COTAHIST.2025BOVESPA 20251230".ljust(245),
        ],
        year=2025,
    )

    def fake_download(year: int, timeout_seconds: int = 90) -> bytes:
        if year == 2024:
            return zip_2024
        if year == 2025:
            return zip_2025
        raise AssertionError(f"Ano inesperado {year} no teste (timeout={timeout_seconds})")

    monkeypatch.setattr(
        b3_external,
        "download_cotahist_zip",
        fake_download,
    )

    response = client.post(
        "/api/market/external/b3/sync-universe-range",
        json={
            "user_id": user_id,
            "start_year": 2024,
            "end_year": 2025,
            "max_days_per_instrument_per_year": 10,
            "max_instruments": 20,
            "allowed_bdi_codes": ["02"],
            "allowed_market_types": ["010"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_scope"] == "universe"
    assert payload["years"] == [2024, 2025]
    assert payload["discovered_universe_size"] == 3
    assert sorted(payload["portfolio"]) == ["B3SA3", "PETR4", "VALE3"]
    assert payload["sync_result"]["inserted"] == 4
    assert payload["format_validation"]["matched_rows"] == 4
    assert len(payload["yearly_breakdown"]) == 2


def test_market_tick_ingest_live_updates_algorithm_state(client) -> None:
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    first_response = None
    final_response = None
    for index in range(26):
        response = client.post(
            "/api/market/ticks/ingest-live",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": 35.0 + (index * 0.2),
                "volume": 1000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"live-petr4-{index}",
                "auto_recompute_indicators": True,
            },
        )
        assert response.status_code == 200
        if index == 0:
            first_response = response.json()
        if index == 25:
            final_response = response.json()

    assert first_response is not None
    assert final_response is not None
    assert first_response["algorithm_update"]["indicator_updated"] is False
    assert first_response["algorithm_update"]["learning_status"] == "warming_up"
    assert final_response["algorithm_update"]["indicator_updated"] is True
    assert final_response["algorithm_update"]["learning_status"] == "updated"
    assert final_response["algorithm_update"]["tick_count"] >= 26
    assert final_response["algorithm_update"]["indicator_snapshot"]["instrument"] == "PETR4"

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from app.main import AUTH_DISABLED
from fastapi.testclient import TestClient

PETR4_SERIES = [
    35.1,
    35.4,
    35.6,
    35.5,
    35.8,
    36.0,
    36.2,
    36.4,
    36.5,
    36.7,
    36.9,
    37.1,
    37.2,
    37.4,
    37.6,
    37.8,
    38.0,
    38.2,
    38.4,
    38.6,
    38.8,
    39.0,
    39.2,
    39.4,
    39.6,
    39.8,
]

PETR4_EXTENDED_SERIES = PETR4_SERIES + [40.0, 40.2, 40.4, 40.6]

PETR4_STABLE_SERIES = [
    35.1,
    35.2,
    35.3,
    35.4,
    35.5,
    35.6,
    35.7,
    35.8,
    35.9,
    36.0,
    36.1,
    36.2,
    36.3,
    36.4,
    36.5,
    36.6,
    36.7,
    36.8,
    36.9,
    37.0,
    37.1,
    37.2,
    37.3,
    37.4,
    37.5,
    37.6,
]

DEFAULT_PASSWORD = "SenhaForte123!"


def _build_cotahist_line(
    *,
    date_yyyymmdd: str,
    ticker: str,
    close_price: float,
    quantity: int,
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
    put(10, 12, "02")
    put(12, 24, ticker.upper())
    put(24, 27, "010")
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


def _build_cotahist_zip(lines: list[str]) -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("COTAHIST_A2025.TXT", "\n".join(lines) + "\n")
    return payload.getvalue()


def signup_and_authenticate(
    client: TestClient,
    *,
    tenant_name: str,
    full_name: str,
    email: str,
) -> int:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": tenant_name,
            "full_name": full_name,
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


def test_dashboard_anonymous_bootstrap_without_seed_user(client) -> None:
    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")
    response = client.get("/api/dashboard/summary/1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 1
    assert payload["open_positions"] == []


def test_dashboard_uses_seed_when_runtime_snapshots_are_missing(client, tmp_path) -> None:
    from app import main as main_module

    if not AUTH_DISABLED:
        pytest.skip("Modo anonimo desativado no ambiente de teste.")

    seed_source = main_module.data_dir / "dashboard_seed.json"
    assert seed_source.exists()
    seed_data_dir = tmp_path / "data"
    seed_data_dir.mkdir(parents=True, exist_ok=True)
    (seed_data_dir / "dashboard_seed.json").write_text(
        seed_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    original_data_dir = main_module.data_dir
    original_bundled_data_dir = main_module.bundled_data_dir
    main_module.data_dir = seed_data_dir
    main_module.bundled_data_dir = seed_data_dir
    try:
        response = client.get("/api/dashboard/summary/1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["thesis_history_overview"]["total_tested"] > 0
        assert len(payload["thesis_open_operations"]) > 0
    finally:
        main_module.data_dir = original_data_dir
        main_module.bundled_data_dir = original_bundled_data_dir


def test_end_to_end_mvp_flow(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Alpha Capital Lab",
        full_name="Enzo Sponsor",
        email="enzo@example.com",
    )

    suitability_response = client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    assert suitability_response.status_code == 200

    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    news_response = client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras divulga fato relevante com atualizacao operacional",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    assert news_response.status_code == 200

    for index, price in enumerate(PETR4_SERIES):
        ingest_response = client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"tick-{index}",
            },
        )
        assert ingest_response.status_code == 200

    indicator_response = client.post(
        "/api/analysis/indicators/recompute",
        json={"instrument": "PETR4"},
    )
    assert indicator_response.status_code == 200

    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    rationale = signal_response.json()["rationale"].lower()
    assert "compre" not in rationale
    assert signal_response.json()["confidence"] > 0.57
    signal_id = signal_response.json()["signal_id"]

    order_response = client.post(
        f"/api/paper/orders/from-signal/{signal_id}",
        json={"user_id": user_id, "quantity": 10},
    )
    assert order_response.status_code == 200
    assert order_response.json()["execution_price"] > 37.6
    assert order_response.json()["risk_status"] == "accepted"

    dashboard_response = client.get(f"/api/dashboard/summary/{user_id}")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["open_positions"][0]["instrument"] == "PETR4"
    assert dashboard["latest_orders"][0]["quantity"] == 10
    assert dashboard["risk_decisions"][0]["decision"] == "accepted"
    assert dashboard["latest_news"][0]["instrument"] == "PETR4"


def test_paper_order_requires_suitability_before_execution(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="No Suitability Lab",
        full_name="User Sem Suitability",
        email="nosuitability@example.com",
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras publica fato relevante operacional",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"nosuitability-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    blocked_order = client.post(
        f"/api/paper/orders/from-signal/{signal_response.json()['signal_id']}",
        json={"user_id": user_id, "quantity": 10},
    )
    assert blocked_order.status_code == 400
    assert "suitability obrigatorio" in blocked_order.json()["detail"].lower()


def test_paper_order_execution_memory_is_auditable(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Paper Memory Lab",
        full_name="User Paper Memory",
        email="paper-memory@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras divulga fato relevante com atualizacao operacional",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1200 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"paper-memory-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    order_response = client.post(
        f"/api/paper/orders/from-signal/{signal_response.json()['signal_id']}",
        json={"user_id": user_id, "quantity": 30},
    )
    assert order_response.status_code == 200
    assert order_response.json()["estimated_cost"] > 0
    assert order_response.json()["estimated_tax"] >= 0

    audit_response = client.get(
        "/api/audit/events",
        params={"event_type": "paper.order.executed"},
    )
    assert audit_response.status_code == 200
    audit_events = audit_response.json()
    assert len(audit_events) >= 1
    payload = json.loads(audit_events[0]["details"])
    assert payload["order_id"] >= 1
    assert payload["execution_memory"]["friction"]["slippage_bps"] > 0
    assert payload["execution_memory"]["cost_breakdown"]["total_cost"] > 0
    assert payload["execution_memory"]["tax_estimate"]["estimated_rate"] == 0.15


def test_login_progressive_lockout_triggers_after_invalid_attempts(client) -> None:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "tenant_name": "Lockout Lab",
            "full_name": "User Lockout",
            "email": "lockout@example.com",
            "password": DEFAULT_PASSWORD,
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert signup_response.status_code == 200

    for _ in range(3):
        invalid_login = client.post(
            "/api/auth/login",
            json={"email": "lockout@example.com", "password": "SenhaErrada123!"},
        )
        assert invalid_login.status_code == 400

    locked_login = client.post(
        "/api/auth/login",
        json={"email": "lockout@example.com", "password": DEFAULT_PASSWORD},
    )
    assert locked_login.status_code == 400
    assert "temporariamente bloqueada" in locked_login.json()["detail"].lower()


def test_high_hype_news_blocks_order_flow(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Beta Lab",
        full_name="User Beta",
        email="beta@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "curto",
            "risk_tolerance": "media",
            "liquidity_need": "alta",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "PETR4 dispara em segredo imperdivel de ultima chance",
            "source_name": "Canal Viral",
            "source_type": "social",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_STABLE_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"beta-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    signal_id = signal_response.json()["signal_id"]
    blocked_order = client.post(
        f"/api/paper/orders/from-signal/{signal_id}",
        json={"user_id": user_id, "quantity": 10},
    )
    assert blocked_order.status_code == 400
    assert "baixa credibilidade" in blocked_order.json()["detail"].lower()


def test_backtest_runs_with_point_in_time_replay(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Gamma Lab",
        full_name="User Gamma",
        email="gamma@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    prices = PETR4_EXTENDED_SERIES
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras publica atualizacao operacional com tom factual",
            "source_name": "B3",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(prices):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1500 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"gamma-tick-{index}",
            },
        )
        if index >= 25:
            client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})

    run_response = client.post(
        "/api/backtests/run",
        json={"user_id": user_id, "instrument": "PETR4", "quantity": 10},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["trade_count"] >= 1
    assert "validation_snapshot" in run
    assert "performance" in run["validation_snapshot"]
    assert "robustness" in run["validation_snapshot"]

    detail_response = client.get(f"/api/backtests/{run['run_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["trades"]) == run["trade_count"]
    assert detail["validation_snapshot"]["performance"]["sharpe_ratio"] == (
        run["validation_snapshot"]["performance"]["sharpe_ratio"]
    )
    assert "rationale" in detail["trades"][0]
    assert detail["trades"][0]["signal_time"] <= detail["trades"][-1]["signal_time"]


def test_backtest_alerts_feed_report_and_dashboard_validation(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Mu Lab",
        full_name="User Mu",
        email="mu@example.com",
    )
    suitability = client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    assert suitability.status_code == 200

    rule_response = client.post(
        "/api/alerts/rules",
        json={
            "user_id": user_id,
            "rule_type": "backtest_return",
            "instrument": "PETR4",
            "threshold_value": 100.0,
        },
    )
    assert rule_response.status_code == 200

    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras atualiza guidance e projeções operacionais",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    prices = PETR4_EXTENDED_SERIES
    for index, price in enumerate(prices):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1200 + index * 5,
                "currency": "BRL",
                "source_payload_id": f"mu-tick-{index}",
            },
        )
        if index >= 25:
            client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})

    run_response = client.post(
        "/api/backtests/run",
        json={"user_id": user_id, "instrument": "PETR4", "quantity": 10},
    )
    assert run_response.status_code == 200

    events_response = client.get(f"/api/alerts/events/{user_id}")
    assert events_response.status_code == 200
    events = events_response.json()
    assert any(event["event_type"] == "backtest_return" for event in events)

    report_response = client.get(f"/api/reports/summary/{user_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["strategy_validation"] is not None
    assert report["strategy_validation"]["run_count"] >= 1
    assert "average_sharpe_ratio" in report["strategy_validation"]

    dashboard_response = client.get(f"/api/dashboard/summary/{user_id}")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["strategy_validation"] is not None
    assert dashboard["alert_summary"]["by_type"]["backtest_return"] >= 1


def test_kill_switch_blocks_paper_order(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Delta Lab",
        full_name="User Delta",
        email="delta@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras divulga atualizacao formal ao mercado",
            "source_name": "B3",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1100 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"delta-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    signal_id = signal_response.json()["signal_id"]
    kill_switch_response = client.post(
        "/api/risk/kill-switch",
        json={
            "scope_type": "user",
            "scope_id": str(user_id),
            "status": "active",
            "reason": "Bloqueio manual para investigacao",
        },
    )
    assert kill_switch_response.status_code == 200
    blocked_order = client.post(
        f"/api/paper/orders/from-signal/{signal_id}",
        json={"user_id": user_id, "quantity": 10},
    )
    assert blocked_order.status_code == 400
    assert "kill-switch" in blocked_order.json()["detail"].lower()


def test_portfolio_exposure_limit_blocks_second_large_order(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Epsilon Lab",
        full_name="User Epsilon",
        email="epsilon@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras divulga atualizacao formal ao mercado",
            "source_name": "B3",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1200 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"epsilon-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    first_signal = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    ).json()
    first_order = client.post(
        f"/api/paper/orders/from-signal/{first_signal['signal_id']}",
        json={"user_id": user_id, "quantity": 120},
    )
    assert first_order.status_code == 200

    second_signal = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    ).json()
    second_order = client.post(
        f"/api/paper/orders/from-signal/{second_signal['signal_id']}",
        json={"user_id": user_id, "quantity": 120},
    )
    assert second_order.status_code == 400
    assert "exposicao agregada" in second_order.json()["detail"].lower()


def test_alert_rule_and_report_endpoints(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Zeta Lab",
        full_name="User Zeta",
        email="zeta@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras divulga atualizacao formal ao mercado",
            "source_name": "B3",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1200 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"zeta-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    rule_response = client.post(
        "/api/alerts/rules",
        json={
            "user_id": user_id,
            "rule_type": "signal_confidence",
            "instrument": "PETR4",
            "threshold_value": 0.55,
        },
    )
    assert rule_response.status_code == 200

    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    assert "xai_payload" in signal_response.json()

    events_response = client.get(f"/api/alerts/events/{user_id}")
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) >= 1

    report_response = client.get(f"/api/reports/summary/{user_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["signals_count"] >= 1
    assert report["alert_events"] >= 1


def test_news_source_history_and_high_magnitude_alert(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Lambda Lab",
        full_name="User Lambda",
        email="lambda@example.com",
    )
    rule_response = client.post(
        "/api/alerts/rules",
        json={
            "user_id": user_id,
            "rule_type": "news_magnitude",
            "instrument": "PETR4",
            "threshold_value": 0.8,
        },
    )
    assert rule_response.status_code == 200

    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    high_magnitude_news = client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras publica fato relevante, guidance positivo e dividendo extra",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    assert high_magnitude_news.status_code == 200
    assert high_magnitude_news.json()["sentiment"]["average_magnitude"] >= 0.8

    low_magnitude_news = client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Atualizacao operacional trimestral sem alteracoes materiais",
            "source_name": "Portal Financeiro",
            "source_type": "financial_media",
            "published_at": (base_time + timedelta(minutes=5)).isoformat(),
        },
    )
    assert low_magnitude_news.status_code == 200

    as_of_time = max(base_time + timedelta(days=1), datetime.now(UTC) + timedelta(minutes=5))
    sources_response = client.get(
        "/api/news/sources/PETR4",
        params={"as_of": as_of_time.isoformat()},
    )
    assert sources_response.status_code == 200
    sources = sources_response.json()
    assert len(sources) == 2
    cvm_row = next(item for item in sources if item["source_name"] == "CVM")
    assert cvm_row["article_count"] == 1
    assert cvm_row["average_credibility"] >= 90
    assert cvm_row["average_magnitude"] >= 0.8

    events_response = client.get(f"/api/alerts/events/{user_id}")
    assert events_response.status_code == 200
    events = events_response.json()
    news_events = [event for event in events if event["event_type"] == "news_magnitude"]
    assert len(news_events) == 1
    payload = json.loads(news_events[0]["payload"])
    assert payload["magnitude_score"] >= 0.8
    assert payload["source_name"] == "CVM"


def test_indicator_batch_recompute_for_multi_asset_flow(client) -> None:
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    petr_prices = [
        35.1, 35.4, 35.6, 35.5, 35.8, 36.0, 36.2, 36.4, 36.5, 36.7, 36.9, 37.1, 37.2,
        37.4, 37.6, 37.8, 38.0, 38.2, 38.4, 38.6, 38.8, 39.0, 39.2, 39.4, 39.6, 39.8,
    ]
    vale_prices = [
        61.2, 61.4, 61.6, 61.3, 61.8, 62.1, 62.4, 62.6, 62.8, 63.0, 63.2, 63.4, 63.5,
        63.7, 63.9, 64.0, 64.2, 64.4, 64.6, 64.8, 65.0, 65.2, 65.4, 65.6, 65.8, 66.0,
    ]
    for index, price in enumerate(petr_prices):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"batch-petr4-{index}",
            },
        )
    for index, price in enumerate(vale_prices):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "VALE3",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 2000 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"batch-vale3-{index}",
            },
        )
    batch_response = client.post(
        "/api/analysis/indicators/recompute-batch",
        json={"instruments": ["PETR4", "VALE3"]},
    )
    assert batch_response.status_code == 200
    payload = batch_response.json()
    assert len(payload) == 2
    assert payload[0]["macd"] != 0
    assert payload[1]["macd"] != 0


def test_market_provider_failover_is_auditable(client) -> None:
    signup_and_authenticate(
        client,
        tenant_name="Failover Lab",
        full_name="Ops Auditor",
        email="ops-auditor@example.com",
    )
    primary_setup = client.post(
        "/api/market/providers/status",
        json={
            "provider_name": "demo-primary",
            "role": "primary",
            "status": "healthy",
            "failure_increment": 0,
            "failover_threshold": 2,
            "notes": "bootstrap",
        },
    )
    assert primary_setup.status_code == 200
    assert primary_setup.json()["is_active"] is True

    secondary_setup = client.post(
        "/api/market/providers/status",
        json={
            "provider_name": "demo-secondary",
            "role": "secondary",
            "status": "healthy",
            "failure_increment": 0,
            "failover_threshold": 2,
            "notes": "ready",
        },
    )
    assert secondary_setup.status_code == 200

    first_failure = client.post(
        "/api/market/providers/status",
        json={
            "provider_name": "demo-primary",
            "role": "primary",
            "status": "degraded",
            "failure_increment": 1,
            "failover_threshold": 2,
            "notes": "latencia elevada",
        },
    )
    assert first_failure.status_code == 200
    assert first_failure.json()["is_active"] is True

    second_failure = client.post(
        "/api/market/providers/status",
        json={
            "provider_name": "demo-primary",
            "role": "primary",
            "status": "failed",
            "failure_increment": 1,
            "failover_threshold": 2,
            "notes": "sem resposta",
        },
    )
    assert second_failure.status_code == 200

    providers_response = client.get("/api/market/providers")
    assert providers_response.status_code == 200
    providers = providers_response.json()
    assert providers[0]["provider_name"] == "demo-secondary"
    assert providers[0]["is_active"] is True

    audit_events_response = client.get(
        "/api/audit/events",
        params={"event_type": "market.provider.failover_activated"},
    )
    assert audit_events_response.status_code == 200
    audit_events = audit_events_response.json()
    assert audit_events[0]["event_type"] == "market.provider.failover_activated"
    assert "demo-secondary" in audit_events[0]["details"]

    blocked_primary_tick = client.post(
        "/api/market/ticks/ingest",
        json={
            "instrument": "PETR4",
            "provider": "demo-primary",
            "event_time": datetime(2026, 4, 20, 12, 0, tzinfo=UTC).isoformat(),
            "price": 39.2,
            "volume": 1000,
            "currency": "BRL",
            "source_payload_id": "failover-primary-blocked",
        },
    )
    assert blocked_primary_tick.status_code == 400

    active_tick = client.post(
        "/api/market/ticks/ingest",
        json={
            "instrument": "PETR4",
            "provider": "demo-secondary",
            "event_time": datetime(2026, 4, 20, 12, 1, tzinfo=UTC).isoformat(),
            "price": 39.3,
            "volume": 1010,
            "currency": "BRL",
            "source_payload_id": "failover-secondary-ok",
        },
    )
    assert active_tick.status_code == 200
    assert active_tick.json()["provider"] == "demo-secondary"

    market_ticks_response = client.get("/api/market/ticks/PETR4")
    assert market_ticks_response.status_code == 200
    tick_payload = market_ticks_response.json()
    assert tick_payload[-1]["event_time"] >= tick_payload[0]["event_time"]


def test_b3_external_sync_restricted_small_portfolio(client, monkeypatch) -> None:
    from app.services import b3_external

    user_id = signup_and_authenticate(
        client,
        tenant_name="B3 Sync Lab",
        full_name="User B3 Sync",
        email="b3-sync@example.com",
    )

    cotahist_lines = [
        "00COTAHIST.2025BOVESPA 20251230".ljust(245),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="PETR4",
            close_price=37.10,
            quantity=123456,
        ),
        _build_cotahist_line(
            date_yyyymmdd="20250121",
            ticker="PETR4",
            close_price=37.40,
            quantity=130000,
        ),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="VALE3",
            close_price=62.85,
            quantity=210000,
        ),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="ABEV3",
            close_price=12.34,
            quantity=99999,
        ),
        "99COTAHIST.2025BOVESPA 20251230".ljust(245),
    ]
    cotahist_zip = _build_cotahist_zip(cotahist_lines)
    monkeypatch.setattr(
        b3_external,
        "download_cotahist_zip",
        lambda year, timeout_seconds=90: cotahist_zip,
    )

    response = client.post(
        "/api/market/external/b3/sync",
        json={
            "user_id": user_id,
            "year": 2025,
            "instruments": ["PETR4", "VALE3"],
            "max_days_per_instrument": 2,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "B3.COTAHIST"
    assert payload["format_validation"]["expected_line_length"] == 245
    assert payload["format_validation"]["matched_rows"] == 3
    assert payload["sync_result"]["inserted"] == 3
    assert payload["sync_result"]["ingested_by_instrument"]["PETR4"] == 2
    assert payload["sync_result"]["ingested_by_instrument"]["VALE3"] == 1

    second = client.post(
        "/api/market/external/b3/sync",
        json={
            "user_id": user_id,
            "year": 2025,
            "instruments": ["PETR4", "VALE3"],
            "max_days_per_instrument": 2,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["sync_result"]["inserted"] == 0
    assert second_payload["sync_result"]["duplicates_ignored"] == 3


def test_b3_external_sync_uses_default_small_portfolio_when_omitted(client, monkeypatch) -> None:
    from app.services import b3_external

    user_id = signup_and_authenticate(
        client,
        tenant_name="B3 Default Sync Lab",
        full_name="User B3 Default",
        email="b3-default@example.com",
    )
    cotahist_lines = [
        "00COTAHIST.2025BOVESPA 20251230".ljust(245),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="PETR4",
            close_price=37.10,
            quantity=123456,
        ),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="B3SA3",
            close_price=12.25,
            quantity=99999,
        ),
        _build_cotahist_line(
            date_yyyymmdd="20250120",
            ticker="MGLU3",
            close_price=4.13,
            quantity=80000,
        ),
        "99COTAHIST.2025BOVESPA 20251230".ljust(245),
    ]
    cotahist_zip = _build_cotahist_zip(cotahist_lines)
    monkeypatch.setattr(
        b3_external,
        "download_cotahist_zip",
        lambda year, timeout_seconds=90: cotahist_zip,
    )

    response = client.post(
        "/api/market/external/b3/sync",
        json={
            "user_id": user_id,
            "year": 2025,
            "max_days_per_instrument": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["portfolio"]) == len(b3_external.DEFAULT_SMALL_PORTFOLIO)
    assert payload["sync_result"]["inserted"] == 2
    assert payload["sync_result"]["ingested_by_instrument"]["PETR4"] == 1
    assert payload["sync_result"]["ingested_by_instrument"]["B3SA3"] == 1


def test_b3_external_sync_range_aggregates_multi_year_results(client, monkeypatch) -> None:
    from app.services import b3_external

    user_id = signup_and_authenticate(
        client,
        tenant_name="B3 Range Sync Lab",
        full_name="User B3 Range",
        email="b3-range@example.com",
    )
    cotahist_2024 = _build_cotahist_zip(
        [
            "00COTAHIST.2024BOVESPA 20241230".ljust(245),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="PETR4",
                close_price=35.40,
                quantity=123456,
            ),
            _build_cotahist_line(
                date_yyyymmdd="20240120",
                ticker="VALE3",
                close_price=61.25,
                quantity=210000,
            ),
            "99COTAHIST.2024BOVESPA 20241230".ljust(245),
        ]
    )
    cotahist_2025 = _build_cotahist_zip(
        [
            "00COTAHIST.2025BOVESPA 20251230".ljust(245),
            _build_cotahist_line(
                date_yyyymmdd="20250120",
                ticker="PETR4",
                close_price=37.10,
                quantity=123456,
            ),
            _build_cotahist_line(
                date_yyyymmdd="20250121",
                ticker="PETR4",
                close_price=37.30,
                quantity=150000,
            ),
            "99COTAHIST.2025BOVESPA 20251230".ljust(245),
        ]
    )

    def fake_download(year: int, timeout_seconds: int = 90) -> bytes:
        if year == 2024:
            return cotahist_2024
        if year == 2025:
            return cotahist_2025
        raise AssertionError(f"Ano inesperado no teste: {year} (timeout={timeout_seconds})")

    monkeypatch.setattr(
        b3_external,
        "download_cotahist_zip",
        fake_download,
    )

    response = client.post(
        "/api/market/external/b3/sync-range",
        json={
            "user_id": user_id,
            "start_year": 2024,
            "end_year": 2025,
            "instruments": ["PETR4", "VALE3"],
            "max_days_per_instrument_per_year": 10,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2024, 2025]
    assert payload["sync_result"]["inserted"] == 4
    assert payload["sync_result"]["duplicates_ignored"] == 0
    assert payload["sync_result"]["ingested_by_instrument"]["PETR4"] == 3
    assert payload["sync_result"]["ingested_by_instrument"]["VALE3"] == 1
    assert payload["format_validation"]["matched_rows"] == 4
    assert len(payload["yearly_breakdown"]) == 2


def test_thesis_case_study_generates_kpis_and_structured_operation(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Case Study Lab",
        full_name="User Case Study",
        email="case-study@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    vale_series = [
        62.8,
        62.7,
        62.6,
        62.4,
        62.2,
        62.0,
        61.9,
        61.8,
        61.7,
        61.6,
        61.4,
        61.2,
        61.0,
        60.9,
        60.8,
        60.7,
        60.6,
        60.5,
        60.4,
        60.3,
        60.2,
        60.1,
        60.0,
        59.9,
        59.8,
        59.7,
    ]
    for index, price in enumerate(PETR4_EXTENDED_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1500 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"case-petr4-{index}",
            },
        )
    for index, price in enumerate(vale_series):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "VALE3",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1800 + index * 8,
                "currency": "BRL",
                "source_payload_id": f"case-vale3-{index}",
            },
        )

    case_response = client.post(
        "/api/theses/case-study",
        json={
            "user_id": user_id,
            "instruments": ["PETR4", "VALE3"],
            "horizon_bars": 6,
        },
    )
    assert case_response.status_code == 200
    payload = case_response.json()
    assert payload["pipeline"]["candidate_count"] >= 1
    assert payload["pipeline"]["selected_thesis_id"].startswith("TH-")
    thesis = payload["selected_case"]["thesis"]
    assert thesis["confidence_tese_pct"] >= 0
    assert thesis["success_probability_pct"] <= 100
    assert thesis["technical_support_pct"] >= 0
    assert thesis["fundamental_support_pct"] <= 100
    assert "fundamental_context" in payload["selected_case"]
    assert "thesis_raised_at" in payload["selected_case"]
    assert "suggested_entry_time" in payload["selected_case"]
    assert "suggested_exit_time" in payload["selected_case"]
    assert payload["selected_case"]["effective_result_reason"] != ""
    assert payload["selected_case"]["structured_operation"]["strategy_id"] in {
        "BULL_CALL_SPREAD",
        "BEAR_PUT_SPREAD",
        "IRON_CONDOR",
    }
    assert len(payload["selected_case"]["monitoring_timeline"]) >= 2
    assert len(payload["knowledge_skill"]["replication_playbook"]) >= 3
    assert "educacional" in payload["disclaimer"].lower()


def test_fundamentals_point_in_time_feed_signal_context(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Theta Lab",
        full_name="User Theta",
        email="theta@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras publica fato relevante com dados operacionais",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
        },
    )
    fundamentals_response = client.post(
        "/api/fundamentals/ingest",
        json={
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
        },
    )
    assert fundamentals_response.status_code == 200
    assert fundamentals_response.json()["quality_score"] > 0

    fundamentals_lookup = client.get(
        "/api/fundamentals/PETR4",
        params={"as_of": base_time.isoformat()},
    )
    assert fundamentals_lookup.status_code == 200
    assert fundamentals_lookup.json()["version_tag"] == "itr-2026q1-v1"

    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1400 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"theta-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    payload = signal_response.json()
    assert "fundamentos point-in-time" in payload["rationale"].lower()
    assert '"available": true' in payload["xai_payload"].lower()


def test_news_sentiment_endpoint_and_signal_context(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Iota Lab",
        full_name="User Iota",
        email="iota@example.com",
    )
    client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    news_response = client.post(
        "/api/news/ingest",
        json={
            "instrument": "PETR4",
            "headline": "Petrobras aprova dividendo extraordinario e guidance positivo",
            "source_name": "CVM",
            "source_type": "official",
            "published_at": base_time.isoformat(),
            "source_url": "https://example.com/cvm/petr4",
            "language": "pt-BR",
        },
    )
    assert news_response.status_code == 200
    assert news_response.json()["sentiment"]["sentiment_bias"] == "positive"

    sentiment_response = client.get(
        "/api/news/sentiment/PETR4",
        params={"as_of": (base_time + timedelta(days=2)).isoformat()},
    )
    assert sentiment_response.status_code == 200
    sentiment_payload = sentiment_response.json()
    assert sentiment_payload["article_count"] >= 1
    assert sentiment_payload["weighted_sentiment"] > 0

    for index, price in enumerate(PETR4_SERIES):
        client.post(
            "/api/market/ticks/ingest",
            json={
                "instrument": "PETR4",
                "provider": "demo-primary",
                "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                "price": price,
                "volume": 1300 + index * 10,
                "currency": "BRL",
                "source_payload_id": f"iota-tick-{index}",
            },
        )
    client.post("/api/analysis/indicators/recompute", json={"instrument": "PETR4"})
    signal_response = client.post(
        "/api/signals/generate",
        json={"user_id": user_id, "instrument": "PETR4"},
    )
    assert signal_response.status_code == 200
    payload = signal_response.json()
    assert "sentimento agregado" in payload["rationale"].lower()
    assert '"sentiment_bias": "positive"' in payload["xai_payload"].lower()


def test_thesis_game_simulation_generates_ten_theses_and_leaderboard(client) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Game Lab",
        full_name="User Game",
        email="game@example.com",
    )
    suitability_response = client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    assert suitability_response.status_code == 200

    base_time = datetime(2026, 4, 20, 10, 0, tzinfo=UTC)
    instruments = ["PETR4", "VALE3", "ITUB4", "B3SA3", "WEGE3"]
    for index in range(42):
        prices = {
            "PETR4": round(35.0 + (index * 0.19) + (0.08 if index % 3 == 0 else -0.03), 4),
            "VALE3": round(64.0 - (index * 0.16) + (0.05 if index % 5 == 0 else -0.04), 4),
            "ITUB4": round(29.5 + ((index % 6) - 3) * 0.07 + (index * 0.01), 4),
            "B3SA3": round(12.4 + (index * 0.11) + ((index % 4) * 0.02), 4),
            "WEGE3": round(42.5 + (index * 0.14) - ((index % 7) * 0.03), 4),
        }
        for instrument in instruments:
            ingest_response = client.post(
                "/api/market/ticks/ingest",
                json={
                    "instrument": instrument,
                    "provider": "demo-primary",
                    "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                    "price": prices[instrument],
                    "volume": 1000 + index * 12,
                    "currency": "BRL",
                    "source_payload_id": f"game-{instrument}-{index}",
                },
            )
            assert ingest_response.status_code == 200

    simulation_response = client.post(
        "/api/theses/game-simulation",
        json={
            "user_id": user_id,
            "instruments": instruments,
            "horizon_bars": 6,
            "thesis_count": 10,
        },
    )
    assert simulation_response.status_code == 200
    payload = simulation_response.json()
    assert payload["thesis_count"] == 10
    assert len(payload["theses"]) == 10
    assert len(payload["players"]) == 2
    assert {player["name"] for player in payload["players"]} == {"Andre", "Enzo"}
    assert payload["winner"]["name"] in {"Andre", "Enzo"}
    assert len(payload["leaderboard"]) == 2
    assert payload["leaderboard"][0]["final_capital"] >= payload["leaderboard"][1]["final_capital"]
    for thesis in payload["theses"]:
        assert thesis["thesis_id"].startswith("TH-")
        assert thesis["suggested_entry_time"] <= thesis["suggested_exit_time"]
        assert len(thesis["options"]) == 3
        assert {option["option_id"] for option in thesis["options"]} == {"A", "B", "C"}
    for player in payload["players"]:
        assert len(player["steps"]) == 10
        assert player["initial_capital"] > 0
        assert player["final_capital"] > 0


def test_thesis_game_playbook_returns_context_and_five_theses(client, monkeypatch) -> None:
    user_id = signup_and_authenticate(
        client,
        tenant_name="Game Playbook Lab",
        full_name="User Game Playbook",
        email="game-playbook@example.com",
    )
    suitability_response = client.post(
        "/api/suitability",
        json={
            "user_id": user_id,
            "time_horizon": "medio",
            "risk_tolerance": "media",
            "liquidity_need": "media",
            "investment_experience": "intermediaria",
        },
    )
    assert suitability_response.status_code == 200

    def fake_context(reference_time: str, instrument: str | None = None):  # noqa: ANN001
        return {
            "reference_date": reference_time[:10],
            "event_year": 2008,
            "event_title": "2008: Exemplo de contexto historico",
            "event_summary": f"Contexto fake para {instrument or 'mercado'}.",
            "source_name": "test-source",
            "source_url": "https://example.com/context",
            "images": [
                {
                    "url": "https://example.com/img-1.png",
                    "caption": "Imagem 1",
                    "source_url": "https://example.com/img-1",
                }
            ],
        }

    monkeypatch.setattr("app.services.game_playbook.context_for_reference_time", fake_context)

    base_time = datetime(2026, 4, 20, 10, 0, tzinfo=UTC)
    instruments = ["PETR4", "VALE3", "ITUB4", "B3SA3", "WEGE3"]
    for index in range(38):
        prices = {
            "PETR4": round(35.0 + (index * 0.16) + (0.04 if index % 4 == 0 else -0.02), 4),
            "VALE3": round(62.0 - (index * 0.13) + (0.02 if index % 5 == 0 else -0.03), 4),
            "ITUB4": round(29.0 + ((index % 6) - 2) * 0.06 + (index * 0.01), 4),
            "B3SA3": round(13.0 + (index * 0.08) + ((index % 3) * 0.01), 4),
            "WEGE3": round(41.0 + (index * 0.12) - ((index % 7) * 0.03), 4),
        }
        for instrument in instruments:
            ingest_response = client.post(
                "/api/market/ticks/ingest",
                json={
                    "instrument": instrument,
                    "provider": "demo-primary",
                    "event_time": (base_time + timedelta(minutes=index)).isoformat(),
                    "price": prices[instrument],
                    "volume": 900 + index * 9,
                    "currency": "BRL",
                    "source_payload_id": f"playbook-{instrument}-{index}",
                },
            )
            assert ingest_response.status_code == 200

    playbook_response = client.post(
        "/api/theses/game-playbook",
        json={
            "user_id": user_id,
            "instruments": instruments,
            "horizon_bars": 6,
            "thesis_count": 5,
            "player_initial_capital": 100000,
        },
    )
    assert playbook_response.status_code == 200
    payload = playbook_response.json()
    assert payload["thesis_count"] == 5
    assert len(payload["theses"]) == 5
    assert payload["player_initial_capital"] == 100000
    for thesis in payload["theses"]:
        assert thesis["thesis_id"].startswith("TH-")
        assert thesis["thesis_statement"] != ""
        assert thesis["objective"] != ""
        assert thesis["suggested_operation"]["option_id"] == "A"
        assert len(thesis["options"]) == 3
        assert thesis["context"]["event_title"].startswith("2008:")
        assert len(thesis["context"]["images"]) == 1

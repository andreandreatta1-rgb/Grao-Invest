from __future__ import annotations

from app.services.thesis_current_by_front_job import (
    FrontConfig,
    FrontRunResult,
    build_current_by_front_job_markdown,
    default_front_configs,
    merge_front_monitor_payloads,
    run_current_thesis_by_front_job,
    trim_payload_theses_for_front,
)


def _payload(
    *,
    thesis_count: int,
    theses: list[dict[str, object]],
    candidate_count: int,
    current_candidate_count: int,
) -> dict[str, object]:
    return {
        "generated_at": "2026-05-02T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 2000,
        "thesis_count": thesis_count,
        "scan_scope": {
            "instruments": [str(item["instrument"]) for item in theses],
            "tick_count": 100 * thesis_count,
            "candidate_count": candidate_count,
            "policy_candidate_count": candidate_count - 1,
            "current_candidate_count": current_candidate_count,
        },
        "summary": {
            "target_hits": sum(
                1 for item in theses if str(item.get("monitor_status")) == "target_hit"
            ),
            "stop_alerts": sum(
                1 for item in theses if str(item.get("monitor_status")) == "stop_alert"
            ),
            "monitoring_count": sum(
                1 for item in theses if str(item.get("monitor_status")) == "monitoring"
            ),
            "avg_unrealized_financial_pct": 0,
            "executive_status_counts": {"mantida": thesis_count},
            "needs_attention_count": 0,
        },
        "theses": theses,
        "disclaimer": "simulado",
    }


def test_merge_front_monitor_payloads_combines_counts_and_tags_each_thesis() -> None:
    b3_payload = _payload(
        thesis_count=2,
        candidate_count=11,
        current_candidate_count=5,
        theses=[
            {
                "thesis_id": "B3-1",
                "instrument": "PETR4",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 1.0,
            },
            {
                "thesis_id": "B3-2",
                "instrument": "VALE3",
                "monitor_status": "target_hit",
                "unrealized_financial_pct": 3.0,
            },
        ],
    )
    crypto_payload = _payload(
        thesis_count=1,
        candidate_count=7,
        current_candidate_count=2,
        theses=[
            {
                "thesis_id": "CR-1",
                "instrument": "BTCUSDT",
                "monitor_status": "stop_alert",
                "unrealized_financial_pct": -2.0,
            }
        ],
    )

    merged = merge_front_monitor_payloads(
        user_id=1,
        horizon_bars=8,
        recent_bars_window=2000,
        generated_at="2026-05-02T21:00:00+00:00",
        front_results=[
            FrontRunResult(
                front_id="acoes_b3",
                label="Acoes B3",
                instruments=["PETR4", "VALE3"],
                payload=b3_payload,
                error="",
            ),
            FrontRunResult(
                front_id="cripto",
                label="Cripto",
                instruments=["BTCUSDT"],
                payload=crypto_payload,
                error="",
            ),
        ],
    )

    assert merged["generated_at"] == "2026-05-02T21:00:00+00:00"
    assert merged["thesis_count"] == 3
    assert merged["summary"]["target_hits"] == 1
    assert merged["summary"]["stop_alerts"] == 1
    assert merged["summary"]["monitoring_count"] == 1
    assert merged["summary"]["avg_unrealized_financial_pct"] == 0.6667
    assert merged["scan_scope"]["candidate_count"] == 18
    assert merged["scan_scope"]["current_candidate_count"] == 7
    assert merged["scan_scope"]["fronts"]["acoes_b3"]["thesis_count"] == 2
    assert merged["scan_scope"]["fronts"]["cripto"]["thesis_count"] == 1
    assert [item["asset_front"] for item in merged["theses"]] == [
        "acoes_b3",
        "acoes_b3",
        "cripto",
    ]
    assert [item["front_label"] for item in merged["theses"]] == [
        "Acoes B3",
        "Acoes B3",
        "Cripto",
    ]


def test_merge_front_monitor_payloads_keeps_front_errors_visible() -> None:
    merged = merge_front_monitor_payloads(
        user_id=1,
        horizon_bars=8,
        recent_bars_window=2000,
        generated_at="2026-05-02T21:00:00+00:00",
        front_results=[
            FrontRunResult(
                front_id="cripto",
                label="Cripto",
                instruments=["BTCUSDT"],
                payload=None,
                error="Nenhuma tese atual encontrada no recorte configurado.",
            )
        ],
    )

    assert merged["thesis_count"] == 0
    assert merged["summary"]["front_errors"]["cripto"].startswith("Nenhuma tese atual")
    assert merged["scan_scope"]["fronts"]["cripto"]["error"].startswith("Nenhuma tese atual")
    assert merged["data_quality"]["status"] == "no_fresh_market_data"


def test_trim_payload_theses_for_front_prioritizes_one_thesis_per_instrument() -> None:
    payload = _payload(
        thesis_count=4,
        candidate_count=20,
        current_candidate_count=10,
        theses=[
            {
                "thesis_id": "P-1",
                "instrument": "PETR4",
                "monitor_status": "target_hit",
                "unrealized_financial_pct": 5.4,
                "executive_status": "revisar_saida",
            },
            {
                "thesis_id": "P-2",
                "instrument": "PETR4",
                "monitor_status": "target_hit",
                "unrealized_financial_pct": 5.1,
                "executive_status": "revisar_saida",
            },
            {
                "thesis_id": "V-1",
                "instrument": "VALE3",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 1.0,
                "executive_status": "mantida",
            },
            {
                "thesis_id": "I-1",
                "instrument": "ITUB4",
                "monitor_status": "stop_alert",
                "unrealized_financial_pct": -2.0,
                "executive_status": "invalidada",
            },
        ],
    )

    trimmed = trim_payload_theses_for_front(payload, max_theses=3)

    assert [item["thesis_id"] for item in trimmed["theses"]] == ["P-1", "V-1", "I-1"]
    assert trimmed["thesis_count"] == 3
    assert trimmed["summary"]["target_hits"] == 1
    assert trimmed["summary"]["stop_alerts"] == 1
    assert trimmed["summary"]["monitoring_count"] == 1
    assert trimmed["summary"]["avg_unrealized_financial_pct"] == 1.4667
    assert trimmed["summary"]["executive_status_counts"] == {
        "revisar_saida": 1,
        "mantida": 1,
        "invalidada": 1,
    }
    assert trimmed["summary"]["needs_attention_count"] == 2


def test_trim_payload_theses_for_front_promotes_overflow_into_scanner_candidates() -> None:
    payload = _payload(
        thesis_count=4,
        candidate_count=20,
        current_candidate_count=10,
        theses=[
            {
                "thesis_id": "BTC-1",
                "instrument": "BTCUSDT",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 1.6,
                "executive_status": "mantida",
            },
            {
                "thesis_id": "ETH-1",
                "instrument": "ETHUSDT",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 1.1,
                "executive_status": "mantida",
            },
            {
                "thesis_id": "SOL-1",
                "instrument": "SOLUSDT",
                "monitor_status": "confirming",
                "unrealized_financial_pct": 0.7,
                "executive_status": "atencao",
            },
            {
                "thesis_id": "BNB-1",
                "instrument": "BNBUSDT",
                "monitor_status": "confirming",
                "unrealized_financial_pct": 0.3,
                "executive_status": "mantida",
            },
        ],
    )

    trimmed = trim_payload_theses_for_front(payload, max_theses=2)

    assert [item["thesis_id"] for item in trimmed["theses"]] == ["BTC-1", "ETH-1"]
    assert [item["thesis_id"] for item in trimmed["scan_scope"]["scanner_candidates"]] == [
        "SOL-1",
        "BNB-1",
    ]
    assert trimmed["scan_scope"]["scanner_candidate_count"] == 2


def test_default_front_configs_expand_crypto_coverage() -> None:
    crypto_front = next(front for front in default_front_configs() if front.front_id == "cripto")

    assert len(crypto_front.instruments) == 10
    assert crypto_front.instruments[:3] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert {
        "BNBUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "LINKUSDT",
        "LTCUSDT",
    }.issubset(set(crypto_front.instruments))


def test_current_by_front_job_reuses_previous_crypto_front_when_feed_is_stale(monkeypatch) -> None:
    persisted: list[dict[str, object]] = []
    db_stub = type("DbStub", (), {"scalars": lambda self, *args, **kwargs: None})()

    latest_b3_payload = _payload(
        thesis_count=1,
        candidate_count=4,
        current_candidate_count=1,
        theses=[
            {
                "thesis_id": "B3-NEW",
                "instrument": "PETR4",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 0.9,
                "executive_status": "mantida",
            }
        ],
    )
    previous_payload = {
        "generated_at": "2026-05-02T20:00:00+00:00",
        "user_id": 1,
        "horizon_bars": 8,
        "recent_bars_window": 30,
        "thesis_count": 1,
        "scan_scope": {
            "fronts": {
                "cripto": {
                    "label": "Cripto",
                    "instruments": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                    "thesis_count": 1,
                    "tick_count": 120,
                    "candidate_count": 8,
                    "policy_candidate_count": 6,
                    "current_candidate_count": 3,
                    "scanner_candidate_count": 1,
                    "scanner_candidates": [
                        {
                            "thesis_id": "CR-SCAN-1",
                            "instrument": "ETHUSDT",
                            "monitor_status": "monitoring",
                            "unrealized_financial_pct": 0.4,
                            "asset_front": "cripto",
                            "front_label": "Cripto",
                        }
                    ],
                    "data_quality": {
                        "status": "fresh",
                    },
                }
            }
        },
        "summary": {
            "target_hits": 0,
            "stop_alerts": 0,
            "monitoring_count": 1,
            "avg_unrealized_financial_pct": 0.6,
            "executive_status_counts": {"mantida": 1},
            "needs_attention_count": 0,
            "front_errors": {},
        },
        "theses": [
            {
                "thesis_id": "CR-OLD",
                "instrument": "BTCUSDT",
                "monitor_status": "monitoring",
                "unrealized_financial_pct": 0.6,
                "asset_front": "cripto",
                "front_label": "Cripto",
                "executive_status": "mantida",
            }
        ],
        "disclaimer": "simulado",
    }

    def fake_run_current_thesis_monitor(*args, **kwargs) -> dict[str, object]:
        instruments = kwargs.get("instruments") or []
        if any(str(item).endswith("USDT") for item in instruments):
            raise ValueError("Nao ha dados de mercado frescos para monitorar teses atuais.")
        return latest_b3_payload

    monkeypatch.setattr(
        "app.services.thesis_current_by_front_job.run_current_thesis_monitor",
        fake_run_current_thesis_monitor,
    )
    monkeypatch.setattr(
        "app.services.thesis_current_by_front_job.load_latest_current_thesis_monitor",
        lambda db, user_id, include_bundled_bootstrap=False: previous_payload,
    )
    monkeypatch.setattr(
        "app.services.thesis_current_by_front_job.persist_current_thesis_monitor_snapshot",
        lambda db, payload, *, user_id: persisted.append(payload),
    )

    merged = run_current_thesis_by_front_job(
        db_stub,  # type: ignore[arg-type]
        user_id=1,
        fronts=[
            FrontConfig(
                front_id="acoes_b3",
                label="Acoes B3",
                instruments=["PETR4"],
            ),
            FrontConfig(
                front_id="cripto",
                label="Cripto",
                instruments=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            ),
        ],
    )

    assert merged["data_quality"]["status"] == "partial"
    assert merged["scan_scope"]["fronts"]["cripto"]["data_quality"]["status"] == "stale_reused"
    assert merged["scan_scope"]["fronts"]["cripto"]["scanner_candidate_count"] == 1
    assert [item["thesis_id"] for item in merged["theses"] if item["asset_front"] == "cripto"] == [
        "CR-OLD"
    ]
    assert [item["thesis_id"] for item in merged["scan_scope"]["scanner_candidates"]] == [
        "CR-SCAN-1"
    ]
    assert persisted[-1]["scan_scope"]["fronts"]["cripto"]["data_quality"]["status"] == "stale_reused"


def test_build_current_by_front_job_markdown_renders_front_summary() -> None:
    merged = merge_front_monitor_payloads(
        user_id=1,
        horizon_bars=8,
        recent_bars_window=2000,
        generated_at="2026-05-02T21:00:00+00:00",
        front_results=[
            FrontRunResult(
                front_id="acoes_b3",
                label="Acoes B3",
                instruments=["PETR4"],
                payload=_payload(
                    thesis_count=1,
                    candidate_count=4,
                    current_candidate_count=1,
                    theses=[
                        {
                            "thesis_id": "B3-1",
                            "instrument": "PETR4",
                            "monitor_status": "monitoring",
                            "unrealized_financial_pct": 1.0,
                        }
                    ],
                ),
                error="",
            )
        ],
    )

    markdown = build_current_by_front_job_markdown(merged)

    assert "# Current Thesis By Front Job" in markdown
    assert "Acoes B3" in markdown
    assert "PETR4" in markdown
    assert "monitoring" in markdown


def test_current_by_front_job_uses_inferred_freshness_by_default(monkeypatch) -> None:
    captured_max_age_days: list[int | None] = []

    def fake_run_current_thesis_monitor(*args, **kwargs) -> dict[str, object]:
        captured_max_age_days.append(kwargs.get("max_latest_age_days"))
        return _payload(
            thesis_count=1,
            candidate_count=4,
            current_candidate_count=1,
            theses=[
                {
                    "thesis_id": "CR-1",
                    "instrument": "BTCUSDT",
                    "monitor_status": "monitoring",
                    "unrealized_financial_pct": 1.0,
                    "executive_status": "mantida",
                }
            ],
        )

    monkeypatch.setattr(
        "app.services.thesis_current_by_front_job.run_current_thesis_monitor",
        fake_run_current_thesis_monitor,
    )
    monkeypatch.setattr(
        "app.services.thesis_current_by_front_job.persist_current_thesis_monitor_snapshot",
        lambda *args, **kwargs: None,
    )

    run_current_thesis_by_front_job(
        object(),  # type: ignore[arg-type]
        user_id=1,
        fronts=[
            FrontConfig(
                front_id="cripto",
                label="Cripto",
                instruments=["BTCUSDT"],
            )
        ],
    )

    assert captured_max_age_days == [0]

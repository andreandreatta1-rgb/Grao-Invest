from __future__ import annotations

from datetime import UTC, datetime

from scripts import run_grao_ops_guard as guard


def test_market_feed_stage_blocks_stale_fronts(monkeypatch) -> None:
    now = datetime(2026, 5, 8, tzinfo=UTC)

    def fake_latest_ticks_for(instruments: list[str]) -> dict[str, object]:
        latest_event_time = (
            "2026-04-22T20:46:19+00:00"
            if "PETR4" in instruments
            else "2026-05-02T20:14:59+00:00"
        )
        return {
            "count": 10,
            "instrument_count": 1,
            "requested_instrument_count": len(instruments),
            "latest_event_time": latest_event_time,
            "latest_ingest_time": latest_event_time,
            "providers": [{"provider": "stub", "count": 10}],
        }

    monkeypatch.setattr(guard, "latest_ticks_for", fake_latest_ticks_for)

    stage = guard.market_feed_stage(
        now=now,
        max_b3_age_days=4.0,
        max_crypto_age_days=1.0,
    )

    assert stage["status"] == "blocked"
    assert stage["stale_fronts"] == ["b3", "crypto"]
    assert stage["fronts"]["b3"]["age_days"] > 4.0
    assert stage["fronts"]["crypto"]["age_days"] > 1.0


def test_blocked_ops_guard_recommends_not_forcing_publication() -> None:
    stages = {
        "scheduler": guard.stage("ok", "scheduler ok"),
        "market_feed": guard.stage("blocked", "feed stale"),
        "current_thesis_generator": guard.stage("blocked", "no fresh data"),
        "dashboard_seed": guard.stage("ok", "seed ok"),
    }

    assert guard.overall_status(stages) == "blocked"
    assert guard.recommended_actions(stages) == [
        "Atualizar feed B3/Cripto antes de esperar novas teses atuais.",
        "Nao forcar publicacao: o bloqueio protege contra tese atual com dado velho.",
    ]


def test_dashboard_safe_payload_removes_local_scheduler_paths() -> None:
    payload = {
        "status": "blocked",
        "stages": {
            "scheduler": {
                "status": "ok",
                "details": {
                    "status": "ok",
                    "repo_root": "C:/Users/Example/OneDrive/ProjectOne",
                    "tasks": [
                        {
                            "task_name": "GraoInvest-B3-01",
                            "ok": True,
                            "arguments": '-File "C:/Users/Example/script.ps1"',
                            "working_directory": "C:/Users/Example/ProjectOne",
                            "last_task_result": 0,
                        }
                    ],
                },
            }
        },
    }

    safe = guard.dashboard_safe_payload(payload)

    details = safe["stages"]["scheduler"]["details"]
    assert details["task_count"] == 1
    assert details["tasks"] == [
        {"task_name": "GraoInvest-B3-01", "ok": True, "last_task_result": 0}
    ]
    assert "repo_root" not in details
    assert "arguments" not in details["tasks"][0]
    assert "working_directory" not in details["tasks"][0]

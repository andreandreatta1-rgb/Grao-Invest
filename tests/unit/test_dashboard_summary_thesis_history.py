from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager

from app.db import get_db
from app.main import app
from app.models import AuditEvent
from sqlalchemy.orm import Session


@contextmanager
def _testing_db_session() -> Generator[Session]:
    override = app.dependency_overrides[get_db]
    db_gen = override()
    db = next(db_gen)
    try:
        yield db
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def _record_event(
    db: Session,
    event_type: str,
    details: dict[str, object],
    created_at: str,
) -> None:
    db.add(
        AuditEvent(
            user_id=1,
            event_type=event_type,
            details=json.dumps(details),
            created_at=created_at,
        )
    )


def test_thesis_history_uses_resolved_case_studies_not_open_monitor_snapshots(client) -> None:
    with _testing_db_session() as db:
        _record_event(
            db,
            "thesis.case_study.generated",
            {
                "user_id": 1,
                "selected_thesis_id": "case-win",
                "strategy_id": "BULL_CALL_SPREAD",
                "policy_name": "anti_blindspot_v3_soft",
                "expected_financial_pct": 4.0,
                "realized_financial_pct": 3.5,
            },
            "2026-05-01T10:00:00+00:00",
        )
        _record_event(
            db,
            "thesis.case_study.generated",
            {
                "user_id": 1,
                "selected_thesis_id": "case-loss",
                "strategy_id": "BULL_CALL_SPREAD",
                "policy_name": "anti_blindspot_v3_soft",
                "expected_financial_pct": 4.0,
                "realized_financial_pct": -1.0,
            },
            "2026-05-01T11:00:00+00:00",
        )
        for hour in (12, 13):
            _record_event(
                db,
                "thesis.current_monitor.generated",
                {
                    "user_id": 1,
                    "thesis_count": 40,
                    "target_hits": 0,
                    "stop_alerts": 0,
                    "avg_unrealized_financial_pct": 0.6,
                    "executive_status_counts": {"atencao": 40},
                    "payload": {
                        "summary": {
                            "target_hits": 0,
                            "stop_alerts": 0,
                            "monitoring_count": 40,
                            "avg_unrealized_financial_pct": 0.6,
                        },
                        "theses": [
                            {
                                "thesis_id": f"open-{index}",
                                "monitor_status": "monitoring",
                                "unrealized_financial_pct": 0.6,
                            }
                            for index in range(40)
                        ],
                    },
                },
                f"2026-05-01T{hour}:00:00+00:00",
            )
        db.commit()

    response = client.get("/api/dashboard/summary/1")

    assert response.status_code == 200
    overview = response.json()["thesis_history_overview"]
    assert overview["total_tested"] == 2
    assert overview["success_count"] == 1
    assert overview["success_rate_pct"] == 50.0
    assert overview["sources"]["case_study_runs"] == 2
    assert overview["sources"]["current_monitor_runs"] == 2
    assert overview["sample_quality"]["counting_policy"] == "unique_resolved_case_studies"
    assert overview["sample_quality"]["current_monitor_snapshots_excluded"] == 2


def test_thesis_history_deduplicates_replayed_case_study_events(client) -> None:
    with _testing_db_session() as db:
        for minute in (0, 30):
            _record_event(
                db,
                "thesis.case_study.generated",
                {
                    "user_id": 1,
                    "selected_thesis_id": "case-replayed",
                    "strategy_id": "BULL_CALL_SPREAD",
                    "policy_name": "anti_blindspot_v3_soft",
                    "expected_financial_pct": 4.0,
                    "realized_financial_pct": 3.5,
                },
                f"2026-05-02T10:{minute:02d}:00+00:00",
            )
        db.commit()

    response = client.get("/api/dashboard/summary/1")

    assert response.status_code == 200
    overview = response.json()["thesis_history_overview"]
    assert overview["total_tested"] == 1
    assert overview["success_count"] == 1
    assert overview["success_rate_pct"] == 100.0
    assert overview["sources"]["case_study_runs"] == 1
    assert overview["sample_quality"]["raw_case_study_events"] == 2
    assert overview["sample_quality"]["duplicate_case_study_events_excluded"] == 1

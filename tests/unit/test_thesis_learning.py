from __future__ import annotations

import json
from pathlib import Path

from app.db import Base
from app.services.thesis_learning import run_thesis_skill_learning_cycle
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def test_thesis_learning_cycle_generates_profile_and_blindspots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    session_local = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    db: Session = session_local()
    try:
        records = []
        for index in range(30):
            high_vol = index < 15
            success = index >= 12
            records.append(
                {
                    "thesis_id": f"T-{index}",
                    "instrument": "PETR4",
                    "direction": "bullish",
                    "confidence_tese_pct": 70.0,
                    "expected_financial_pct": 3.5,
                    "realized_financial_pct": -1.0 if not success else 1.2,
                    "success": success,
                    "support_rate_pct": 42.0 if high_vol else 60.0,
                    "technical_support_pct": 68.0,
                    "fundamental_support_pct": 50.0,
                    "news_support_pct": 48.0 if high_vol else 58.0,
                    "fundamental_available": False if high_vol else True,
                    "news_available": True,
                    "geo_oil_available": True,
                    "volatility_pct": 3.2 if high_vol else 1.4,
                }
            )

        monkeypatch.setattr(
            "app.services.thesis_learning._learning_records",
            lambda *args, **kwargs: (records, ["PETR4"]),  # noqa: ARG005
        )

        output_path = tmp_path / "thesis_skill_profile.json"
        payload = run_thesis_skill_learning_cycle(
            db,
            user_id=1,
            instruments=["PETR4"],
            horizon_bars=12,
            max_candidates=200,
            profile_path=output_path,
        )

        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["sample_size"] == 30
        assert "calibration" in saved
        assert any(rule["condition"] == "high_volatility" for rule in saved["blindspots"])
        assert payload["summary"]["blindspot_count"] >= 1
    finally:
        db.close()

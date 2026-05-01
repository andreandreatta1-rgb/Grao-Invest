from __future__ import annotations

from app.models import FundamentalSnapshot
from app.services.fundamentals import summarize_fundamental_quality


def test_summarize_fundamental_quality() -> None:
    snapshot = FundamentalSnapshot(
        instrument="PETR4",
        source_name="CVM",
        source_type="regulatory",
        reference_time="2026-03-31T00:00:00+00:00",
        availability_time="2026-05-15T00:00:00+00:00",
        pe_ratio=9.5,
        pb_ratio=1.6,
        ev_ebitda=7.2,
        dividend_yield=6.1,
        roe=17.0,
        net_margin=13.0,
        revenue_growth=8.5,
        payout_ratio=40.0,
        version_tag="itr-2026q1-v1",
    )
    summary = summarize_fundamental_quality(snapshot)
    assert summary["value_score"] > 0.3
    assert summary["quality_score"] > 0.3

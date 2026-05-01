from __future__ import annotations

from app.models import FundamentalSnapshot
from app.schemas import FundamentalIngestRequest
from app.services.audit import record_audit_event
from app.services.utils import isoformat
from sqlalchemy import select
from sqlalchemy.orm import Session


def ingest_fundamentals(db: Session, payload: FundamentalIngestRequest) -> FundamentalSnapshot:
    if payload.availability_time < payload.reference_time:
        raise ValueError("availability_time nao pode ser anterior a reference_time")

    instrument = payload.instrument.upper()
    reference_time = isoformat(payload.reference_time)
    availability_time = isoformat(payload.availability_time)
    existing = db.scalar(
        select(FundamentalSnapshot)
        .where(FundamentalSnapshot.instrument == instrument)
        .where(FundamentalSnapshot.source_name == payload.source_name)
        .where(FundamentalSnapshot.source_type == payload.source_type)
        .where(FundamentalSnapshot.reference_time == reference_time)
        .where(FundamentalSnapshot.availability_time == availability_time)
        .where(FundamentalSnapshot.version_tag == payload.version_tag)
        .order_by(FundamentalSnapshot.id.desc())
        .limit(1)
    )
    if existing is not None:
        record_audit_event(
            db,
            "fundamentals.snapshot.duplicate_ignored",
            {
                "instrument": existing.instrument,
                "reference_time": existing.reference_time,
                "availability_time": existing.availability_time,
                "version_tag": existing.version_tag,
                "fundamental_id": existing.id,
            },
        )
        return existing

    snapshot = FundamentalSnapshot(
        instrument=instrument,
        source_name=payload.source_name,
        source_type=payload.source_type,
        reference_time=reference_time,
        availability_time=availability_time,
        pe_ratio=payload.pe_ratio,
        pb_ratio=payload.pb_ratio,
        ev_ebitda=payload.ev_ebitda,
        dividend_yield=payload.dividend_yield,
        roe=payload.roe,
        net_margin=payload.net_margin,
        revenue_growth=payload.revenue_growth,
        payout_ratio=payload.payout_ratio,
        version_tag=payload.version_tag,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    record_audit_event(
        db,
        "fundamentals.snapshot.ingested",
        {
            "instrument": snapshot.instrument,
            "reference_time": snapshot.reference_time,
            "availability_time": snapshot.availability_time,
            "version_tag": snapshot.version_tag,
        },
    )
    return snapshot


def summarize_fundamental_quality(snapshot: FundamentalSnapshot) -> dict[str, float]:
    value_score = 0.0
    quality_score = 0.0

    if snapshot.pe_ratio <= 12:
        value_score += 0.15
    elif snapshot.pe_ratio <= 18:
        value_score += 0.08

    if snapshot.pb_ratio <= 2.0:
        value_score += 0.1
    elif snapshot.pb_ratio <= 3.0:
        value_score += 0.05

    if snapshot.ev_ebitda <= 8:
        value_score += 0.1
    elif snapshot.ev_ebitda <= 12:
        value_score += 0.05

    if snapshot.dividend_yield >= 5:
        value_score += 0.08
    elif snapshot.dividend_yield >= 3:
        value_score += 0.04

    if snapshot.roe >= 15:
        quality_score += 0.15
    elif snapshot.roe >= 10:
        quality_score += 0.08

    if snapshot.net_margin >= 12:
        quality_score += 0.12
    elif snapshot.net_margin >= 6:
        quality_score += 0.06

    if snapshot.revenue_growth >= 8:
        quality_score += 0.12
    elif snapshot.revenue_growth >= 3:
        quality_score += 0.06

    if 20 <= snapshot.payout_ratio <= 70:
        quality_score += 0.08

    return {
        "value_score": round(value_score, 4),
        "quality_score": round(quality_score, 4),
    }


def fundamentals_to_response(snapshot: FundamentalSnapshot) -> dict[str, object]:
    summary = summarize_fundamental_quality(snapshot)
    return {
        "event_type": "fundamental.snapshot.normalized.v1",
        "version": 1,
        "fundamental_id": snapshot.id,
        "instrument": snapshot.instrument,
        "source_name": snapshot.source_name,
        "source_type": snapshot.source_type,
        "reference_time": snapshot.reference_time,
        "availability_time": snapshot.availability_time,
        "pe_ratio": snapshot.pe_ratio,
        "pb_ratio": snapshot.pb_ratio,
        "ev_ebitda": snapshot.ev_ebitda,
        "dividend_yield": snapshot.dividend_yield,
        "roe": snapshot.roe,
        "net_margin": snapshot.net_margin,
        "revenue_growth": snapshot.revenue_growth,
        "payout_ratio": snapshot.payout_ratio,
        "version_tag": snapshot.version_tag,
        "value_score": summary["value_score"],
        "quality_score": summary["quality_score"],
    }

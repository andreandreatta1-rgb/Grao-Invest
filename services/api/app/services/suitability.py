from __future__ import annotations

from app.models import SuitabilityProfile
from app.schemas import SuitabilityRequest
from app.services.audit import record_audit_event
from app.services.utils import isoformat, utc_now
from sqlalchemy.orm import Session


def classify_profile(risk_tolerance: str, investment_experience: str) -> str:
    if risk_tolerance == "alta" and investment_experience in {"intermediaria", "avancada"}:
        return "arrojado"
    if risk_tolerance == "media":
        return "moderado"
    return "conservador"


def save_suitability(db: Session, payload: SuitabilityRequest) -> SuitabilityProfile:
    profile = SuitabilityProfile(
        user_id=payload.user_id,
        investor_profile=classify_profile(payload.risk_tolerance, payload.investment_experience),
        time_horizon=payload.time_horizon,
        risk_tolerance=payload.risk_tolerance,
        liquidity_need=payload.liquidity_need,
        created_at=isoformat(utc_now()),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    record_audit_event(
        db,
        "suitability.profile.created",
        {"investor_profile": profile.investor_profile},
        payload.user_id,
    )
    return profile

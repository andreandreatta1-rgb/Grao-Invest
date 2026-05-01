from __future__ import annotations

import time

from app.models import AuditEvent
from app.services.utils import isoformat, to_json, utc_now
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def _is_sqlite_lock_error(exc: OperationalError) -> bool:
    raw = str(getattr(exc, "orig", exc)).lower()
    return "database is locked" in raw


def record_audit_event(
    db: Session,
    event_type: str,
    details: dict[str, object],
    user_id: int | None = None,
    retries: int = 2,
) -> AuditEvent | None:
    for attempt in range(max(0, retries) + 1):
        event = AuditEvent(
            user_id=user_id,
            event_type=event_type,
            details=to_json(details),
            created_at=isoformat(utc_now()),
        )
        db.add(event)
        try:
            db.commit()
            db.refresh(event)
            return event
        except OperationalError as exc:
            db.rollback()
            if not _is_sqlite_lock_error(exc):
                raise
            if attempt >= retries:
                return None
            time.sleep(0.15 * (attempt + 1))
    return None

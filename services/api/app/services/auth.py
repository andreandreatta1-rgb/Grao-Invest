from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pyotp
from app.models import Consent, LoginAttemptState, Tenant, User
from app.schemas import LoginRequest, MFAVerifyRequest, SignupRequest
from app.services.audit import record_audit_event
from app.services.utils import (
    create_access_token,
    hash_password,
    isoformat,
    utc_now,
    verify_password,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

LOCKOUT_MINUTES_BY_LEVEL = {
    1: 5,
    2: 15,
    3: 60,
}


def _attempt_state(db: Session, email: str) -> LoginAttemptState | None:
    return db.scalar(select(LoginAttemptState).where(LoginAttemptState.email == email))


def _locked_until_datetime(state: LoginAttemptState) -> datetime | None:
    if state.locked_until is None:
        return None
    return datetime.fromisoformat(state.locked_until).astimezone(UTC)


def _register_failed_login(db: Session, email: str) -> LoginAttemptState:
    now = utc_now()
    state = _attempt_state(db, email)
    if state is None:
        state = LoginAttemptState(
            email=email,
            failed_attempts=0,
            lock_level=0,
            locked_until=None,
            updated_at=isoformat(now),
        )
        db.add(state)
        db.flush()

    locked_until = _locked_until_datetime(state)
    if locked_until is not None and locked_until <= now:
        state.locked_until = None

    state.failed_attempts += 1
    if state.failed_attempts >= 3:
        state.failed_attempts = 0
        state.lock_level = min(3, state.lock_level + 1)
        minutes = LOCKOUT_MINUTES_BY_LEVEL[state.lock_level]
        state.locked_until = isoformat(now + timedelta(minutes=minutes))
    state.updated_at = isoformat(now)
    db.commit()
    db.refresh(state)
    return state


def _reset_login_attempts(db: Session, email: str) -> None:
    state = _attempt_state(db, email)
    if state is None:
        return
    state.failed_attempts = 0
    state.locked_until = None
    state.updated_at = isoformat(utc_now())
    db.commit()


def issue_access_token(user: User) -> str:
    return create_access_token(
        user_id=user.id,
        email=user.email,
        mfa_enabled=user.mfa_enabled,
    )


def create_user(db: Session, payload: SignupRequest) -> User:
    if not payload.accepted_terms or not payload.accepted_privacy:
        raise ValueError("Termos e privacidade precisam ser aceitos")
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ValueError("Email ja cadastrado")
    tenant = Tenant(name=payload.tenant_name, created_at=isoformat(utc_now()))
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        created_at=isoformat(utc_now()),
    )
    db.add(user)
    db.flush()
    consent = Consent(
        user_id=user.id,
        accepted_terms=payload.accepted_terms,
        accepted_privacy=payload.accepted_privacy,
        consented_at=isoformat(utc_now()),
    )
    db.add(consent)
    db.commit()
    db.refresh(user)
    record_audit_event(
        db,
        "auth.signup.completed",
        {"email": user.email, "tenant_id": tenant.id},
        user.id,
    )
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    state = _attempt_state(db, payload.email)
    now = utc_now()
    if state is not None:
        locked_until = _locked_until_datetime(state)
        if locked_until is not None and locked_until > now:
            raise ValueError(
                "Conta temporariamente bloqueada por tentativas invalidas. "
                f"Tente novamente apos {locked_until.isoformat()}."
            )

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        failed_state = _register_failed_login(db, payload.email)
        event_payload: dict[str, object] = {
            "email": payload.email,
            "lock_level": failed_state.lock_level,
            "failed_attempts": failed_state.failed_attempts,
        }
        if failed_state.locked_until is not None:
            event_payload["locked_until"] = failed_state.locked_until
        record_audit_event(db, "auth.login.failed", event_payload)
        raise ValueError("Credenciais invalidas")

    if user.mfa_enabled:
        if payload.otp_code is None:
            raise ValueError("MFA obrigatorio para este usuario")
        totp = pyotp.TOTP(user.mfa_secret or "")
        if not totp.verify(payload.otp_code):
            failed_state = _register_failed_login(db, payload.email)
            event_payload = {
                "email": payload.email,
                "lock_level": failed_state.lock_level,
                "failed_attempts": failed_state.failed_attempts,
                "reason": "otp_invalido",
            }
            if failed_state.locked_until is not None:
                event_payload["locked_until"] = failed_state.locked_until
            record_audit_event(db, "auth.login.failed", event_payload, user.id)
            raise ValueError("Codigo MFA invalido")

    _reset_login_attempts(db, payload.email)
    record_audit_event(db, "auth.login.completed", {"email": user.email}, user.id)
    return user


def setup_mfa(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("Usuario nao encontrado")
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    db.commit()
    record_audit_event(db, "auth.mfa.setup", {"user_id": user_id}, user_id)
    return pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="AI Advisor MVP")


def verify_mfa(db: Session, payload: MFAVerifyRequest) -> User:
    user = db.get(User, payload.user_id)
    if user is None or not user.mfa_secret:
        raise ValueError("Usuario sem MFA pendente")
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(payload.otp_code):
        raise ValueError("Codigo MFA invalido")
    user.mfa_enabled = True
    db.commit()
    record_audit_event(db, "auth.mfa.enabled", {"user_id": user.id}, user.id)
    return user

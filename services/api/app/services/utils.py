from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

DISCLAIMER = (
    "Este conteudo tem finalidade exclusivamente educacional e analitica. "
    "Nao constitui recomendacao de investimento, consultoria, analise nem indicacao "
    "de compra ou venda. O investidor e responsavel por suas decisoes."
)

FORBIDDEN_COPY_TERMS = [
    "compre",
    "venda",
    "invista",
    "aplique agora",
    "entrada garantida",
    "lucro certo",
]

_PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
_TOKEN_SECRET = os.getenv("APP_TOKEN_SECRET", "dev-only-secret-change-in-production")
_TOKEN_TTL_MINUTES = 60


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerificationError, ValueError):
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def create_access_token(
    *,
    user_id: int,
    email: str,
    mfa_enabled: bool,
    ttl_minutes: int = _TOKEN_TTL_MINUTES,
) -> str:
    issued_at = int(utc_now().timestamp())
    expires_at = issued_at + (ttl_minutes * 60)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "mfa_enabled": mfa_enabled,
        "iat": issued_at,
        "exp": expires_at,
    }
    header_raw = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header_b64 = _b64url_encode(header_raw)
    payload_b64 = _b64url_encode(payload_raw)
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(_TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Token invalido") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_signature = hmac.new(
        _TOKEN_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url_encode(expected_signature), signature_b64):
        raise ValueError("Assinatura de token invalida")

    payload_raw = _b64url_decode(payload_b64).decode("utf-8")
    payload = json.loads(payload_raw)
    if not isinstance(payload, dict):
        raise ValueError("Payload de token invalido")
    normalized_payload = {str(key): value for key, value in payload.items()}
    expires_at = int(normalized_payload.get("exp", 0))
    if expires_at <= int(utc_now().timestamp()):
        raise ValueError("Token expirado")
    return normalized_payload


def access_token_ttl_seconds() -> int:
    return _TOKEN_TTL_MINUTES * 60


def anti_recommendation_text(text: str) -> str:
    lowered = text
    replacements = {
        "compre": "observe",
        "venda": "reduza exposicao se o seu plano permitir",
        "invista": "avalie com criterio",
        "aplique agora": "avalie o momento com criterio",
        "entrada garantida": "cenario sem garantia",
        "lucro certo": "resultado incerto",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
        lowered = lowered.replace(source.capitalize(), target.capitalize())
    return lowered


def assert_compliant_copy(text: str) -> None:
    lowered = text.lower()
    violations = [term for term in FORBIDDEN_COPY_TERMS if term in lowered]
    if violations:
        joined = ", ".join(violations)
        raise ValueError(f"Copy contem termos proibidos: {joined}")


def to_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True)

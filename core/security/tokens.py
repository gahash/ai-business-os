import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from core.config.settings import get_settings

ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or signed with the wrong key."""


def create_access_token(*, user_id: str, tenant_id: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError("invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise TokenError("not an access token")
    return payload


def generate_opaque_token() -> str:
    """High-entropy opaque token for refresh tokens and password-reset tokens: the raw value is
    handed to the client/caller once and never stored — only `hash_opaque_token` of it is."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

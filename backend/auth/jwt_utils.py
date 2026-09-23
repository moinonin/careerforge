from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.config import settings
from jose import jwt
from passlib.context import CryptContext

# ── Password hashing ────────────────────────────────────────────────────────

pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__time_cost=3,
    argon2__memory_cost=64 * 1024,
    argon2__parallelism=4,
    deprecated="auto",
)


def hash_password(plain: str) -> str:
    """Argon2id hash of a raw password."""
    return pwd_context.hash(plain)  # type: ignore[no-any-return]


def verify_password(plain: str, hashed: str) -> bool:
    """True when *plain* matches the stored *hashed* password."""
    return pwd_context.verify(plain, hashed)  # type: ignore[no-any-return]


# ── JWT helpers ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """Short-lived JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)  # type: ignore[no-any-return]


def create_refresh_token(user_id: str) -> str:
    """Long-lived refresh token (opaque random in production; JWT here for tooling)."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)  # type: ignore[no-any-return]


def create_reset_token(user_id: str) -> str:
    """Short-lived single-use reset token (JWT with type='reset')."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "reset",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)  # type: ignore[no-any-return]


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode and validate a JWT. Raises on expired/invalid tokens."""
    payload = jwt.decode(  # type: ignore[no-any-return]
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise ValueError(f"Token type mismatch: expected {expected_type!r}")
    return payload  # type: ignore[no-any-return]


def get_user_id_from_token(token: str) -> str:
    """Extract the user id from an access token. Raises on invalid/expired."""
    payload = decode_token(token, expected_type="access")
    return payload["sub"]  # type: ignore[no-any-return]

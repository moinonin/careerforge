from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from backend import models
from backend.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

EXPIRES_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _now_iso() -> str:
    return datetime.now(UTC).strftime(EXPIRES_AT_FORMAT)


def _new_id() -> str:
    return str(uuid.uuid4())


async def signup(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str | None,
) -> models.User:
    """Register a new user, hash the password, and initialize the 14-day trial."""
    existing = await session.execute(
        select(models.User).where(models.User.email == email)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("A user with this email already exists")

    password_hash = hash_password(password)
    trial_ends_at = datetime.now(UTC) + timedelta(days=14)

    user = models.User(
        id=_new_id(),
        email=email,
        password_hash=password_hash,
        full_name=full_name or email.split("@")[0],
        role="user",
        created_at=datetime.now(UTC),
    )
    session.add(user)

    subscription = models.Subscription(
        id=_new_id(),
        user=user,
        plan_tier="trial",
        status="trialing",
        trial_ends_at=trial_ends_at,
        credits_remaining=2,
        storage_quota_bytes=5_242_880,
    )
    session.add(subscription)
    await session.flush()
    await session.refresh(user)
    return user


async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[models.User, str, str]:
    """Authenticate a user and return (user, access_token, refresh_token)."""
    stmt = (
        select(models.User)
        .where(models.User.email == email)
        .options(selectinload(models.User.subscription))
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("Invalid email or password")

    if not user.password_hash or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    access_token = create_access_token(str(user.id), user.email)
    refresh_token = create_refresh_token(str(user.id))

    # Store refresh token in DB for rotation + revocation
    token_record = models.RefreshToken(
        id=_new_id(),
        user_id=str(user.id),
        token_hash=refresh_token,
        revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(token_record)
    await session.flush()

    return user, access_token, refresh_token


async def refresh_access_token(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[str, str]:
    """Rotate a refresh token: invalidate the old one, issue new pair."""
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload["sub"]

    # Find and revoke the most recent matching stored refresh token
    result = await session.execute(
        select(models.RefreshToken)
        .where(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.revoked == False,  # noqa: E712
            models.RefreshToken.expires_at > datetime.now(UTC),
        )
        .order_by(models.RefreshToken.created_at.desc())
        .limit(1)
    )
    token_record = result.scalar_one_or_none()
    if token_record is None:
        raise ValueError("Invalid or expired refresh token")

    token_record.revoked = True
    await session.flush()

    new_access = create_access_token(user_id, payload.get("email", ""))
    new_refresh = create_refresh_token(user_id)

    new_record = models.RefreshToken(
        id=_new_id(),
        user_id=user_id,
        token_hash=new_refresh,
        revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(new_record)
    await session.flush()

    return new_access, new_refresh


async def revoke_refresh_token(
    session: AsyncSession,
    token: str,
    user_id: str,
) -> None:
    """Revoke a refresh token on logout."""
    decode_token(token, expected_type="refresh")
    result = await session.execute(
        select(models.RefreshToken).where(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.token_hash == token,
            models.RefreshToken.revoked == False,  # noqa: E712
        )
    )
    token_record = result.scalar_one_or_none()
    if token_record is not None:
        token_record.revoked = True
        await session.flush()


async def get_user_me(
    session: AsyncSession,
    current_user_id: str,
) -> models.User:
    """Fetch the full user object for the current user."""
    result = await session.execute(
        select(models.User)
        .where(models.User.id == current_user_id)
        .options(
            selectinload(models.User.subscription),
            selectinload(models.User.llm_configs),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    return user


async def update_user_me(
    session: AsyncSession,
    current_user_id: str,
    *,
    full_name: str | None = None,
    password: str | None = None,
    email: str | None = None,
) -> models.User:
    """Update the current user's profile."""
    user = await get_user_me(session, current_user_id)
    if user is None:
        raise ValueError("User not found")

    if full_name is not None:
        user.full_name = full_name
    if email is not None and email != user.email:
        existing = await session.execute(
            select(models.User).where(models.User.email == email)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Email already in use")
        user.email = email
    if password is not None:
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        user.password_hash = hash_password(password)

    await session.flush()
    await session.refresh(user)
    return user


async def initiate_password_reset(
    session: AsyncSession,
    email: str,
) -> str:
    """Lookup the user by email and return a reset token.

    Returns the reset token so the caller can build the reset link.  The
    caller is responsible for email delivery; this function does not send
    email itself (email is disabled in development).  Returns empty string
    if the email is not found (so the caller can emit a generic message).
    """
    result = await session.execute(
        select(models.User).where(models.User.email == email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return ""
    return create_reset_token(str(user.id))


async def reset_password(
    session: AsyncSession,
    user_id: str,
    token: str,
    new_password: str,
) -> models.User:
    """Validate a reset token and update the password."""
    payload = decode_token(token, expected_type="reset")
    if payload.get("sub") != user_id:
        raise ValueError("Reset token is not valid for this user")

    result = await session.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    if not new_password or len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")
    user.password_hash = hash_password(new_password)
    await session.flush()
    await session.refresh(user)
    return user

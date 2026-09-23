"""FastAPI dependencies — authentication, database, etc."""

from __future__ import annotations

from typing import Annotated

from backend.auth.jwt_utils import get_user_id_from_token
from backend.database import get_session
from backend.models import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

bearer = HTTPBearer(auto_error=False)

# Database dependency alias
get_db = get_session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from the JWT access token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# Alias for backward compatibility
CurrentUserId = Annotated[str, Depends(lambda user: user.id)]
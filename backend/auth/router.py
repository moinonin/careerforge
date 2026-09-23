"""Auth router — Sprint 1 (Authentication & Identity).

Endpoints:
  POST   /api/v1/auth/signup
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/logout
  POST   /api/v1/auth/forgot-password
  POST   /api/v1/auth/reset-password
  GET    /api/v1/users/me
  PUT    /api/v1/users/me
"""

from __future__ import annotations

from contextlib import suppress
from typing import Annotated

from backend.auth.jwt_utils import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
)
from backend.auth.schemas import (  # noqa: E402
    CurrentUserId,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserMeResponse,
)
from backend.auth.service import (  # noqa: E402
    get_user_me,
    initiate_password_reset,
    revoke_refresh_token,
    update_user_me,
)
from backend.auth.service import (
    login as auth_login,
)
from backend.auth.service import (
    refresh_access_token as auth_refresh,
)
from backend.auth.service import (
    reset_password as auth_reset_password,
)
from backend.auth.service import (
    signup as auth_signup,
)
from backend.config import settings  # noqa: E402
from backend.database import get_session  # noqa: E402
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["auth"])
users_router = APIRouter(tags=["users"])

bearer = HTTPBearer(auto_error=False)


# ── Helper: issue tokens for a user ──────────────────────────────────────────

def _issue_tokens(user_id: str, email: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id, email),
        refresh_token=create_refresh_token(user_id),
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ── Signup ────────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    req: SignupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    try:
        user = await auth_signup(session, req.email, req.password, req.full_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _issue_tokens(user.id, user.email)


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    try:
        user, _, _ = await auth_login(session, req.email, req.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password") from exc
    return _issue_tokens(user.id, user.email)


# ── Refresh ────────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    try:
        new_access, new_refresh = await auth_refresh(session, req.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid refresh token: {exc}") from exc
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc
    with suppress(ValueError):
        await revoke_refresh_token(session, credentials.credentials, user_id)


# ── Forgot / Reset password ────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    req: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    await initiate_password_reset(session, req.email)
    return {"status": "ok", "message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    req: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    try:
        payload = decode_token(req.token, expected_type="reset")
        user_id = payload["sub"]  # type: ignore[no-any-return]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid reset token: {exc}") from exc
    try:
        await auth_reset_password(session, user_id, req.token, req.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "ok", "message": "Password has been reset"}


# ── /users/me ────────────────────────────────────────────────────────────────

@users_router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserMeResponse:
    try:
        user = await get_user_me(session, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@users_router.put("/me", response_model=UserMeResponse)
async def update_me(
    current_user_id: CurrentUserId,
    full_name: str | None = None,
    password: str | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserMeResponse:
    try:
        user = await update_user_me(
            session, current_user_id, full_name=full_name, password=password
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )

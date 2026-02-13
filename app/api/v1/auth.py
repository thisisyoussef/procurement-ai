"""Authentication endpoints (Google sign-in + current user)."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, create_access_token, get_current_auth_user
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.repositories.user_repository import get_user_by_id, upsert_google_user
from app.schemas.auth import AuthTokenResponse, AuthUserResponse, GoogleAuthRequest

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


async def _verify_google_id_token(id_token: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google auth not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google token verification unavailable",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    payload = response.json()
    audience = payload.get("aud")
    email_verified = str(payload.get("email_verified", "")).lower() == "true"
    issuer = payload.get("iss")

    if audience != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token audience mismatch",
        )
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token issuer mismatch",
        )
    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email is not verified",
        )
    return payload


@router.post("/google", response_model=AuthTokenResponse)
async def authenticate_with_google(request: GoogleAuthRequest):
    payload = await _verify_google_id_token(request.id_token)

    email = payload.get("email")
    google_sub = payload.get("sub")
    if not email or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token missing required claims",
        )

    full_name = payload.get("name")
    avatar_url = payload.get("picture")

    try:
        async with async_session_factory() as session:
            user = await upsert_google_user(
                session,
                google_sub=str(google_sub),
                email=str(email),
                full_name=full_name,
                avatar_url=avatar_url,
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to upsert Google user")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User store unavailable",
        ) from exc

    auth_user = AuthUser(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
    )
    access_token, expires_in = create_access_token(auth_user)

    return AuthTokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=AuthUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            plan=user.plan,
        ),
    )


@router.get("/me", response_model=AuthUserResponse)
async def me(current_user: AuthUser = Depends(get_current_auth_user)):
    try:
        async with async_session_factory() as session:
            user = await get_user_by_id(session, current_user.user_id)
    except Exception:
        logger.warning("User lookup failed for /auth/me; falling back to token claims", exc_info=True)
        user = None

    if user is None:
        return AuthUserResponse(
            id=current_user.user_id,
            email=current_user.email or "",
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
            plan=None,
        )

    return AuthUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        plan=user.plan,
    )

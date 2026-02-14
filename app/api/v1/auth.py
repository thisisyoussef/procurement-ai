"""Authentication endpoints (Google sign-in + current user + business profile)."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, create_access_token, get_current_auth_user
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.user import User
from app.repositories.user_repository import get_user_by_id, update_user_profile, upsert_google_user
from app.schemas.auth import (
    AuthTokenResponse,
    AuthUserResponse,
    BusinessProfileRequest,
    GoogleAuthRequest,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        plan=user.plan,
        onboarding_completed=user.onboarding_completed,
        company_name=user.company_name,
        job_title=user.job_title,
        phone=user.phone,
        company_website=user.company_website,
        business_address=user.business_address,
        company_description=user.company_description,
    )


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
        user=_user_to_response(user),
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

    return _user_to_response(user)


@router.put("/profile", response_model=AuthUserResponse)
async def save_business_profile(
    body: BusinessProfileRequest,
    current_user: AuthUser = Depends(get_current_auth_user),
):
    """Save the user's business profile (onboarding step)."""
    try:
        async with async_session_factory() as session:
            user = await update_user_profile(
                session,
                current_user.user_id,
                company_name=body.company_name,
                job_title=body.job_title,
                phone=body.phone,
                company_website=body.company_website,
                business_address=body.business_address,
                company_description=body.company_description,
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save business profile")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save profile",
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_response(user)

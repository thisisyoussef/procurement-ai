"""JWT auth utilities and FastAPI auth dependencies."""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


@dataclass
class AuthUser:
    user_id: str
    email: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None


def create_access_token(user: AuthUser) -> tuple[str, int]:
    now = int(time.time())
    expires_in = max(3600, int(settings.auth_jwt_ttl_hours) * 3600)
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "name": user.full_name,
        "picture": user.avatar_url,
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)
    return token, expires_in


def parse_access_token(token: str) -> AuthUser:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return AuthUser(
        user_id=str(user_id),
        email=payload.get("email"),
        full_name=payload.get("name"),
        avatar_url=payload.get("picture"),
    )


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_token: str | None,
) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    if access_token:
        return access_token
    return None


async def get_current_auth_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Query(default=None),
) -> AuthUser:
    token = _extract_token(credentials, access_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return parse_access_token(token)


async def get_optional_auth_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Query(default=None),
) -> AuthUser | None:
    token = _extract_token(credentials, access_token)
    if not token:
        return None
    return parse_access_token(token)

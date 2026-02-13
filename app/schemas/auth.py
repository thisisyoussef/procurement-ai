"""Authentication request/response schemas."""

from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=10)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    plan: str | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse

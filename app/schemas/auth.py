"""Authentication request/response schemas."""

from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=10)


class BusinessProfileRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=500)
    job_title: str = Field(min_length=1, max_length=300)
    phone: str | None = Field(default=None, max_length=50)
    company_website: str | None = Field(default=None, max_length=1000)
    business_address: str | None = Field(default=None, max_length=1000)
    company_description: str | None = Field(default=None, max_length=2000)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    plan: str | None = None
    onboarding_completed: bool = False
    company_name: str | None = None
    job_title: str | None = None
    phone: str | None = None
    company_website: str | None = None
    business_address: str | None = None
    company_description: str | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse

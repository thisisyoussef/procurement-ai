"""Repository helpers for user persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def upsert_google_user(
    session: AsyncSession,
    *,
    google_sub: str,
    email: str,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    normalized_email = email.strip().lower()
    stmt = select(User).where(
        or_(
            User.google_sub == google_sub,
            func.lower(User.email) == normalized_email,
        )
    ).limit(1)
    user = (await session.execute(stmt)).scalars().first()

    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            google_sub=google_sub,
            email=normalized_email,
            full_name=full_name,
            avatar_url=avatar_url,
            plan="free_trial",
            last_login_at=now,
        )
        session.add(user)
        await session.flush()
        return user

    user.google_sub = google_sub or user.google_sub
    user.email = normalized_email
    user.full_name = full_name or user.full_name
    user.avatar_url = avatar_url or user.avatar_url
    user.last_login_at = now
    await session.flush()
    return user


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    from uuid import UUID

    try:
        normalized = UUID(str(user_id))
    except ValueError:
        return None
    return await session.get(User, normalized)


async def update_user_profile(
    session: AsyncSession,
    user_id: str,
    *,
    company_name: str,
    job_title: str,
    phone: str | None = None,
    company_website: str | None = None,
    business_address: str | None = None,
    company_description: str | None = None,
) -> User | None:
    user = await get_user_by_id(session, user_id)
    if user is None:
        return None

    user.company_name = company_name
    user.job_title = job_title
    user.phone = phone or user.phone
    user.company_website = company_website or user.company_website
    user.business_address = business_address or user.business_address
    user.company_description = company_description or user.company_description
    user.onboarding_completed = True
    await session.flush()
    return user

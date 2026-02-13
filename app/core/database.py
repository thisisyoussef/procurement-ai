"""Async SQLAlchemy database engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


def _normalize_async_database_url(url: str) -> str:
    """Ensure Postgres URLs use asyncpg for async SQLAlchemy engines.

    Railway and other providers commonly expose `postgresql://...` or `postgres://...`.
    For `create_async_engine`, we need the `postgresql+asyncpg://...` dialect URL.
    """
    normalized = (url or "").strip()
    if normalized.startswith("postgres://"):
        return "postgresql+asyncpg://" + normalized[len("postgres://") :]
    if normalized.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + normalized[len("postgresql+psycopg2://") :]
    if normalized.startswith("postgresql://"):
        return "postgresql+asyncpg://" + normalized[len("postgresql://") :]
    return normalized


engine = create_async_engine(
    _normalize_async_database_url(settings.database_url),
    echo=not settings.is_production,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

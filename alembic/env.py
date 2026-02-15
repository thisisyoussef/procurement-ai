"""Alembic migration environment."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base
from app.models.supplier import Supplier  # noqa: F401
from app.models.project import SourcingProject, Quote  # noqa: F401
from app.models.runtime import RuntimeProject, LandingLead, AnalyticsEvent  # noqa: F401
from app.models.user import User  # noqa: F401
from automotive.models.project import AutomotiveProject, AutomotiveProjectEvent, AutomotiveSupplier  # noqa: F401

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _normalize_async_database_url(url: str) -> str:
    normalized = (url or "").strip()
    if normalized.startswith("postgres://"):
        return "postgresql+asyncpg://" + normalized[len("postgres://") :]
    if normalized.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + normalized[len("postgresql+psycopg2://") :]
    if normalized.startswith("postgresql://"):
        return "postgresql+asyncpg://" + normalized[len("postgresql://") :]
    return normalized


config.set_main_option("sqlalchemy.url", _normalize_async_database_url(settings.database_url))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

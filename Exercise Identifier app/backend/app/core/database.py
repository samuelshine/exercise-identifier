"""Async SQLAlchemy engine + session factory + declarative Base.

Why async: FastAPI endpoints are async-first (per project guidelines),
and the vector-DB / LLM calls downstream are inherently I/O-bound.
Sync sessions would force sync-over-async shims at the boundary.

Note: we don't create tables here. Schema management goes through
Alembic once we're ready to version migrations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Subclasses live under `app.models` and should import this directly
    to avoid a circular dep via the top-level `app.models` package."""


# Engine is module-level (one per process). Sessions are short-lived
# and handed out via the `get_session` dependency below.
_settings = get_settings()
engine = create_async_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped async session.

    Commits are the caller's responsibility — this keeps transactional
    boundaries explicit at the route/service layer rather than implicit
    on dependency teardown."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ---------- Bootstrap ------------------------------------------------------


async def ensure_database_exists(database_url: str | None = None) -> bool:
    """Create the target database if it doesn't already exist.

    `CREATE DATABASE` can't run inside a transaction, so we can't use the
    app's normal engine (which wraps statements in transactions by
    default). We build a throwaway admin engine pointed at the default
    `postgres` maintenance DB with `isolation_level="AUTOCOMMIT"`, check
    `pg_database`, and issue the CREATE if needed.

    Returns True if the DB was just created, False if it already existed.

    This is dev ergonomics — once we move to production, the DB is
    provisioned out-of-band and this helper simply never finds a missing
    database.
    """
    url = make_url(database_url or get_settings().database_url)
    target_db = url.database
    if not target_db:
        raise ValueError("DATABASE_URL has no database name")

    # Same server/credentials, but target the maintenance DB. Quote
    # identifiers via SQLAlchemy's preparer to stay injection-safe.
    admin_url = url.set(database="postgres")
    admin_engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=False,
    )
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": target_db},
            )
            if exists:
                return False
            # Quote the DB name safely; target_db is trusted config, but
            # identifier quoting is cheap insurance.
            quoted = conn.dialect.identifier_preparer.quote(target_db)
            await conn.execute(text(f"CREATE DATABASE {quoted}"))
            return True
    finally:
        await admin_engine.dispose()

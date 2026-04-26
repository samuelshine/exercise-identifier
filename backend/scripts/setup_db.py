"""
Database bootstrap script — creates the database and all tables.

Connects to the PostgreSQL server via the system 'postgres' database first,
creates 'exercise-identifier' if it doesn't already exist, then runs
SQLAlchemy's create_all to build the full schema.

Usage:
    cd backend
    python -m scripts.setup_db

Run this once before generate_dataset.py or the FastAPI server.
"""

import asyncio
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

# Import all models so SQLAlchemy's metadata knows about every table
import app.models.exercise  # noqa: F401

from app.core.database import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def _system_dsn(database_url: str) -> tuple[str, str]:
    """
    Split the configured database URL into:
      - a system-level asyncpg DSN pointing at 'postgres' (for CREATE DATABASE)
      - the target database name

    Handles names with hyphens by returning them unquoted (asyncpg quotes
    identifiers automatically in CREATE DATABASE calls).
    """
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")

    # Build a DSN pointing at the 'postgres' system database
    system = urlunparse(parsed._replace(path="/postgres", scheme="postgresql"))
    return system, db_name


async def create_database(database_url: str) -> None:
    """Connect to the 'postgres' system DB and CREATE DATABASE if absent."""
    system_dsn, db_name = _system_dsn(database_url)

    conn = await asyncpg.connect(dsn=system_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if exists:
            logger.info("Database '%s' already exists — skipping creation.", db_name)
        else:
            # asyncpg doesn't support parameters in DDL; use a quoted identifier
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info("Database '%s' created.", db_name)
    finally:
        await conn.close()


async def create_tables(database_url: str) -> None:
    """Run SQLAlchemy create_all against the target database."""
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("All tables created (or already exist).")


async def main() -> None:
    settings = get_settings()
    url = settings.database_url

    logger.info("Target database URL: %s", url)

    await create_database(url)
    await create_tables(url)

    logger.info("Setup complete — ready to seed with: python -m scripts.generate_dataset")


if __name__ == "__main__":
    asyncio.run(main())

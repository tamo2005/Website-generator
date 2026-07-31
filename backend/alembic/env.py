"""
alembic/env.py — Async Alembic environment configuration

Supports async migrations via asyncpg. Reads DATABASE_URL from .env
to override the alembic.ini connection string.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Ensure the backend directory is on sys.path so model imports work
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env so DATABASE_URL is available
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

# Import Base and all models so metadata is populated
from db.base import Base  # noqa: E402
import models  # noqa: E402, F401 — triggers all model imports

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (async)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """Run migrations using a synchronous connection wrapper."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (async) migrations."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""
tests/conftest.py — pytest-asyncio fixtures and test database session

Uses an isolated SQLite in-memory database for all tests.
get_settings() is patched to use test values (no real DB/Redis required).
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from core.config import get_settings, Settings


# ── Test settings override ───────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for the test environment."""
    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        REDIS_URL="memory://",
        JWT_SECRET_KEY="test-secret-key-32-characters-long",
        RESEND_API_KEY="",                  # Console-mode emails in tests
        OPENROUTER_API_KEY="test-key",
        ENABLE_AI_CACHE=False,
        ENABLE_REPAIR=False,                 # Disable repair in unit tests
        ENABLE_PIPELINE_EVENTS=False,
    )


from sqlalchemy.pool import StaticPool

# ── Async engine + session ───────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def test_engine(test_settings):
    """Create an async SQLite engine for the test session."""
    import models  # noqa: ensure all ORM models are registered on Base.metadata
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async DB session, rolled back after each test."""
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ── HTTP Test Client ─────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(test_engine, test_settings) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client bound to the FastAPI app.
    Overrides get_settings() with test values.
    """
    from main import app
    from db.session import get_db

    # Override DB dependency
    async def override_get_db():
        async_session = async_sessionmaker(
            bind=test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helper fixtures ──────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a verified test user for use in authenticated tests."""
    from repositories.user_repo import user_repo
    from core.security import hash_password

    user = await user_repo.create(
        db_session,
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("TestPass123!"),
        is_verified=True,
    )
    await db_session.commit()
    yield user
    await db_session.delete(user)
    await db_session.commit()


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

"""
Shared test fixtures for UDL backend tests.

Key design decision: session-scoped event loop.
asyncpg connections are bound to the event loop they were created on.
Without a shared loop, each test function gets its own loop and the
SQLAlchemy engine's pooled connections fail with
"InterfaceError: another operation is in progress".
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session, engine


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop — all async tests share one loop.

    This prevents asyncpg InterfaceError caused by pooled connections
    being accessed from a different event loop than the one they were
    created on.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provide a database session with per-test table cleanup.

    After each test, all tables are truncated so tests are fully isolated.
    """
    async with async_session() as session:
        yield session
        await session.rollback()

    # Truncate all tables after each test for isolation (CASCADE handles FK order)
    async with engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE picks, fixed_team_selections, join_requests, "
            "participants, games, competitions, golfers, teams, leagues, "
            "audit_logs, users CASCADE"
        ))


@pytest_asyncio.fixture(scope="function")
async def client():
    """Async HTTP test client wired to the FastAPI ASGI app.

    Uses ASGITransport which does NOT invoke the app lifespan,
    so background jobs and Redis subscribers are not started.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

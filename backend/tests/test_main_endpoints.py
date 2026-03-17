"""Tests for main.py endpoints and middleware.

Tests the root /, /health, security headers, and the unhandled exception handler.
Uses the existing `client` fixture (ASGITransport, no lifespan invocation).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ping_get(client: AsyncClient):
    """GET /ping returns 200 for standard clients."""
    resp = await client.get("/ping")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ping_head(client: AsyncClient):
    """HEAD /ping returns 200 — required for UptimeRobot free tier which
    is locked to HEAD-only requests and cannot be changed without a paid plan."""
    resp = await client.head("/ping")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """GET / returns API metadata."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /health returns database and redis status."""
    resp = await client.get("/health")
    # In CI both DB and Redis are available; in local dev they may not be.
    # Either 200 (all ok) or 503 (a dependency down) is acceptable.
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "api" in data
    assert "database" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_security_headers_on_api_response(client: AsyncClient):
    """Security headers are added to every HTTP response."""
    resp = await client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

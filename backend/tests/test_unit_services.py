"""
Pure unit tests for service-layer classes that require no database or HTTP.

Covers:
- app/services/circuit_breaker.py
- app/core/security.py
- app/services/sports_api/base.py
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerOpenError,
    CircuitState,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
)
from app.services.sports_api.base import (
    BaseSportsAPIClient,
    APIProvider,
    GameData,
    RateLimitExceededError,
    APIUnavailableError,
)


# ── Circuit Breaker ──────────────────────────────────────────────────────────

class TestCircuitBreaker:

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3, timeout_seconds=60)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_success_call_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.failure_count = 2
        cb.call(lambda: "ok")
        assert cb.failure_count == 0

    def test_failure_increments_count(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert cb.failure_count == 1

    def test_trips_on_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_call_before_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout_seconds=3600)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not run")

    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout_seconds=0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        # Now state is OPEN. Since timeout=0, should_attempt_reset is True.
        # Next call transitions to HALF_OPEN.
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_trips_again(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout_seconds=0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        # Force HALF_OPEN
        cb.state = CircuitState.HALF_OPEN
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("still failing")))
        except RuntimeError:
            pass
        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_get_status_closed(self):
        cb = CircuitBreaker("svc", failure_threshold=5, timeout_seconds=60)
        status = cb.get_status()
        assert status["name"] == "svc"
        assert status["state"] == CircuitState.CLOSED
        assert status["failure_count"] == 0
        assert status["time_until_reset"] == 0

    def test_get_status_open(self):
        cb = CircuitBreaker("svc", failure_threshold=1, timeout_seconds=60)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        except RuntimeError:
            pass
        status = cb.get_status()
        assert status["state"] == CircuitState.OPEN
        assert status["last_failure_time"] is not None

    def test_time_until_reset_no_failure(self):
        cb = CircuitBreaker("test", timeout_seconds=60)
        assert cb._time_until_reset() == 0

    def test_time_until_reset_with_recent_failure(self):
        cb = CircuitBreaker("test", timeout_seconds=60)
        cb.last_failure_time = datetime.utcnow()
        remaining = cb._time_until_reset()
        assert 55 <= remaining <= 60

    def test_should_attempt_reset_no_failure(self):
        cb = CircuitBreaker("test", timeout_seconds=60)
        assert cb._should_attempt_reset() is True

    def test_should_attempt_reset_before_timeout(self):
        cb = CircuitBreaker("test", timeout_seconds=3600)
        cb.last_failure_time = datetime.utcnow()
        assert cb._should_attempt_reset() is False

    def test_should_attempt_reset_after_timeout(self):
        cb = CircuitBreaker("test", timeout_seconds=1)
        cb.last_failure_time = datetime.utcnow() - timedelta(seconds=5)
        assert cb._should_attempt_reset() is True

    @pytest.mark.asyncio
    async def test_async_call_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def ok():
            return "async_ok"

        result = await cb.async_call(ok)
        assert result == "async_ok"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_async_call_failure(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise ValueError("async fail")

        with pytest.raises(ValueError):
            await cb.async_call(fail)
        assert cb.failure_count == 1

    @pytest.mark.asyncio
    async def test_async_call_open_raises(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout_seconds=3600)
        cb.state = CircuitState.OPEN
        cb.last_failure_time = datetime.utcnow()

        async def should_not_run():
            return "nope"

        with pytest.raises(CircuitBreakerOpenError):
            await cb.async_call(should_not_run)

    @pytest.mark.asyncio
    async def test_async_call_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout_seconds=0)
        cb.state = CircuitState.OPEN
        cb.last_failure_time = datetime.utcnow() - timedelta(seconds=10)

        async def ok():
            return "back"

        result = await cb.async_call(ok)
        assert result == "back"
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerManager:

    def test_get_breaker_creates_new(self):
        mgr = CircuitBreakerManager()
        cb = mgr.get_breaker("api_x", failure_threshold=3, timeout_seconds=30)
        assert cb.name == "api_x"
        assert cb.failure_threshold == 3

    def test_get_breaker_returns_existing(self):
        mgr = CircuitBreakerManager()
        cb1 = mgr.get_breaker("api_y")
        cb2 = mgr.get_breaker("api_y")
        assert cb1 is cb2

    def test_reset_all(self):
        mgr = CircuitBreakerManager()
        cb = mgr.get_breaker("api_z", failure_threshold=1)
        cb.state = CircuitState.OPEN
        cb.failure_count = 5
        mgr.reset_all()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_get_all_status(self):
        mgr = CircuitBreakerManager()
        mgr.get_breaker("a")
        mgr.get_breaker("b")
        statuses = mgr.get_all_status()
        assert "a" in statuses
        assert "b" in statuses


# ── Security ─────────────────────────────────────────────────────────────────

class TestSecurity:

    def test_create_access_token_contains_type(self):
        token = create_access_token({"sub": "user123"})
        payload = verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_create_access_token_with_custom_expiry(self):
        token = create_access_token({"sub": "u"}, expires_delta=timedelta(hours=1))
        payload = verify_token(token, "access")
        assert payload is not None

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "user456"})
        payload = verify_token(token, "refresh")
        assert payload is not None
        assert payload["sub"] == "user456"
        assert payload["type"] == "refresh"

    def test_verify_wrong_token_type_returns_none(self):
        access_token = create_access_token({"sub": "u"})
        # Pass access token where refresh is expected
        assert verify_token(access_token, "refresh") is None

    def test_verify_invalid_token_returns_none(self):
        assert verify_token("not.a.real.token", "access") is None

    def test_verify_tampered_token_returns_none(self):
        token = create_access_token({"sub": "u"})
        tampered = token[:-5] + "XXXXX"
        assert verify_token(tampered, "access") is None

    def test_password_hash_and_verify(self):
        raw = "SuperSecret123!"
        hashed = get_password_hash(raw)
        assert hashed != raw
        assert verify_password(raw, hashed) is True

    def test_wrong_password_fails_verify(self):
        hashed = get_password_hash("correctPassword")
        assert verify_password("wrongPassword", hashed) is False


# ── Base Sports API Client ────────────────────────────────────────────────────

class ConcreteClient(BaseSportsAPIClient):
    """Minimal concrete subclass for testing BaseSportsAPIClient."""

    def __init__(self):
        super().__init__(APIProvider.ESPN)

    def _map_league_name(self, league: str) -> str:
        return league.lower()

    async def get_schedule(self, league, start_date, end_date):
        return []

    async def get_live_scores(self, league):
        return []

    async def get_game_details(self, league, game_id):
        return None


class TestBaseSportsAPIClient:

    def test_parse_datetime_iso(self):
        client = ConcreteClient()
        dt = client._parse_datetime("2023-01-15T18:30:00Z")
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_invalid_falls_back(self):
        client = ConcreteClient()
        # Should not raise, falls back to utcnow()
        dt = client._parse_datetime("not-a-date")
        assert isinstance(dt, datetime)

    @pytest.mark.asyncio
    async def test_make_request_raises_rate_limit_on_429(self):
        client = ConcreteClient()
        mock_response = MagicMock()
        mock_response.status_code = 429
        http_error = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=mock_response
        )
        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            mock_response.raise_for_status.side_effect = http_error
            with pytest.raises(RateLimitExceededError):
                await client._make_request("GET", "http://example.com")

    @pytest.mark.asyncio
    async def test_make_request_raises_on_500(self):
        client = ConcreteClient()
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            mock_response.raise_for_status.side_effect = http_error
            with pytest.raises(httpx.HTTPStatusError):
                await client._make_request("GET", "http://example.com")

    @pytest.mark.asyncio
    async def test_make_request_raises_on_4xx(self):
        client = ConcreteClient()
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            mock_response.raise_for_status.side_effect = http_error
            with pytest.raises(httpx.HTTPStatusError):
                await client._make_request("GET", "http://example.com")

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        client = ConcreteClient()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": "ok"}
        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            result = await client._make_request("GET", "http://example.com")
            assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_make_request_timeout_raises(self):
        from tenacity import RetryError
        client = ConcreteClient()
        with patch.object(
            client.client, "request", new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out")
        ):
            # tenacity retries API_MAX_RETRIES times then wraps in RetryError
            with pytest.raises(RetryError):
                await client._make_request("GET", "http://example.com")

    @pytest.mark.asyncio
    async def test_close(self):
        client = ConcreteClient()
        with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestGameData:

    def test_game_data_defaults(self):
        now = datetime.utcnow()
        gd = GameData(
            external_id="g1",
            home_team="Home",
            away_team="Away",
            scheduled_start_time=now,
            status="scheduled",
        )
        assert gd.external_id == "g1"
        assert gd.home_score is None
        assert gd.away_score is None
        assert gd.raw_data == {}

    def test_game_data_full(self):
        now = datetime.utcnow()
        gd = GameData(
            external_id="g2",
            home_team="H",
            away_team="A",
            scheduled_start_time=now,
            status="final",
            home_score=21,
            away_score=14,
            venue="Stadium",
            raw_data={"key": "val"},
            home_team_external_id="h_ext",
            away_team_external_id="a_ext",
            home_team_abbreviation="HTM",
            away_team_abbreviation="ATM",
        )
        assert gd.home_score == 21
        assert gd.venue == "Stadium"
        assert gd.home_team_abbreviation == "HTM"

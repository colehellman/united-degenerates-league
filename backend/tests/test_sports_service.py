from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sports_api.base import APIProvider, GameData
from app.services.sports_api.sports_service import SportsDataService


@pytest.fixture
def mock_redis_client():
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    return mock


@pytest.fixture
def sports_service(mock_redis_client):
    with patch("redis.from_url", return_value=mock_redis_client):
        service = SportsDataService()
        # Mock the clients to prevent actual API calls
        service.clients = [AsyncMock(), AsyncMock()]
        service.clients[0].provider = APIProvider.ESPN
        service.clients[1].provider = APIProvider.THE_ODDS_API
        yield service


@pytest.mark.asyncio
async def test_get_schedule_success_with_caching(sports_service, mock_redis_client):
    """Test get_schedule success from primary API and caching."""
    game = GameData(
        external_id="1",
        home_team="Team A",
        away_team="Team B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    sports_service.clients[0].get_schedule.return_value = [game]

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 3)

    # First call - should call the API and set cache
    games = await sports_service.get_schedule("NFL", start_date, end_date, use_cache=True)
    assert len(games) == 1
    sports_service.clients[0].get_schedule.assert_called_once()
    mock_redis_client.setex.assert_called_once()

    # Second call - should hit the cache
    sports_service.clients[0].get_schedule.reset_mock()
    mock_redis_client.get.return_value = sports_service._serialize_games([game])
    games = await sports_service.get_schedule("NFL", start_date, end_date, use_cache=True)
    assert len(games) == 1
    sports_service.clients[0].get_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_get_schedule_primary_empty_tries_secondary(sports_service):
    """When the primary API returns empty, the secondary is tried."""
    game = GameData(
        external_id="g2",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    sports_service.clients[0].get_schedule.return_value = []
    sports_service.clients[1].get_schedule.return_value = [game]

    games = await sports_service.get_schedule(
        "NFL", datetime(2023, 1, 1), datetime(2023, 1, 3), use_cache=False
    )
    assert len(games) == 1
    assert games[0].external_id == "g2"


@pytest.mark.asyncio
async def test_get_schedule_all_apis_fail_raises(sports_service):
    """When all APIs fail, APIUnavailableError is raised."""
    from app.services.sports_api.base import APIUnavailableError

    sports_service.clients[0].get_schedule.return_value = []
    sports_service.clients[1].get_schedule.return_value = []

    with pytest.raises(APIUnavailableError):
        await sports_service.get_schedule(
            "NFL", datetime(2023, 1, 1), datetime(2023, 1, 3), use_cache=False
        )


@pytest.mark.asyncio
async def test_get_schedule_rate_limit_skips_to_next(sports_service):
    """RateLimitExceededError on primary causes fallback to secondary."""
    from app.services.sports_api.base import RateLimitExceededError

    game = GameData(
        external_id="g3",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    sports_service.clients[0].get_schedule.side_effect = RateLimitExceededError("too many")
    sports_service.clients[1].get_schedule.return_value = [game]

    games = await sports_service.get_schedule(
        "NFL", datetime(2023, 1, 1), datetime(2023, 1, 3), use_cache=False
    )
    assert len(games) == 1


@pytest.mark.asyncio
async def test_get_live_scores_success(sports_service, mock_redis_client):
    """get_live_scores returns games from primary API and caches result."""
    game = GameData(
        external_id="live1",
        home_team="X",
        away_team="Y",
        scheduled_start_time=datetime.utcnow(),
        status="in_progress",
    )
    sports_service.clients[0].get_live_scores.return_value = [game]

    games = await sports_service.get_live_scores("NFL", use_cache=False)
    assert len(games) == 1
    mock_redis_client.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_live_scores_cache_hit(sports_service, mock_redis_client):
    """get_live_scores returns cached data without calling the API."""
    game = GameData(
        external_id="cached",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    mock_redis_client.get.return_value = sports_service._serialize_games([game])

    games = await sports_service.get_live_scores("NFL", use_cache=True)
    assert len(games) == 1
    sports_service.clients[0].get_live_scores.assert_not_called()


@pytest.mark.asyncio
async def test_get_live_scores_all_fail_raises(sports_service):
    """get_live_scores raises APIUnavailableError when all APIs fail."""
    from app.services.sports_api.base import APIUnavailableError

    sports_service.clients[0].get_live_scores.side_effect = RuntimeError("fail")
    sports_service.clients[1].get_live_scores.side_effect = RuntimeError("fail")

    with pytest.raises(APIUnavailableError):
        await sports_service.get_live_scores("NFL", use_cache=False)


@pytest.mark.asyncio
async def test_get_game_details_success(sports_service, mock_redis_client):
    """get_game_details returns game from primary API and caches."""
    game = GameData(
        external_id="det1",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="final",
    )
    sports_service.clients[0].get_game_details.return_value = game

    result = await sports_service.get_game_details("NFL", "det1", use_cache=False)
    assert result is not None
    assert result.external_id == "det1"
    mock_redis_client.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_game_details_cache_hit(sports_service, mock_redis_client):
    """get_game_details returns cached game without API call."""
    game = GameData(
        external_id="cached_det",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="final",
    )
    mock_redis_client.get.return_value = sports_service._serialize_games([game])

    result = await sports_service.get_game_details("NFL", "cached_det", use_cache=True)
    assert result is not None
    sports_service.clients[0].get_game_details.assert_not_called()


@pytest.mark.asyncio
async def test_get_game_details_all_fail_returns_none(sports_service):
    """get_game_details returns None when all APIs return None."""
    sports_service.clients[0].get_game_details.return_value = None
    sports_service.clients[1].get_game_details.return_value = None

    result = await sports_service.get_game_details("NFL", "unknown", use_cache=False)
    assert result is None


def test_get_api_health_status(sports_service):
    """get_api_health_status returns structured dict with providers and cache."""
    status = sports_service.get_api_health_status()
    assert "configured_apis" in status
    assert "circuit_breakers" in status
    assert status["cache_status"] == "connected"


def test_serialize_deserialize_roundtrip(sports_service):
    """Games survive a serialize → deserialize roundtrip."""
    now = datetime.utcnow().replace(microsecond=0)
    games = [
        GameData(
            external_id="rt1",
            home_team="Home",
            away_team="Away",
            scheduled_start_time=now,
            status="scheduled",
            home_score=10,
            away_score=7,
            venue="Stadium",
            home_team_external_id="h_ext",
            away_team_external_id="a_ext",
            home_team_abbreviation="HME",
            away_team_abbreviation="AWY",
        )
    ]
    serialized = sports_service._serialize_games(games)
    restored = sports_service._deserialize_games(serialized)

    assert len(restored) == 1
    assert restored[0].external_id == "rt1"
    assert restored[0].home_score == 10
    assert restored[0].venue == "Stadium"


def test_deserialize_invalid_json_returns_empty(sports_service):
    """_deserialize_games returns [] on unparseable JSON."""
    result = sports_service._deserialize_games("not valid json")
    assert result == []


async def test_get_from_cache_redis_error_returns_none(sports_service, mock_redis_client):
    """_get_from_cache swallows Redis errors and returns None."""
    mock_redis_client.get.side_effect = Exception("redis down")
    result = await sports_service._get_from_cache("any_key")
    assert result is None


async def test_set_cache_redis_error_is_silenced(sports_service, mock_redis_client):
    """_set_cache swallows Redis errors without raising."""
    mock_redis_client.setex.side_effect = Exception("redis down")
    await sports_service._set_cache("key", "value", 60)  # should not raise


async def test_get_from_cache_no_redis(sports_service):
    """_get_from_cache returns None when redis_client is None."""
    sports_service.redis_client = None
    assert await sports_service._get_from_cache("key") is None


async def test_set_cache_no_redis(sports_service):
    """_set_cache is a no-op when redis_client is None."""
    sports_service.redis_client = None
    await sports_service._set_cache("key", "val", 60)  # should not raise


# ---------------------------------------------------------------------------
# Error-handler coverage: circuit breaker, rate-limit, generic exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_schedule_circuit_breaker_open_falls_through(sports_service):
    """CircuitBreakerOpenError on primary is recorded and secondary is tried."""
    from app.services.circuit_breaker import CircuitBreakerOpenError

    game = GameData(
        external_id="cb_fallback",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    open_breaker = AsyncMock()
    open_breaker.async_call.side_effect = CircuitBreakerOpenError("open")

    good_breaker = AsyncMock()
    good_breaker.async_call.return_value = [game]

    with patch("app.services.sports_api.sports_service.circuit_breaker_manager") as mock_cbm:
        mock_cbm.get_breaker.side_effect = [open_breaker, good_breaker]
        games = await sports_service.get_schedule(
            "NFL", datetime(2023, 1, 1), datetime(2023, 1, 3), use_cache=False
        )

    assert len(games) == 1


@pytest.mark.asyncio
async def test_get_schedule_generic_exception_falls_through(sports_service):
    """A generic exception from the primary API causes fallback to secondary."""
    game = GameData(
        external_id="exc_fallback",
        home_team="A",
        away_team="B",
        scheduled_start_time=datetime.utcnow(),
        status="scheduled",
    )
    error_breaker = AsyncMock()
    error_breaker.async_call.side_effect = ValueError("unexpected API error")

    good_breaker = AsyncMock()
    good_breaker.async_call.return_value = [game]

    with patch("app.services.sports_api.sports_service.circuit_breaker_manager") as mock_cbm:
        mock_cbm.get_breaker.side_effect = [error_breaker, good_breaker]
        games = await sports_service.get_schedule(
            "NFL", datetime(2023, 1, 1), datetime(2023, 1, 3), use_cache=False
        )

    assert len(games) == 1


@pytest.mark.asyncio
async def test_get_live_scores_circuit_breaker_open_falls_through(sports_service):
    """CircuitBreakerOpenError on primary live-scores call falls through to secondary."""
    from app.services.circuit_breaker import CircuitBreakerOpenError

    game = GameData(
        external_id="live_cb",
        home_team="X",
        away_team="Y",
        scheduled_start_time=datetime.utcnow(),
        status="in_progress",
    )
    open_breaker = AsyncMock()
    open_breaker.async_call.side_effect = CircuitBreakerOpenError("open")

    good_breaker = AsyncMock()
    good_breaker.async_call.return_value = [game]

    with patch("app.services.sports_api.sports_service.circuit_breaker_manager") as mock_cbm:
        mock_cbm.get_breaker.side_effect = [open_breaker, good_breaker]
        games = await sports_service.get_live_scores("NFL", use_cache=False)

    assert len(games) == 1


@pytest.mark.asyncio
async def test_get_live_scores_rate_limit_falls_through(sports_service):
    """RateLimitExceededError on primary live-scores falls through to secondary."""
    from app.services.sports_api.base import RateLimitExceededError

    game = GameData(
        external_id="live_rl",
        home_team="X",
        away_team="Y",
        scheduled_start_time=datetime.utcnow(),
        status="in_progress",
    )
    rate_breaker = AsyncMock()
    rate_breaker.async_call.side_effect = RateLimitExceededError("rate limited")

    good_breaker = AsyncMock()
    good_breaker.async_call.return_value = [game]

    with patch("app.services.sports_api.sports_service.circuit_breaker_manager") as mock_cbm:
        mock_cbm.get_breaker.side_effect = [rate_breaker, good_breaker]
        games = await sports_service.get_live_scores("NFL", use_cache=False)

    assert len(games) == 1


@pytest.mark.asyncio
async def test_get_game_details_exception_returns_none(sports_service):
    """Exceptions in get_game_details are caught and None is returned."""
    error_breaker = AsyncMock()
    error_breaker.async_call.side_effect = ValueError("API failure")

    with patch("app.services.sports_api.sports_service.circuit_breaker_manager") as mock_cbm:
        mock_cbm.get_breaker.return_value = error_breaker
        result = await sports_service.get_game_details("NFL", "g1", use_cache=False)

    assert result is None


def test_deserialize_games_skips_malformed_entry(sports_service):
    """_deserialize_games logs and skips entries that fail validation."""
    import json

    valid = {
        "external_id": "v1",
        "home_team": "Home",
        "away_team": "Away",
        "scheduled_start_time": datetime.utcnow().isoformat(),
        "status": "scheduled",
        "home_score": None,
        "away_score": None,
        "venue": None,
        "home_team_external_id": None,
        "away_team_external_id": None,
        "home_team_abbreviation": None,
        "away_team_abbreviation": None,
    }
    # Bad entry: scheduled_start_time is not a valid ISO string → datetime.fromisoformat fails
    bad = {
        "external_id": "bad",
        "home_team": "X",
        "away_team": "Y",
        "scheduled_start_time": "NOT-A-DATE",
        "status": "scheduled",
    }
    data = json.dumps([valid, bad])
    games = sports_service._deserialize_games(data)
    assert len(games) == 1
    assert games[0].external_id == "v1"


@pytest.mark.asyncio
async def test_service_close_calls_client_close(sports_service):
    """close() awaits client.close() for each API client and closes Redis."""
    await sports_service.close()
    for client in sports_service.clients:
        client.close.assert_called_once()
    sports_service.redis_client.close.assert_called_once()


def test_sports_data_service_redis_init_failure():
    """SportsDataService sets redis_client=None when Redis connection fails."""
    with patch("redis.from_url", side_effect=Exception("connection refused")):
        service = SportsDataService()
    assert service.redis_client is None

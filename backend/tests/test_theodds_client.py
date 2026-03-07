"""Tests for TheOddsAPIClient covering all public methods and parse helpers."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.services.sports_api.theodds_client import TheOddsAPIClient
from app.services.sports_api.base import GameData, RateLimitExceededError


@pytest.fixture
def client():
    return TheOddsAPIClient()


# ── _map_league_name ─────────────────────────────────────────────────────────

def test_map_league_name_known(client: TheOddsAPIClient):
    assert client._map_league_name("NFL") == "americanfootball_nfl"
    assert client._map_league_name("NBA") == "basketball_nba"
    assert client._map_league_name("MLB") == "baseball_mlb"
    assert client._map_league_name("NHL") == "icehockey_nhl"
    assert client._map_league_name("NCAA_BASKETBALL") == "basketball_ncaab"
    assert client._map_league_name("NCAA_FOOTBALL") == "americanfootball_ncaaf"


def test_map_league_name_unknown(client: TheOddsAPIClient):
    assert client._map_league_name("UNKNOWN") == "unknown"


# ── get_schedule ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_schedule_success(client: TheOddsAPIClient):
    """get_schedule returns games within the date range."""
    # _parse_datetime returns tz-aware datetimes; use tz-aware bounds for comparison
    now = datetime.now(timezone.utc)
    mock_response = [
        {
            "id": "odds_game_1",
            "home_team": "Chiefs",
            "away_team": "Raiders",
            "commence_time": now.isoformat().replace("+00:00", "Z"),
        }
    ]
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        games = await client.get_schedule(
            "NFL",
            now - timedelta(hours=1),
            now + timedelta(hours=1),
        )
        assert len(games) == 1
        assert games[0].external_id == "odds_game_1"
        assert games[0].home_team == "Chiefs"


@pytest.mark.asyncio
async def test_get_schedule_filters_outside_date_range(client: TheOddsAPIClient):
    """Games outside the date range are excluded."""
    old_dt = datetime.now(timezone.utc) - timedelta(days=5)
    old_time = old_dt.isoformat().replace("+00:00", "Z")
    mock_response = [
        {
            "id": "old_game",
            "home_team": "A",
            "away_team": "B",
            "commence_time": old_time,
        }
    ]
    now = datetime.now(timezone.utc)
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        games = await client.get_schedule(
            "NFL",
            now - timedelta(hours=2),
            now + timedelta(hours=2),
        )
        assert games == []


@pytest.mark.asyncio
async def test_get_schedule_non_list_response(client: TheOddsAPIClient):
    """get_schedule handles non-list API response gracefully."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={}):
        games = await client.get_schedule("NFL", datetime.utcnow(), datetime.utcnow())
        assert games == []


@pytest.mark.asyncio
async def test_get_schedule_exception_returns_empty(client: TheOddsAPIClient):
    """get_schedule swallows generic exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("timeout")
        games = await client.get_schedule("NFL", datetime.utcnow(), datetime.utcnow())
        assert games == []


# ── get_live_scores ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_live_scores_success(client: TheOddsAPIClient):
    """get_live_scores returns in-progress games (not completed)."""
    now = datetime.utcnow().isoformat() + "Z"
    mock_response = [
        {
            "id": "live_1",
            "home_team": "Heat",
            "away_team": "Bulls",
            "commence_time": now,
            "completed": False,
            "scores": [
                {"name": "Heat", "score": "55"},
                {"name": "Bulls", "score": "48"},
            ],
        },
        {
            "id": "done_1",
            "home_team": "Lakers",
            "away_team": "Nets",
            "commence_time": now,
            "completed": True,  # completed games are skipped in get_live_scores
        },
    ]
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        games = await client.get_live_scores("NBA")
        assert len(games) == 1
        assert games[0].external_id == "live_1"


@pytest.mark.asyncio
async def test_get_live_scores_non_list_response(client: TheOddsAPIClient):
    """get_live_scores handles non-list response."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={}):
        games = await client.get_live_scores("NBA")
        assert games == []


@pytest.mark.asyncio
async def test_get_live_scores_exception_returns_empty(client: TheOddsAPIClient):
    """get_live_scores swallows exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("api down")
        games = await client.get_live_scores("NFL")
        assert games == []


# ── get_game_details ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_game_details_success(client: TheOddsAPIClient):
    """get_game_details finds game by ID from scores endpoint."""
    now = datetime.utcnow().isoformat() + "Z"
    mock_response = [
        {"id": "target_game", "home_team": "A", "away_team": "B", "commence_time": now, "completed": True, "scores": []},
        {"id": "other_game", "home_team": "C", "away_team": "D", "commence_time": now, "completed": False, "scores": []},
    ]
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        game = await client.get_game_details("NFL", "target_game")
        assert game is not None
        assert game.external_id == "target_game"


@pytest.mark.asyncio
async def test_get_game_details_not_found_returns_none(client: TheOddsAPIClient):
    """get_game_details returns None when game ID is not in response."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=[]):
        game = await client.get_game_details("NFL", "nonexistent")
        assert game is None


@pytest.mark.asyncio
async def test_get_game_details_non_list_returns_none(client: TheOddsAPIClient):
    """get_game_details returns None for non-list response."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={}):
        game = await client.get_game_details("NFL", "any")
        assert game is None


@pytest.mark.asyncio
async def test_get_game_details_exception_returns_none(client: TheOddsAPIClient):
    """get_game_details swallows errors and returns None."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("fail")
        game = await client.get_game_details("NFL", "any")
        assert game is None


# ── _parse_event ──────────────────────────────────────────────────────────────

def test_parse_event_success(client: TheOddsAPIClient):
    """_parse_event returns scheduled GameData from odds event."""
    event = {
        "id": "e1",
        "home_team": "Chiefs",
        "away_team": "Raiders",
        "commence_time": "2023-01-01T18:00:00Z",
    }
    result = client._parse_event(event)
    assert result is not None
    assert result.status == "scheduled"
    assert result.home_team == "Chiefs"


def test_parse_event_missing_teams_returns_none(client: TheOddsAPIClient):
    """_parse_event returns None when team names are missing."""
    assert client._parse_event({"id": "x"}) is None


def test_parse_event_no_commence_time(client: TheOddsAPIClient):
    """_parse_event defaults to utcnow when commence_time is absent."""
    event = {"id": "e2", "home_team": "A", "away_team": "B"}
    result = client._parse_event(event)
    assert result is not None


# ── _parse_score_event ────────────────────────────────────────────────────────

def test_parse_score_event_live(client: TheOddsAPIClient):
    """_parse_score_event maps non-completed event to in_progress."""
    event = {
        "id": "s1",
        "home_team": "Heat",
        "away_team": "Bulls",
        "commence_time": "2023-01-01T20:00:00Z",
        "completed": False,
        "scores": [
            {"name": "Heat", "score": "55"},
            {"name": "Bulls", "score": "48"},
        ],
    }
    result = client._parse_score_event(event)
    assert result is not None
    assert result.status == "in_progress"
    assert result.home_score == 55
    assert result.away_score == 48


def test_parse_score_event_completed(client: TheOddsAPIClient):
    """_parse_score_event maps completed event to final."""
    event = {
        "id": "s2",
        "home_team": "Celtics",
        "away_team": "Warriors",
        "commence_time": "2023-01-01T20:00:00Z",
        "completed": True,
        "scores": [
            {"name": "Celtics", "score": "110"},
            {"name": "Warriors", "score": "105"},
        ],
    }
    result = client._parse_score_event(event)
    assert result is not None
    assert result.status == "final"
    assert result.home_score == 110


def test_parse_score_event_missing_teams_returns_none(client: TheOddsAPIClient):
    """_parse_score_event returns None when team names are missing."""
    assert client._parse_score_event({"id": "x", "completed": False}) is None

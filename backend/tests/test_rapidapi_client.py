import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.services.sports_api.rapidapi_client import RapidAPIClient
from app.services.sports_api.base import GameData


@pytest.fixture
def client():
    with patch("app.core.config.settings.RAPIDAPI_HOST_NFL", "some-host"):
        yield RapidAPIClient()


@pytest.mark.asyncio
async def test_get_schedule_success(client: RapidAPIClient):
    """Test get_schedule successfully fetches and parses data."""
    mock_response = {
        "response": [
            {
                "id": "12345",
                "teams": {
                    "home": {"name": "Team A"},
                    "visitors": {"name": "Team B"},
                },
                "scores": {
                    "home": {"points": 10},
                    "visitors": {"points": 7},
                },
                "status": {"short": "FT"},
                "date": {"start": "2023-01-01T20:00:00Z"},
            }
        ]
    }

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)

        games = await client.get_schedule("NFL", start_date, end_date)

        assert len(games) == 1
        assert isinstance(games[0], GameData)
        assert games[0].external_id == "12345"
        assert games[0].home_team == "Team A"
        assert games[0].status == "final"


def test_map_league_name(client: RapidAPIClient):
    """Test internal league names are correctly mapped."""
    assert client._map_league_name("NFL") == "some-host"
    assert client._map_league_name("UNKNOWN") == ""


@pytest.mark.asyncio
async def test_get_schedule_unknown_league_returns_empty(client: RapidAPIClient):
    """get_schedule returns [] immediately when league has no host mapping."""
    games = await client.get_schedule("UNKNOWN_SPORT", datetime(2023, 1, 1), datetime(2023, 1, 3))
    assert games == []


@pytest.mark.asyncio
async def test_get_schedule_exception_returns_empty(client: RapidAPIClient):
    """get_schedule swallows generic exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("api down")
        games = await client.get_schedule("NFL", datetime(2023, 1, 1), datetime(2023, 1, 3))
        assert games == []


@pytest.mark.asyncio
async def test_get_live_scores_success(client: RapidAPIClient):
    """get_live_scores returns in-progress games only."""
    mock_response = {
        "response": [
            {
                "id": "live_g",
                "teams": {"home": {"name": "Heat"}, "visitors": {"name": "Bulls"}},
                "scores": {"home": {"points": 55}, "visitors": {"points": 48}},
                "status": {"short": "2"},
                "date": {"start": "2023-01-01T21:00:00Z"},
            },
            {
                "id": "scheduled_g",
                "teams": {"home": {"name": "Lakers"}, "visitors": {"name": "Nets"}},
                "scores": {"home": {}, "visitors": {}},
                "status": {"short": "NS"},
                "date": {"start": "2023-01-01T23:00:00Z"},
            },
        ]
    }
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        games = await client.get_live_scores("NFL")
        assert len(games) == 1
        assert games[0].external_id == "live_g"
        assert games[0].status == "in_progress"


@pytest.mark.asyncio
async def test_get_live_scores_unknown_league_returns_empty(client: RapidAPIClient):
    """get_live_scores returns [] for unmapped leagues."""
    games = await client.get_live_scores("UNKNOWN_SPORT")
    assert games == []


@pytest.mark.asyncio
async def test_get_live_scores_exception_returns_empty(client: RapidAPIClient):
    """get_live_scores swallows exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("network error")
        games = await client.get_live_scores("NFL")
        assert games == []


@pytest.mark.asyncio
async def test_get_game_details_success(client: RapidAPIClient):
    """get_game_details returns the first matching game."""
    mock_response = {
        "response": [
            {
                "id": "g_detail",
                "teams": {"home": {"name": "Celtics"}, "visitors": {"name": "Warriors"}},
                "scores": {"home": {"points": 110}, "visitors": {"points": 105}},
                "status": {"short": "FT"},
                "date": {"start": "2023-02-01T19:00:00Z"},
            }
        ]
    }
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        game = await client.get_game_details("NFL", "g_detail")
        assert game is not None
        assert game.external_id == "g_detail"
        assert game.status == "final"


@pytest.mark.asyncio
async def test_get_game_details_empty_response_returns_none(client: RapidAPIClient):
    """get_game_details returns None when response list is empty."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={"response": []}):
        game = await client.get_game_details("NFL", "missing")
        assert game is None


@pytest.mark.asyncio
async def test_get_game_details_unknown_league_returns_none(client: RapidAPIClient):
    """get_game_details returns None for unmapped leagues."""
    game = await client.get_game_details("UNKNOWN", "any")
    assert game is None


@pytest.mark.asyncio
async def test_get_game_details_exception_returns_none(client: RapidAPIClient):
    """get_game_details swallows errors and returns None."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("fail")
        game = await client.get_game_details("NFL", "any")
        assert game is None


def test_parse_game_missing_teams_returns_none(client: RapidAPIClient):
    """_parse_game returns None when team names cannot be extracted."""
    assert client._parse_game({}, "NFL") is None


def test_parse_game_with_arena_venue(client: RapidAPIClient):
    """_parse_game extracts arena name as venue."""
    game_data = {
        "id": "arena_game",
        "teams": {"home": {"name": "Heat"}, "visitors": {"name": "Bucks"}},
        "scores": {"home": {"points": 100}, "visitors": {"points": 95}},
        "status": {"short": "FT"},
        "date": {"start": "2023-03-01T20:00:00Z"},
        "arena": {"name": "Kaseya Center"},
    }
    result = client._parse_game(game_data, "NBA")
    assert result is not None
    assert result.venue == "Kaseya Center"


def test_parse_game_halftime_status(client: RapidAPIClient):
    """_parse_game maps 'H' (halftime) to in_progress."""
    game_data = {
        "id": "ht_game",
        "teams": {"home": {"name": "A"}, "visitors": {"name": "B"}},
        "scores": {"home": {"points": 45}, "visitors": {"points": 42}},
        "status": {"short": "H"},
        "date": {"start": "2023-03-01T20:00:00Z"},
    }
    result = client._parse_game(game_data, "NFL")
    assert result is not None
    assert result.status == "in_progress"


def test_get_headers(client: RapidAPIClient):
    """_get_headers returns correct RapidAPI headers."""
    headers = client._get_headers("some-host")
    assert "X-RapidAPI-Key" in headers
    assert headers["X-RapidAPI-Host"] == "some-host"

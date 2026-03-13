import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.services.sports_api.espn_client import ESPNAPIClient
from app.services.sports_api.base import GameData


@pytest.fixture
def client():
    return ESPNAPIClient()


@pytest.mark.asyncio
async def test_get_schedule_success(client: ESPNAPIClient):
    """Test get_schedule successfully fetches and parses data."""
    mock_response = {
        "events": [
            {
                "id": "test_game_1",
                "date": "2023-01-01T20:00:00Z",
                "status": {"type": {"state": "pre"}},
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {
                                    "id": "1",
                                    "displayName": "Team A",
                                    "abbreviation": "TA",
                                },
                            },
                            {
                                "homeAway": "away",
                                "team": {
                                    "id": "2",
                                    "displayName": "Team B",
                                    "abbreviation": "TB",
                                },
                            },
                        ]
                    }
                ],
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
        assert games[0].external_id == "test_game_1"
        assert games[0].home_team == "Team A"


def test_map_league_name(client: ESPNAPIClient):
    """Test internal league names are correctly mapped."""
    assert client._map_league_name("NFL") == "football/nfl"
    assert client._map_league_name("NBA") == "basketball/nba"
    assert client._map_league_name("UNKNOWN") == "unknown"
    assert client._map_league_name("MLB") == "baseball/mlb"
    assert client._map_league_name("NHL") == "hockey/nhl"
    assert client._map_league_name("NCAA_BASKETBALL") == "basketball/mens-college-basketball"
    assert client._map_league_name("NCAA_FOOTBALL") == "football/college-football"


@pytest.mark.asyncio
async def test_get_schedule_returns_empty_on_exception(client: ESPNAPIClient):
    """get_schedule swallows generic exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("network error")
        games = await client.get_schedule("NFL", datetime(2023, 1, 1), datetime(2023, 1, 3))
        assert games == []


@pytest.mark.asyncio
async def test_get_live_scores_success(client: ESPNAPIClient):
    """get_live_scores parses events and returns GameData list."""
    mock_response = {
        "events": [
            {
                "id": "live_1",
                "date": "2023-10-01T14:00:00Z",
                "status": {"type": {"state": "in"}},
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {"id": "10", "displayName": "Chiefs", "abbreviation": "KC"},
                                "score": "17",
                            },
                            {
                                "homeAway": "away",
                                "team": {"id": "20", "displayName": "Raiders", "abbreviation": "LV"},
                                "score": "10",
                            },
                        ]
                    }
                ],
            }
        ]
    }
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        games = await client.get_live_scores("NFL")
        assert len(games) == 1
        assert games[0].status == "in_progress"
        assert games[0].home_score == 17
        assert games[0].away_score == 10


@pytest.mark.asyncio
async def test_get_live_scores_empty_events(client: ESPNAPIClient):
    """get_live_scores returns [] when response has no events."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={"events": []}):
        games = await client.get_live_scores("NFL")
        assert games == []


@pytest.mark.asyncio
async def test_get_live_scores_returns_empty_on_exception(client: ESPNAPIClient):
    """get_live_scores swallows generic exceptions and returns []."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("timeout")
        games = await client.get_live_scores("NBA")
        assert games == []


@pytest.mark.asyncio
async def test_get_game_details_success(client: ESPNAPIClient):
    """get_game_details returns a GameData for a valid header response."""
    mock_response = {
        "header": {
            "id": "detail_1",
            "date": "2023-11-01T20:00:00Z",
            "status": {"type": {"state": "post"}},
            "competitions": [
                {
                    "competitors": [
                        {
                            "homeAway": "home",
                            "team": {"id": "1", "displayName": "Team A", "abbreviation": "TA"},
                            "score": "30",
                        },
                        {
                            "homeAway": "away",
                            "team": {"id": "2", "displayName": "Team B", "abbreviation": "TB"},
                            "score": "27",
                        },
                    ]
                }
            ],
        }
    }
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
        game = await client.get_game_details("NFL", "detail_1")
        assert game is not None
        assert game.status == "final"


@pytest.mark.asyncio
async def test_get_game_details_not_found(client: ESPNAPIClient):
    """get_game_details returns None when header is missing."""
    with patch.object(client, "_make_request", new_callable=AsyncMock, return_value={}):
        game = await client.get_game_details("NFL", "missing_id")
        assert game is None


@pytest.mark.asyncio
async def test_get_game_details_returns_none_on_exception(client: ESPNAPIClient):
    """get_game_details swallows errors and returns None."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("error")
        game = await client.get_game_details("NFL", "any_id")
        assert game is None


def test_parse_event_no_competitions_returns_none(client: ESPNAPIClient):
    """_parse_event returns None when competitions list is empty."""
    assert client._parse_event({"id": "x", "competitions": []}) is None


def test_parse_event_insufficient_competitors_returns_none(client: ESPNAPIClient):
    """_parse_event returns None when fewer than 2 competitors."""
    event = {
        "id": "x",
        "competitions": [{"competitors": [{"homeAway": "home", "team": {"id": "1", "displayName": "A", "abbreviation": "A"}}]}],
    }
    assert client._parse_event(event) is None


def test_parse_event_missing_home_team_returns_none(client: ESPNAPIClient):
    """_parse_event returns None when home team cannot be determined."""
    event = {
        "id": "x",
        "date": "2023-01-01T00:00:00Z",
        "status": {"type": {"state": "pre"}},
        "competitions": [
            {
                "competitors": [
                    {"homeAway": "away", "team": {"id": "1", "displayName": "A", "abbreviation": "A"}},
                    {"homeAway": "away", "team": {"id": "2", "displayName": "B", "abbreviation": "B"}},
                ]
            }
        ],
    }
    assert client._parse_event(event) is None


def test_parse_event_with_venue(client: ESPNAPIClient):
    """_parse_event correctly extracts venue name."""
    event = {
        "id": "v_game",
        "date": "2023-01-01T18:00:00Z",
        "status": {"type": {"state": "post"}},
        "competitions": [
            {
                "venue": {"fullName": "Arrowhead Stadium"},
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"id": "1", "displayName": "Chiefs", "abbreviation": "KC"},
                        "score": "24",
                    },
                    {
                        "homeAway": "away",
                        "team": {"id": "2", "displayName": "Raiders", "abbreviation": "LV"},
                        "score": "14",
                    },
                ],
            }
        ],
    }
    result = client._parse_event(event)
    assert result is not None
    assert result.venue == "Arrowhead Stadium"


def test_parse_event_non_digit_score_treated_as_none(client: ESPNAPIClient):
    """_parse_event handles non-numeric score values gracefully."""
    event = {
        "id": "pre_game",
        "date": "2023-01-01T18:00:00Z",
        "status": {"type": {"state": "pre"}},
        "competitions": [
            {
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"id": "1", "displayName": "X", "abbreviation": "X"},
                        "score": "-",
                    },
                    {
                        "homeAway": "away",
                        "team": {"id": "2", "displayName": "Y", "abbreviation": "Y"},
                        "score": "",
                    },
                ]
            }
        ],
    }
    result = client._parse_event(event)
    assert result is not None
    assert result.home_score is None
    assert result.away_score is None


def test_parse_event_with_odds(client: ESPNAPIClient):
    """_parse_event correctly extracts spread and overUnder."""
    event = {
        "id": "odds_game",
        "date": "2023-01-01T18:00:00Z",
        "status": {"type": {"state": "pre"}},
        "competitions": [
            {
                "odds": [
                    {
                        "provider": {"name": "DraftKings"},
                        "details": "KC -4.5",
                        "overUnder": 48.5,
                        "spread": -4.5,
                    }
                ],
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"id": "1", "displayName": "Chiefs", "abbreviation": "KC"},
                    },
                    {
                        "homeAway": "away",
                        "team": {"id": "2", "displayName": "Raiders", "abbreviation": "LV"},
                    },
                ],
            }
        ],
    }
    result = client._parse_event(event)
    assert result is not None
    assert result.spread == -4.5
    assert result.over_under == 48.5


def test_parse_event_with_away_favorite_odds(client: ESPNAPIClient):
    """_parse_event correctly inverts the spread if the away team is favored."""
    event = {
        "id": "away_fav",
        "date": "2023-01-01T18:00:00Z",
        "status": {"type": {"state": "pre"}},
        "competitions": [
            {
                "odds": [
                    {
                        "provider": {"name": "DraftKings"},
                        "details": "LV -3.5",
                        "spread": -3.5,
                    }
                ],
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"id": "1", "displayName": "Chiefs", "abbreviation": "KC"},
                    },
                    {
                        "homeAway": "away",
                        "team": {"id": "2", "displayName": "Raiders", "abbreviation": "LV"},
                    },
                ],
            }
        ],
    }
    result = client._parse_event(event)
    assert result is not None
    # Away favored by 3.5 (-3.5) means Home spread is +3.5
    assert result.spread == 3.5


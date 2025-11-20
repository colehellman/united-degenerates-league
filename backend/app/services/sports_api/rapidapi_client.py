from typing import List, Optional
from datetime import datetime
import logging

from app.services.sports_api.base import (
    BaseSportsAPIClient,
    APIProvider,
    GameData,
    RateLimitExceededError,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class RapidAPIClient(BaseSportsAPIClient):
    """RapidAPI Sports client implementation"""

    def __init__(self):
        super().__init__(APIProvider.RAPIDAPI)
        self.api_key = settings.RAPIDAPI_KEY

    def _map_league_name(self, league: str) -> str:
        """Map internal league names to RapidAPI hosts"""
        mapping = {
            "NFL": settings.RAPIDAPI_HOST_NFL,
            "NBA": settings.RAPIDAPI_HOST_NBA,
            "MLB": settings.RAPIDAPI_HOST_MLB,
            "NHL": settings.RAPIDAPI_HOST_NHL,
            "NCAA_BASKETBALL": settings.RAPIDAPI_HOST_NCAA,
            "NCAA_FOOTBALL": settings.RAPIDAPI_HOST_NCAA,
            "PGA": settings.RAPIDAPI_HOST_GOLF,
        }
        return mapping.get(league, "")

    def _get_headers(self, host: str) -> dict:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": host,
        }

    async def get_schedule(
        self,
        league: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[GameData]:
        """Fetch game schedule from RapidAPI"""
        try:
            host = self._map_league_name(league)
            if not host:
                logger.warning(f"RapidAPI: No host mapping for {league}")
                return []

            url = f"https://{host}/games"

            # Date format varies by API, using common ISO format
            params = {
                "date": start_date.strftime("%Y-%m-%d"),
                "season": start_date.year,
            }

            headers = self._get_headers(host)
            response = await self._make_request("GET", url, headers=headers, params=params)

            games = []

            # RapidAPI response format varies, handle common structures
            results = response.get("response", [])
            if isinstance(results, list):
                for game_data in results:
                    parsed_game = self._parse_game(game_data, league)
                    if parsed_game:
                        games.append(parsed_game)

            logger.info(f"RapidAPI: Fetched {len(games)} games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"RapidAPI: Error fetching schedule for {league}: {str(e)}")
            return []

    async def get_live_scores(self, league: str) -> List[GameData]:
        """Fetch live scores from RapidAPI"""
        try:
            host = self._map_league_name(league)
            if not host:
                logger.warning(f"RapidAPI: No host mapping for {league}")
                return []

            url = f"https://{host}/games"

            params = {
                "live": "all",  # Get all live games
            }

            headers = self._get_headers(host)
            response = await self._make_request("GET", url, headers=headers, params=params)

            games = []
            results = response.get("response", [])

            if isinstance(results, list):
                for game_data in results:
                    parsed_game = self._parse_game(game_data, league)
                    if parsed_game and parsed_game.status == "in_progress":
                        games.append(parsed_game)

            logger.info(f"RapidAPI: Fetched {len(games)} live games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"RapidAPI: Error fetching live scores for {league}: {str(e)}")
            return []

    async def get_game_details(self, league: str, game_id: str) -> Optional[GameData]:
        """Fetch game details from RapidAPI"""
        try:
            host = self._map_league_name(league)
            if not host:
                logger.warning(f"RapidAPI: No host mapping for {league}")
                return None

            url = f"https://{host}/games"

            params = {"id": game_id}
            headers = self._get_headers(host)

            response = await self._make_request("GET", url, headers=headers, params=params)

            results = response.get("response", [])
            if isinstance(results, list) and len(results) > 0:
                return self._parse_game(results[0], league)

            return None

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"RapidAPI: Error fetching game {game_id}: {str(e)}")
            return None

    def _parse_game(self, game_data: dict, league: str) -> Optional[GameData]:
        """Parse RapidAPI game data into standardized GameData"""
        try:
            # RapidAPI structure varies by sport, handle common patterns

            # Try NBA/NFL structure
            teams = game_data.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("visitors", {}) or teams.get("away", {})

            home_team = home.get("name", "") or home.get("nickname", "")
            away_team = away.get("name", "") or away.get("nickname", "")

            if not home_team or not away_team:
                return None

            # Scores
            scores = game_data.get("scores", {})
            home_score_data = scores.get("home", {})
            away_score_data = scores.get("visitors", {}) or scores.get("away", {})

            home_score = home_score_data.get("points") or home_score_data.get("total")
            away_score = away_score_data.get("points") or away_score_data.get("total")

            # Parse status
            status_short = game_data.get("status", {}).get("short", "NS")
            status_map = {
                "NS": "scheduled",  # Not Started
                "1": "in_progress",
                "2": "in_progress",
                "3": "in_progress",
                "4": "in_progress",
                "H": "in_progress",  # Halftime
                "FT": "final",
                "AOT": "final",  # After Overtime
                "AP": "final",  # After Penalties
            }
            status = status_map.get(status_short, "scheduled")

            # Parse datetime
            date_str = game_data.get("date", {}).get("start", "")
            scheduled_time = self._parse_datetime(date_str) if date_str else datetime.utcnow()

            # Venue
            venue = game_data.get("arena", {}).get("name") or game_data.get("venue", {}).get("name")

            return GameData(
                external_id=str(game_data.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                scheduled_start_time=scheduled_time,
                status=status,
                home_score=int(home_score) if home_score else None,
                away_score=int(away_score) if away_score else None,
                venue=venue,
                raw_data=game_data,
            )

        except Exception as e:
            logger.error(f"RapidAPI: Error parsing game data: {str(e)}")
            return None

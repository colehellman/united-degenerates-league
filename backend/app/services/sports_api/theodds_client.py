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


class TheOddsAPIClient(BaseSportsAPIClient):
    """The Odds API client implementation"""

    def __init__(self):
        super().__init__(APIProvider.THE_ODDS_API)
        self.base_url = settings.THE_ODDS_API_BASE_URL
        self.api_key = settings.THE_ODDS_API_KEY

    def _map_league_name(self, league: str) -> str:
        """Map internal league names to The Odds API sport keys"""
        mapping = {
            "NFL": "americanfootball_nfl",
            "NBA": "basketball_nba",
            "MLB": "baseball_mlb",
            "NHL": "icehockey_nhl",
            "NCAA_BASKETBALL": "basketball_ncaab",
            "NCAA_FOOTBALL": "americanfootball_ncaaf",
        }
        return mapping.get(league, league.lower())

    async def get_schedule(
        self,
        league: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[GameData]:
        """Fetch game schedule from The Odds API"""
        try:
            sport_key = self._map_league_name(league)
            url = f"{self.base_url}/sports/{sport_key}/odds"

            params = {
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h",  # Head-to-head for game results
                "dateFormat": "iso",
            }

            response = await self._make_request("GET", url, params=params)

            games = []
            if isinstance(response, list):
                for event in response:
                    game_data = self._parse_event(event)
                    if game_data:
                        # Filter by date range
                        if start_date <= game_data.scheduled_start_time <= end_date:
                            games.append(game_data)

            logger.info(f"TheOddsAPI: Fetched {len(games)} games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"TheOddsAPI: Error fetching schedule for {league}: {str(e)}")
            return []

    async def get_live_scores(self, league: str) -> List[GameData]:
        """Fetch live scores from The Odds API"""
        try:
            sport_key = self._map_league_name(league)
            url = f"{self.base_url}/sports/{sport_key}/scores"

            params = {
                "apiKey": self.api_key,
                "daysFrom": 1,  # Last 1 day
                "dateFormat": "iso",
            }

            response = await self._make_request("GET", url, params=params)

            games = []
            if isinstance(response, list):
                for event in response:
                    # Filter for completed or live games
                    if not event.get("completed", False):
                        game_data = self._parse_score_event(event)
                        if game_data:
                            games.append(game_data)

            logger.info(f"TheOddsAPI: Fetched {len(games)} live games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"TheOddsAPI: Error fetching live scores for {league}: {str(e)}")
            return []

    async def get_game_details(self, league: str, game_id: str) -> Optional[GameData]:
        """
        The Odds API doesn't have individual game endpoints,
        so we fetch from the scores endpoint and filter
        """
        try:
            sport_key = self._map_league_name(league)
            url = f"{self.base_url}/sports/{sport_key}/scores"

            params = {
                "apiKey": self.api_key,
                "daysFrom": 3,  # Last 3 days
                "dateFormat": "iso",
            }

            response = await self._make_request("GET", url, params=params)

            if isinstance(response, list):
                for event in response:
                    if event.get("id") == game_id:
                        return self._parse_score_event(event)

            return None

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"TheOddsAPI: Error fetching game {game_id}: {str(e)}")
            return None

    def _parse_event(self, event: dict) -> Optional[GameData]:
        """Parse The Odds API event data (from odds endpoint)"""
        try:
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")

            if not home_team or not away_team:
                return None

            # Parse datetime
            commence_time = event.get("commence_time", "")
            scheduled_time = self._parse_datetime(commence_time) if commence_time else datetime.utcnow()

            return GameData(
                external_id=event.get("id", ""),
                home_team=home_team,
                away_team=away_team,
                scheduled_start_time=scheduled_time,
                status="scheduled",
                home_score=None,
                away_score=None,
                venue=None,
                raw_data=event,
            )

        except Exception as e:
            logger.error(f"TheOddsAPI: Error parsing event: {str(e)}")
            return None

    def _parse_score_event(self, event: dict) -> Optional[GameData]:
        """Parse The Odds API score data (from scores endpoint)"""
        try:
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")

            if not home_team or not away_team:
                return None

            # Get scores
            scores = event.get("scores", [])
            home_score = None
            away_score = None

            for score in scores:
                if score.get("name") == home_team:
                    home_score = int(score.get("score", 0))
                elif score.get("name") == away_team:
                    away_score = int(score.get("score", 0))

            # Parse datetime
            commence_time = event.get("commence_time", "")
            scheduled_time = self._parse_datetime(commence_time) if commence_time else datetime.utcnow()

            # Determine status
            completed = event.get("completed", False)
            status = "final" if completed else "in_progress"

            return GameData(
                external_id=event.get("id", ""),
                home_team=home_team,
                away_team=away_team,
                scheduled_start_time=scheduled_time,
                status=status,
                home_score=home_score,
                away_score=away_score,
                venue=None,
                raw_data=event,
            )

        except Exception as e:
            logger.error(f"TheOddsAPI: Error parsing score event: {str(e)}")
            return None

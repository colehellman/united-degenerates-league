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


class ESPNAPIClient(BaseSportsAPIClient):
    """ESPN API client implementation"""

    def __init__(self):
        super().__init__(APIProvider.ESPN)
        self.base_url = settings.ESPN_API_BASE_URL
        self.api_key = settings.ESPN_API_KEY

    def _map_league_name(self, league: str) -> str:
        """Map internal league names to ESPN sport/league identifiers"""
        mapping = {
            "NFL": "football/nfl",
            "NBA": "basketball/nba",
            "MLB": "baseball/mlb",
            "NHL": "hockey/nhl",
            "NCAA_BASKETBALL": "basketball/mens-college-basketball",
            "NCAA_FOOTBALL": "football/college-football",
        }
        return mapping.get(league, league.lower())

    async def get_schedule(
        self,
        league: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[GameData]:
        """Fetch game schedule from ESPN API"""
        try:
            league_path = self._map_league_name(league)
            url = f"{self.base_url}/{league_path}/scoreboard"

            # ESPN uses dates parameter (YYYYMMDD format)
            params = {
                "dates": start_date.strftime("%Y%m%d"),
            }

            if self.api_key:
                params["apikey"] = self.api_key

            response = await self._make_request("GET", url, params=params)

            games = []
            events = response.get("events", [])

            for event in events:
                game_data = self._parse_event(event)
                if game_data:
                    games.append(game_data)

            logger.info(f"ESPN: Fetched {len(games)} games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"ESPN: Error fetching schedule for {league}: {str(e)}")
            return []

    async def get_live_scores(self, league: str) -> List[GameData]:
        """Fetch live scores from ESPN API"""
        try:
            league_path = self._map_league_name(league)
            url = f"{self.base_url}/{league_path}/scoreboard"

            params = {}
            if self.api_key:
                params["apikey"] = self.api_key

            response = await self._make_request("GET", url, params=params)

            games = []
            events = response.get("events", [])

            # Filter for live/in-progress games
            for event in events:
                status = event.get("status", {}).get("type", {}).get("state", "")
                if status.lower() in ["in", "live"]:
                    game_data = self._parse_event(event)
                    if game_data:
                        games.append(game_data)

            logger.info(f"ESPN: Fetched {len(games)} live games for {league}")
            return games

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"ESPN: Error fetching live scores for {league}: {str(e)}")
            return []

    async def get_game_details(self, league: str, game_id: str) -> Optional[GameData]:
        """Fetch game details from ESPN API"""
        try:
            league_path = self._map_league_name(league)
            url = f"{self.base_url}/{league_path}/summary"

            params = {"event": game_id}
            if self.api_key:
                params["apikey"] = self.api_key

            response = await self._make_request("GET", url, params=params)

            event = response.get("header", {})
            if event:
                return self._parse_event(event)

            return None

        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"ESPN: Error fetching game {game_id}: {str(e)}")
            return None

    def _parse_event(self, event: dict) -> Optional[GameData]:
        """Parse ESPN event data into standardized GameData"""
        try:
            competitions = event.get("competitions", [])
            if not competitions:
                return None

            competition = competitions[0]
            competitors = competition.get("competitors", [])

            if len(competitors) < 2:
                return None

            # ESPN typically has home team at index 0
            home_team = None
            away_team = None

            for competitor in competitors:
                team_name = competitor.get("team", {}).get("displayName", "")
                score = competitor.get("score")
                home_away = competitor.get("homeAway", "")

                if home_away == "home":
                    home_team = {
                        "name": team_name,
                        "score": int(score) if score and score.isdigit() else None,
                    }
                else:
                    away_team = {
                        "name": team_name,
                        "score": int(score) if score and score.isdigit() else None,
                    }

            if not home_team or not away_team:
                return None

            # Parse game status
            status_type = event.get("status", {}).get("type", {}).get("state", "pre")
            status_map = {
                "pre": "scheduled",
                "in": "in_progress",
                "post": "final",
            }
            status = status_map.get(status_type.lower(), "scheduled")

            # Parse datetime
            date_str = event.get("date", "")
            scheduled_time = self._parse_datetime(date_str) if date_str else datetime.utcnow()

            # Venue
            venue = competition.get("venue", {}).get("fullName")

            return GameData(
                external_id=event.get("id", ""),
                home_team=home_team["name"],
                away_team=away_team["name"],
                scheduled_start_time=scheduled_time,
                status=status,
                home_score=home_team["score"],
                away_score=away_team["score"],
                venue=venue,
                raw_data=event,
            )

        except Exception as e:
            logger.error(f"ESPN: Error parsing event: {str(e)}")
            return None

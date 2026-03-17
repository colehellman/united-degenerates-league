import logging
from datetime import datetime

from app.core.config import settings
from app.services.sports_api.base import (
    APIProvider,
    BaseSportsAPIClient,
    GameData,
    RateLimitExceededError,
)

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
    ) -> list[GameData]:
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
            logger.error(f"ESPN: Error fetching schedule for {league}: {e!s}")
            return []

    async def get_live_scores(self, league: str) -> list[GameData]:
        """Fetch today's scoreboard from ESPN API.

        Returns ALL games (scheduled, in-progress, final) so the background
        job can create new games, update scores, and detect completed games.
        """
        try:
            league_path = self._map_league_name(league)
            url = f"{self.base_url}/{league_path}/scoreboard"

            params = {}
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
            logger.error(f"ESPN: Error fetching scores for {league}: {e!s}")
            return []

    async def get_game_details(self, league: str, game_id: str) -> GameData | None:
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
            logger.error(f"ESPN: Error fetching game {game_id}: {e!s}")
            return None

    def _parse_event(self, event: dict) -> GameData | None:
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
                team_data = competitor.get("team", {})
                team_name = team_data.get("displayName", "")
                team_abbr = team_data.get("abbreviation", "")
                team_ext_id = team_data.get("id", "")
                score = competitor.get("score")
                home_away = competitor.get("homeAway", "")

                # Parse season record from ESPN's "records" array.
                # ESPN returns a list of record objects; "overall"/"total" is the
                # full-season win-loss-tie, e.g. {"name":"overall","summary":"12-5"}.
                wins = losses = ties = None
                for rec in competitor.get("records", []):
                    rec_name = rec.get("name", "").lower()
                    rec_type = rec.get("type", "").lower()
                    if rec_name in ("overall", "total") or rec_type in ("total",):
                        summary = rec.get("summary", "")
                        parts = summary.split("-")
                        try:
                            wins = int(parts[0]) if len(parts) > 0 else None
                            losses = int(parts[1]) if len(parts) > 1 else None
                            ties = int(parts[2]) if len(parts) > 2 else None
                        except (ValueError, IndexError):
                            pass
                        break

                info = {
                    "name": team_name,
                    "score": int(score) if score and score.isdigit() else None,
                    "external_id": str(team_ext_id),
                    "abbreviation": team_abbr,
                    "wins": wins,
                    "losses": losses,
                    "ties": ties,
                }

                if home_away == "home":
                    home_team = info
                else:
                    away_team = info

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

            # Parse betting odds (DraftKings is ESPN's primary provider)
            spread = None
            over_under = None
            odds_list = competition.get("odds", [])
            if odds_list:
                # Use the first odds object, or try to find DraftKings
                odds = odds_list[0]
                for o in odds_list:
                    if o.get("provider", {}).get("name", "").lower() == "draftkings":
                        odds = o
                        break

                over_under = odds.get("overUnder")
                # ESPN spread is a float. It doesn't explicitly state 'home' vs 'away'
                # perspective in the raw float, but the 'details' string often does.
                # However, DraftKings odds in the scoreboard API usually follow
                # the standard: negative = favorite.
                # We need to ensure we store it from the HOME team's perspective.
                # If 'details' says "LAL -4.5" and LAL is away, home spread is +4.5.
                raw_spread = odds.get("spread")
                details = odds.get("details", "")

                if raw_spread is not None:
                    spread = float(raw_spread)
                    # If the details string mentions the AWAY team's abbreviation
                    # followed by a negative number (e.g. "AWAY -4.5"), then the
                    # away team is the favorite, and the HOME spread should be positive.
                    away_abbr = away_team.get("abbreviation", "")
                    if away_abbr and details.startswith(away_abbr):
                        # If the details string starts with away abbreviation and the
                        # spread is negative, it means away is favored.
                        # raw_spread is usually the absolute value of the favorite's spread
                        # in some API versions, but in others it's already signed.
                        # Testing shows ESPN's 'spread' field is usually the favorite's spread (negative).
                        # So if details="AWAY -4.5", spread=-4.5.
                        # To get home perspective: if away is -4.5, home is +4.5.
                        spread = -spread

            return GameData(
                external_id=event.get("id", ""),
                home_team=home_team["name"],
                away_team=away_team["name"],
                scheduled_start_time=scheduled_time,
                status=status,
                home_score=home_team["score"],
                away_score=away_team["score"],
                venue=venue,
                # We only store fields relevant to competition rules — no raw API bloat.
                # ESPN event payloads are 50-200KB each; storing them in game.api_data
                # would inflate the DB and Redis cache with no benefit to scoring logic.
                raw_data={},
                home_team_external_id=home_team["external_id"],
                away_team_external_id=away_team["external_id"],
                home_team_abbreviation=home_team["abbreviation"],
                away_team_abbreviation=away_team["abbreviation"],
                home_team_wins=home_team["wins"],
                home_team_losses=home_team["losses"],
                home_team_ties=home_team["ties"],
                away_team_wins=away_team["wins"],
                away_team_losses=away_team["losses"],
                away_team_ties=away_team["ties"],
                spread=spread,
                over_under=over_under,
            )

        except Exception as e:
            logger.error(f"ESPN: Error parsing event: {e!s}")
            return None

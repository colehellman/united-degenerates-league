import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class APIProvider(str, Enum):
    ESPN = "espn"
    THE_ODDS_API = "the_odds_api"
    RAPIDAPI = "rapidapi"
    SPORTSDATA = "sportsdata"
    MLB_STATS = "mlb_stats"
    NHL_STATS = "nhl_stats"
    PGA_TOUR = "pga_tour"


class GameData:
    """Standardized game data structure"""

    def __init__(
        self,
        external_id: str,
        home_team: str,
        away_team: str,
        scheduled_start_time: datetime,
        status: str,
        home_score: int | None = None,
        away_score: int | None = None,
        venue: str | None = None,
        raw_data: dict | None = None,
        # Team identifiers for matching/creating team records
        home_team_external_id: str | None = None,
        away_team_external_id: str | None = None,
        home_team_abbreviation: str | None = None,
        away_team_abbreviation: str | None = None,
        # Season win/loss/tie record at the time the game data was fetched.
        # Sourced from the "overall" record in the sports API response.
        # None means the API did not provide record data for this team.
        home_team_wins: int | None = None,
        home_team_losses: int | None = None,
        home_team_ties: int | None = None,
        away_team_wins: int | None = None,
        away_team_losses: int | None = None,
        away_team_ties: int | None = None,
        # Betting odds sourced from ESPN (DraftKings).
        # spread is home-team perspective: -3.5 means home favored by 3.5.
        # None when the API does not supply odds (e.g. pre-season, non-covered leagues).
        spread: float | None = None,
        over_under: float | None = None,
    ):
        self.external_id = external_id
        self.home_team = home_team
        self.away_team = away_team
        self.scheduled_start_time = scheduled_start_time
        self.status = status
        self.home_score = home_score
        self.away_score = away_score
        self.venue = venue
        self.raw_data = raw_data or {}
        self.home_team_external_id = home_team_external_id
        self.away_team_external_id = away_team_external_id
        self.home_team_abbreviation = home_team_abbreviation
        self.away_team_abbreviation = away_team_abbreviation
        self.home_team_wins = home_team_wins
        self.home_team_losses = home_team_losses
        self.home_team_ties = home_team_ties
        self.away_team_wins = away_team_wins
        self.away_team_losses = away_team_losses
        self.away_team_ties = away_team_ties
        self.spread = spread
        self.over_under = over_under


class BaseSportsAPIClient(ABC):
    """
    Abstract base class for sports API clients.

    All API implementations must inherit from this and implement the required methods.
    """

    def __init__(self, provider: APIProvider):
        self.provider = provider
        self.client = httpx.AsyncClient(
            timeout=settings.API_TIMEOUT_SECONDS,
            follow_redirects=True,
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    @abstractmethod
    async def get_schedule(
        self,
        league: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[GameData]:
        """
        Fetch game schedule for a league within a date range.

        Args:
            league: League identifier (e.g., "NFL", "NBA")
            start_date: Start of date range (UTC)
            end_date: End of date range (UTC)

        Returns:
            List of GameData objects
        """

    @abstractmethod
    async def get_live_scores(self, league: str) -> list[GameData]:
        """
        Fetch live scores for ongoing games in a league.

        Args:
            league: League identifier (e.g., "NFL", "NBA")

        Returns:
            List of GameData objects with current scores
        """

    @abstractmethod
    async def get_game_details(self, league: str, game_id: str) -> GameData | None:
        """
        Fetch detailed information for a specific game.

        Args:
            league: League identifier
            game_id: External game ID from the API

        Returns:
            GameData object or None if not found
        """

    @retry(
        stop=stop_after_attempt(settings.API_MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.API_RETRY_DELAY_SECONDS, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            headers: Optional headers
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses
            httpx.TimeoutException: For request timeouts
        """
        try:
            logger.debug(f"{self.provider}: {method} {url}")

            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"{self.provider}: Rate limit exceeded (429) - {url}")
                raise RateLimitExceededError(f"Rate limit exceeded for {self.provider}") from None
            if e.response.status_code >= 500:
                logger.error(f"{self.provider}: Server error ({e.response.status_code}) - {url}")
                raise
            logger.error(f"{self.provider}: Client error ({e.response.status_code}) - {url}")
            raise

        except httpx.TimeoutException:
            logger.warning(f"{self.provider}: Request timeout - {url}")
            raise

        except Exception as e:
            logger.error(f"{self.provider}: Unexpected error - {url}: {e!s}")
            raise

    def _parse_datetime(self, date_str: str) -> datetime:
        """
        Parse datetime string to UTC datetime.

        Override this in subclasses for provider-specific formats.
        """
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            # Add other format parsers as needed
            logger.warning(f"Could not parse datetime: {date_str}")
            return datetime.utcnow()

    @abstractmethod
    def _map_league_name(self, league: str) -> str:
        """
        Map internal league name to API-specific league identifier.

        Args:
            league: Internal league name (e.g., "NFL", "NBA")

        Returns:
            API-specific league identifier
        """


class RateLimitExceededError(Exception):
    """Raised when API rate limit is exceeded"""


class APIUnavailableError(Exception):
    """Raised when API is unavailable"""

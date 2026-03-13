from typing import List, Optional, Dict
from datetime import datetime
import logging
import json
import redis

from app.services.sports_api.base import (
    BaseSportsAPIClient,
    GameData,
    APIProvider,
    RateLimitExceededError,
    APIUnavailableError,
)
from app.services.sports_api.espn_client import ESPNAPIClient
from app.services.sports_api.theodds_client import TheOddsAPIClient
from app.services.sports_api.rapidapi_client import RapidAPIClient
from app.services.circuit_breaker import (
    circuit_breaker_manager,
    CircuitBreakerOpenError,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class SportsDataService:
    """
    Main service for fetching sports data with automatic failover between multiple APIs.

    Features:
    - Circuit breaker pattern for each API
    - Automatic fallback to alternative APIs
    - Redis caching for API responses
    - Rate limit handling
    """

    def __init__(self):
        # Initialize API clients in priority order
        self.clients: List[BaseSportsAPIClient] = []

        # ESPN hidden API is always available (no key required).
        # If a key is set it will be passed as a query parameter,
        # but the public scoreboard endpoints work without one.
        self.clients.append(ESPNAPIClient())
        logger.info("SportsDataService: ESPN API client initialized (no key required)")

        # Initialize The Odds API client (secondary)
        if settings.THE_ODDS_API_KEY:
            self.clients.append(TheOddsAPIClient())
            logger.info("SportsDataService: The Odds API client initialized")

        # Initialize RapidAPI client (tertiary)
        if settings.RAPIDAPI_KEY:
            self.clients.append(RapidAPIClient())
            logger.info("SportsDataService: RapidAPI client initialized")

        if not self.clients:
            logger.warning("SportsDataService: No API clients configured!")

        # Initialize Redis for caching
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            logger.info("SportsDataService: Redis cache connected")
        except Exception as e:
            logger.error(f"SportsDataService: Redis connection failed: {e}")
            self.redis_client = None

    async def get_schedule(
        self,
        league: str,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True,
    ) -> List[GameData]:
        """
        Fetch game schedule with automatic failover.

        Tries each API in order until one succeeds.
        """
        cache_key = f"schedule:{league}:{start_date.date()}:{end_date.date()}"

        # Try cache first
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info(f"SportsDataService: Cache hit for {cache_key}")
                return self._deserialize_games(cached)

        # Try each API in priority order
        last_exception = None

        for client in self.clients:
            try:
                breaker = circuit_breaker_manager.get_breaker(
                    name=f"{client.provider}_schedule",
                    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    timeout_seconds=settings.CIRCUIT_BREAKER_TIMEOUT_SECONDS,
                )

                logger.info(
                    f"SportsDataService: Attempting {client.provider} for schedule ({league})"
                )

                # Execute with circuit breaker protection
                games = await breaker.async_call(client.get_schedule, league, start_date, end_date)

                if games:
                    logger.info(
                        f"SportsDataService: Success with {client.provider} - {len(games)} games"
                    )

                    # Cache the result
                    self._set_cache(
                        cache_key,
                        self._serialize_games(games),
                        ttl=settings.CACHE_SCHEDULE_SECONDS,
                    )

                    return games

            except CircuitBreakerOpenError as e:
                logger.warning(
                    f"SportsDataService: {client.provider} circuit breaker is open, skipping"
                )
                last_exception = e
                continue

            except RateLimitExceededError as e:
                logger.warning(
                    f"SportsDataService: {client.provider} rate limit exceeded, trying next API"
                )
                last_exception = e
                continue

            except Exception as e:
                logger.error(
                    f"SportsDataService: {client.provider} failed: {str(e)}"
                )
                last_exception = e
                continue

        # All APIs failed
        logger.error(
            f"SportsDataService: All APIs failed for schedule ({league}). "
            f"Last error: {str(last_exception)}"
        )

        raise APIUnavailableError(
            f"Failed to fetch schedule for {league} from all API providers"
        )

    async def get_live_scores(
        self,
        league: str,
        use_cache: bool = True,
    ) -> List[GameData]:
        """
        Fetch live scores with automatic failover.
        """
        cache_key = f"live_scores:{league}"

        # Try cache first (short TTL for live data)
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"SportsDataService: Cache hit for {cache_key}")
                return self._deserialize_games(cached)

        # Try each API in priority order
        last_exception = None

        for client in self.clients:
            try:
                breaker = circuit_breaker_manager.get_breaker(
                    name=f"{client.provider}_live_scores",
                    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    timeout_seconds=settings.CIRCUIT_BREAKER_TIMEOUT_SECONDS,
                )

                logger.debug(
                    f"SportsDataService: Attempting {client.provider} for live scores ({league})"
                )

                games = await breaker.async_call(client.get_live_scores, league)

                if games is not None:  # Allow empty list
                    logger.info(
                        f"SportsDataService: Success with {client.provider} - {len(games)} live games"
                    )

                    # Cache with short TTL for live data
                    self._set_cache(
                        cache_key,
                        self._serialize_games(games),
                        ttl=settings.CACHE_SCORES_SECONDS,
                    )

                    return games

            except CircuitBreakerOpenError:
                logger.warning(
                    f"SportsDataService: {client.provider} circuit breaker is open, skipping"
                )
                continue

            except RateLimitExceededError:
                logger.warning(
                    f"SportsDataService: {client.provider} rate limit exceeded, trying next API"
                )
                continue

            except Exception as e:
                logger.error(
                    f"SportsDataService: {client.provider} failed: {str(e)}"
                )
                last_exception = e
                continue

        # All APIs failed
        logger.error(
            f"SportsDataService: All APIs failed for live scores ({league}). "
            f"Last error: {str(last_exception)}"
        )

        raise APIUnavailableError(
            f"Failed to fetch live scores for {league} from all API providers"
        )

    async def get_game_details(
        self,
        league: str,
        game_id: str,
        use_cache: bool = True,
    ) -> Optional[GameData]:
        """
        Fetch game details with automatic failover.
        """
        cache_key = f"game_details:{league}:{game_id}"

        # Try cache first
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"SportsDataService: Cache hit for {cache_key}")
                games = self._deserialize_games(cached)
                return games[0] if games else None

        # Try each API
        for client in self.clients:
            try:
                breaker = circuit_breaker_manager.get_breaker(
                    name=f"{client.provider}_game_details",
                    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                    timeout_seconds=settings.CIRCUIT_BREAKER_TIMEOUT_SECONDS,
                )

                game = await breaker.async_call(client.get_game_details, league, game_id)

                if game:
                    logger.info(
                        f"SportsDataService: Success with {client.provider} for game {game_id}"
                    )

                    # Cache the result
                    self._set_cache(
                        cache_key,
                        self._serialize_games([game]),
                        ttl=settings.CACHE_SCORES_SECONDS,
                    )

                    return game

            except (CircuitBreakerOpenError, RateLimitExceededError):
                continue
            except Exception as e:
                logger.error(f"SportsDataService: {client.provider} failed: {str(e)}")
                continue

        logger.error(f"SportsDataService: All APIs failed for game {game_id}")
        return None

    def get_api_health_status(self) -> Dict:
        """Get health status of all API providers and circuit breakers"""
        return {
            "configured_apis": [client.provider for client in self.clients],
            "circuit_breakers": circuit_breaker_manager.get_all_status(),
            "cache_status": "connected" if self.redis_client else "disconnected",
        }

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def _set_cache(self, key: str, value: str, ttl: int):
        """Set value in Redis cache with TTL"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def _serialize_games(self, games: List[GameData]) -> str:
        """Serialize GameData objects to JSON for Redis cache.

        Only stores fields relevant to competition rules -- no raw API bloat.
        raw_data is intentionally excluded: ESPN event payloads are 50-200KB
        each and would inflate the cache by 10-100x with no benefit.
        """
        data = []
        for game in games:
            game_dict = {
                "external_id": game.external_id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "scheduled_start_time": game.scheduled_start_time.isoformat(),
                "status": game.status,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "venue": game.venue,
                "home_team_external_id": game.home_team_external_id,
                "away_team_external_id": game.away_team_external_id,
                "home_team_abbreviation": game.home_team_abbreviation,
                "away_team_abbreviation": game.away_team_abbreviation,
                "home_team_wins": game.home_team_wins,
                "home_team_losses": game.home_team_losses,
                "home_team_ties": game.home_team_ties,
                "away_team_wins": game.away_team_wins,
                "away_team_losses": game.away_team_losses,
                "away_team_ties": game.away_team_ties,
                "spread": game.spread,
                "over_under": game.over_under,
            }
            data.append(game_dict)
        return json.dumps(data)

    def _deserialize_games(self, data: str) -> List[GameData]:
        """Deserialize JSON to GameData objects.

        Failures are isolated per-game so a single bad cache entry does not
        silently drop the entire league's game list.
        """
        try:
            games_data = json.loads(data)
        except Exception as e:
            logger.error(f"Error parsing cached game JSON: {e}")
            return []

        games = []
        for i, game_dict in enumerate(games_data):
            try:
                game = GameData(
                    external_id=game_dict["external_id"],
                    home_team=game_dict["home_team"],
                    away_team=game_dict["away_team"],
                    scheduled_start_time=datetime.fromisoformat(
                        game_dict["scheduled_start_time"]
                    ),
                    status=game_dict["status"],
                    home_score=game_dict.get("home_score"),
                    away_score=game_dict.get("away_score"),
                    venue=game_dict.get("venue"),
                    home_team_external_id=game_dict.get("home_team_external_id"),
                    away_team_external_id=game_dict.get("away_team_external_id"),
                    home_team_abbreviation=game_dict.get("home_team_abbreviation"),
                    away_team_abbreviation=game_dict.get("away_team_abbreviation"),
                    home_team_wins=game_dict.get("home_team_wins"),
                    home_team_losses=game_dict.get("home_team_losses"),
                    home_team_ties=game_dict.get("home_team_ties"),
                    away_team_wins=game_dict.get("away_team_wins"),
                    away_team_losses=game_dict.get("away_team_losses"),
                    away_team_ties=game_dict.get("away_team_ties"),
                    spread=game_dict.get("spread"),
                    over_under=game_dict.get("over_under"),
                )
                games.append(game)
            except Exception as e:
                external_id = game_dict.get("external_id", f"index={i}")
                logger.error(f"Error deserializing game {external_id}: {e}")
                continue
        return games

    async def close(self):
        """Close all API clients and connections"""
        for client in self.clients:
            await client.close()

        if self.redis_client:
            self.redis_client.close()


# Global instance
sports_service = SportsDataService()

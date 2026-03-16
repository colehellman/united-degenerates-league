from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://udl_user:udl_password@localhost:5432/udl_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    # Separate signing key for refresh tokens. Falls back to SECRET_KEY if unset.
    # In production, set a distinct value so compromising one key doesn't
    # compromise the other token type.
    REFRESH_SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Auth rate limiting (stricter than global limit)
    AUTH_RATE_LIMIT: str = "5/minute"
    # Account lockout after repeated failures
    AUTH_LOCKOUT_ATTEMPTS: int = 10
    AUTH_LOCKOUT_MINUTES: int = 15

    # Environment
    ENVIRONMENT: str = "development"

    # CORS — stored as comma-separated string, parsed to list at runtime
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        """Refuse to start in production if insecure defaults are still set.

        Catches misconfigured deploys before they silently accept weak JWTs
        or connect to a DB with a publicly-known password.
        """
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "dev-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed from the default in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if "udl_password" in self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL still contains the default development password. "
                    "Set a strong, unique password in production."
                )
        return self

    # Sports Data APIs - Multiple providers for failover
    # ESPN API
    ESPN_API_KEY: str = ""
    ESPN_API_BASE_URL: str = "https://site.api.espn.com/apis/site/v2/sports"

    # The Odds API
    THE_ODDS_API_KEY: str = ""
    THE_ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"

    # RapidAPI Sports
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_HOST_NFL: str = "api-american-football.p.rapidapi.com"
    RAPIDAPI_HOST_NBA: str = "api-nba-v1.p.rapidapi.com"
    RAPIDAPI_HOST_MLB: str = "api-baseball.p.rapidapi.com"
    RAPIDAPI_HOST_NHL: str = "api-hockey.p.rapidapi.com"
    RAPIDAPI_HOST_NCAA: str = "api-ncaa.p.rapidapi.com"
    RAPIDAPI_HOST_GOLF: str = "golf-leaderboard-data.p.rapidapi.com"
    RAPIDAPI_BASE_URL: str = "https://{host}"

    # SportsData.io (backup)
    SPORTSDATA_API_KEY: str = ""
    SPORTSDATA_BASE_URL: str = "https://api.sportsdata.io"

    # MLB Stats API (free, no key needed)
    MLB_STATS_API_URL: str = "https://statsapi.mlb.com/api/v1"

    # NHL Stats API (free, no key needed)
    NHL_STATS_API_URL: str = "https://api-web.nhle.com/v1"

    # PGA Tour API
    PGA_TOUR_API_KEY: str = ""
    PGA_TOUR_API_URL: str = "https://statdata.pgatour.com"

    # API Failover Configuration
    API_TIMEOUT_SECONDS: int = 10
    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY_SECONDS: int = 2

    # Circuit Breaker Settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = 60
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: str = "httpx.HTTPError"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    # Caching
    CACHE_SCORES_SECONDS: int = 60
    CACHE_LEADERBOARD_SECONDS: int = 30
    CACHE_USER_PREFS_SECONDS: int = 300
    CACHE_SCHEDULE_SECONDS: int = 3600  # 1 hour for schedules
    CACHE_API_RESPONSE_SECONDS: int = 300  # 5 minutes for API responses

    # Monitoring
    SENTRY_DSN: str = ""

    # Background Jobs
    SCORE_UPDATE_INTERVAL_SECONDS: int = 60
    # Set to True on API instances when running a separate worker process
    DISABLE_BACKGROUND_JOBS: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

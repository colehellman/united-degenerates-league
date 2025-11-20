from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://udl_user:udl_password@localhost:5432/udl_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Environment
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

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

    # Background Jobs
    SCORE_UPDATE_INTERVAL_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

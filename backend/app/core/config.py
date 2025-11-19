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

    # Sports Data APIs
    ESPN_API_KEY: str = ""
    SPORTSDATA_API_KEY: str = ""
    MLB_STATS_API_KEY: str = ""
    NHL_STATS_API_KEY: str = ""
    PGA_TOUR_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    # Caching
    CACHE_SCORES_SECONDS: int = 60
    CACHE_LEADERBOARD_SECONDS: int = 30
    CACHE_USER_PREFS_SECONDS: int = 300

    # Background Jobs
    SCORE_UPDATE_INTERVAL_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

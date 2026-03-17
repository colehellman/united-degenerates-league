from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Convert postgres:// or postgresql:// to postgresql+asyncpg:// and strip
# sslmode param (asyncpg doesn't accept sslmode — we handle SSL via
# connect_args instead).  Many cloud providers (Neon, Heroku) use the
# short-form postgres:// which SQLAlchemy async does not support directly.
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
if "sslmode=" in database_url:
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(database_url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items() if k != "sslmode"}
    database_url = urlunparse(parsed._replace(query=urlencode(params)))

# Neon and other cloud Postgres providers require SSL
connect_args = {}
if "neon.tech" in database_url or settings.ENVIRONMENT == "production":
    connect_args["ssl"] = True

engine = create_async_engine(
    database_url,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias used by background_jobs.py and other non-request contexts
async_session = AsyncSessionLocal

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.api import auth, users, competitions, picks, leaderboards, admin, health, ws, leagues, bug_reports

# Import for lifespan
from app.services.background_jobs import start_background_jobs, stop_background_jobs

logger = logging.getLogger(__name__)

# Configure structured logging for production
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

# Sentry error tracking (production only)
if settings.ENVIRONMENT == "production" and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )
    logger.info("Sentry initialized")

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


async def _seed_leagues_if_empty():
    """Auto-seed leagues on first boot. Idempotent — skips if leagues already exist."""
    from sqlalchemy import select, func
    from app.models.league import League, LeagueName

    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(League))
        if count and count > 0:
            return

        logger.info("No leagues found — seeding default leagues...")
        default_leagues = [
            (LeagueName.NFL, "National Football League", True),
            (LeagueName.NBA, "National Basketball Association", True),
            (LeagueName.MLB, "Major League Baseball", True),
            (LeagueName.NHL, "National Hockey League", True),
            (LeagueName.NCAA_BASKETBALL, "NCAA Men's Basketball", True),
            (LeagueName.NCAA_FOOTBALL, "NCAA Football", True),
            (LeagueName.PGA, "PGA Tour", False),
        ]
        for name, display_name, is_team_based in default_leagues:
            db.add(League(name=name, display_name=display_name, is_team_based=is_team_based))
        await db.commit()
        logger.info(f"Seeded {len(default_leagues)} leagues")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Refuse to start with default secret key in production
    if settings.ENVIRONMENT != "development" and settings.SECRET_KEY == "dev-secret-key-change-in-production":
        raise RuntimeError("SECRET_KEY must be changed in production. Set the SECRET_KEY environment variable.")

    logger.info("Starting United Degenerates League API...")

    # Auto-seed leagues if none exist (idempotent)
    await _seed_leagues_if_empty()

    # Start background jobs unless running a separate worker process
    if not settings.DISABLE_BACKGROUND_JOBS:
        start_background_jobs()
    else:
        logger.info("Background jobs disabled — expecting a separate worker process")

    # Always subscribe to Redis score channel so WebSocket clients
    # receive updates regardless of where the scheduler runs
    from app.services.ws_manager import score_manager
    await score_manager.start_subscriber()

    yield

    logger.info("Shutting down United Degenerates League API...")
    await score_manager.stop_subscriber()
    if not settings.DISABLE_BACKGROUND_JOBS:
        stop_background_jobs()


app = FastAPI(
    title="United Degenerates League API",
    description="API for the United Degenerates League sports prediction platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so unhandled exceptions return actionable JSON
    instead of a bare 'Internal Server Error' from uvicorn."""
    logger.error(
        f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    detail = (
        f"{type(exc).__name__}: {exc}"
        if settings.ENVIRONMENT == "development"
        else "Internal server error"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to every response"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["Competitions"])
app.include_router(picks.router, prefix="/api/picks", tags=["Picks"])
app.include_router(leaderboards.router, prefix="/api/leaderboards", tags=["Leaderboards"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(leagues.router, prefix="/api/leagues", tags=["Leagues"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(bug_reports.router, prefix="/api/bug-reports", tags=["Bug Reports"])
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    """Lightweight keepalive for UptimeRobot free tier (HEAD-only).
    /health is intercepted by Render's edge layer for HEAD requests; this
    path has no special Render handling so HEAD reaches FastAPI directly."""
    return Response(status_code=200)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "United Degenerates League API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Deep health check — verifies database and Redis connectivity"""
    checks = {"api": "ok"}

    # Check Postgres
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "error"

    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = "error"

    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(checks, status_code=status_code)

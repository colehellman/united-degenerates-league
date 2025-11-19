from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import auth, users, competitions, picks, leaderboards, admin

# Import for lifespan
from app.services.background_jobs import start_background_jobs, stop_background_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("Starting United Degenerates League API...")
    start_background_jobs()
    yield
    # Shutdown
    print("Shutting down United Degenerates League API...")
    stop_background_jobs()


app = FastAPI(
    title="United Degenerates League API",
    description="API for the United Degenerates League sports prediction platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["Competitions"])
app.include_router(picks.router, prefix="/api/picks", tags=["Picks"])
app.include_router(leaderboards.router, prefix="/api/leaderboards", tags=["Leaderboards"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


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
    """Health check endpoint"""
    return {"status": "healthy"}

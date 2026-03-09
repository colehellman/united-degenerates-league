# UDL — United Degenerates League

Sports prediction platform. FastAPI backend, React/TypeScript frontend, PostgreSQL, Redis.

## Quick Start

```bash
# Docker (recommended)
docker-compose up --build
docker-compose exec backend alembic upgrade head

# Manual — backend (Python 3.11 required, matches Dockerfile)
cd backend
python3.11 -m venv .venv          # one-time setup
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Manual — frontend
cd frontend && npm install && npm run dev
```

> **Python version**: The backend targets **Python 3.11** (same as the Docker image).
> Always activate `.venv` before running any backend commands locally.

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Stack

| Layer | Tech | Version |
|-------|------|---------|
| API | FastAPI + uvicorn | 0.109.0 |
| ORM | SQLAlchemy async | 2.0.25 |
| DB | PostgreSQL | 15 |
| Cache/PubSub | Redis | 7 |
| Auth | JWT (python-jose) | httpOnly cookies |
| Frontend | React + TypeScript | 18 + 5.2 |
| State | Zustand + TanStack Query | 4.4 + 5.17 |
| CSS | Tailwind | 3.3 |
| Jobs | APScheduler | 3.10 |
| Build | Vite | 5.0 |

## Project Layout

```
backend/
  app/
    api/          # Route handlers (auth, users, competitions, picks, leaderboards, admin, ws)
    core/         # config.py, security.py, deps.py
    db/           # session.py (async engine + session factory)
    models/       # SQLAlchemy ORM models (UUID PKs, async)
    schemas/      # Pydantic request/response models
    services/     # Business logic, sports API clients, background jobs, WebSocket manager
  alembic/        # Database migrations
  tests/          # pytest (asyncio mode=auto)
  worker.py       # Standalone background job process

frontend/
  src/
    pages/        # Route components (Login, Register, Dashboard, Competitions)
    components/   # Layout, ErrorBoundary
    services/     # api.ts (axios), authStore.ts (zustand)
    hooks/        # useLiveScores.ts (WebSocket)
    types/        # TypeScript interfaces
```

## Key Commands

```bash
# Backend tests (requires Postgres + Redis running)
cd backend && source .venv/bin/activate && pytest tests/ -v --tb=short

# Frontend
cd frontend && npm run lint && npm run build

# Database migrations
cd backend && source .venv/bin/activate && alembic upgrade head
cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "description"

# Standalone worker (production only)
cd backend && source .venv/bin/activate && python worker.py
```

## Architecture Notes

- **Auth**: JWT access (30min) + refresh (7d) tokens in httpOnly cookies. Bearer header also accepted. See `core/deps.py` for the dual-check logic.
- **Sports APIs**: Multi-provider failover (ESPN → Odds API → RapidAPI → SportsData → free MLB/NHL). Circuit breaker pattern in `services/circuit_breaker.py`.
- **Background jobs**: APScheduler runs score updates (60s), competition transitions (5min), pick locking (60s), account cleanup (daily 2AM). Can run in-process or as separate worker via `DISABLE_BACKGROUND_JOBS=true`.
- **WebSocket**: `/ws/scores` broadcasts live score updates. Redis pub/sub bridges worker↔API processes. See `services/ws_manager.py`.
- **Models**: All use UUID primary keys. Enums for status fields (UserRole, CompetitionStatus, GameStatus, etc.).

## Conventions

- **Python**: snake_case functions, PascalCase classes, full type hints, docstrings on public functions
- **TypeScript**: PascalCase components/pages, camelCase services/hooks, interfaces over types
- **Imports**: stdlib → third-party → local (3-group)
- **DB**: UUID PKs, `created_at`/`updated_at` timestamps, `relationship()` with `back_populates`
- **API**: Pydantic schemas for all request/response bodies, HTTPException for errors
- **Never delete** comments that explain "why" a decision was made

## Environment Variables

Backend (`backend/.env`):
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `SECRET_KEY` — JWT signing key (**must change in production**)
- `ENVIRONMENT` — `development` or `production`
- `CORS_ORIGINS` — Comma-separated allowed origins
- `DISABLE_BACKGROUND_JOBS` — `true` when running separate worker
- `SENTRY_DSN` — Error tracking (optional)
- Sports API keys: `ESPN_API_KEY`, `THE_ODDS_API_KEY`, `RAPIDAPI_KEY`, etc.

Frontend (`frontend/.env`):
- `VITE_API_URL` — Backend URL (build-time)

## Deployment

**Render.com** (free tier) with `render.yaml` blueprint:
1. **API** — Render Web Service (Docker, `backend/Dockerfile`)
2. **Frontend** — Render Static Site (CDN-backed, never sleeps)
3. **Postgres** — Neon (free, 0.5GB)
4. **Redis** — Upstash (free, 10k cmds/day)

Background jobs run in-process with the API on free tier. For paid tier,
set `DISABLE_BACKGROUND_JOBS=true` on API and deploy `worker.py` separately
via `backend/Dockerfile.worker`.

CI: `.github/workflows/ci.yml` runs on PR/push to main.

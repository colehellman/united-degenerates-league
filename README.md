# United Degenerates League (UDL)

[![CI](https://github.com/colehellman/united-degenerates-league/actions/workflows/ci.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/ci.yml)
[![E2E Tests](https://github.com/colehellman/united-degenerates-league/actions/workflows/e2e.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/e2e.yml)
[![Lighthouse CI](https://github.com/colehellman/united-degenerates-league/actions/workflows/lighthouse.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/lighthouse.yml)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://udl-frontend.onrender.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Sports prediction platform for competing in daily picks and fixed-team challenges across NFL, NBA, MLB, NHL, NCAA, and PGA. Built as a production-grade full-stack application with real infrastructure constraints in mind.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser Clients                       │
│                  React 18 + TanStack Query                   │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP + WebSocket (/ws/scores)
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI (async)                            │
│         JWT dual-auth · rate limiting · audit log            │
└──────┬────────────────┬────────────────────────┬────────────┘
       │                │                        │
┌──────▼──────┐  ┌──────▼──────┐  ┌─────────────▼───────────┐
│  PostgreSQL  │  │    Redis    │  │     Sports APIs          │
│  SQLAlchemy  │  │  pub/sub +  │  │  ESPN → TheOdds →        │
│  2.0 async   │  │   caching   │  │  RapidAPI → MLB/NHL      │
│  Alembic     │  │             │  │  (circuit breaker chain) │
└─────────────┘  └──────┬──────┘  └─────────────────────────┘
                        │ PUBLISH score_updates
               ┌────────▼────────┐
               │  Background     │
               │  Worker         │
               │  (APScheduler)  │
               └─────────────────┘
```

## Engineering Decisions

### Multi-Provider API Failover with Circuit Breaker — [ADR-002](docs/adr/002-sports-api-failover.md)

No single free sports API covers all leagues reliably. The `SportsService` orchestrator maintains a failover chain (ESPN → TheOdds → RapidAPI → MLB/NHL Stats APIs) where each provider is wrapped in a circuit breaker:

- Opens after 5 consecutive failures, stays open for 60 seconds
- CLOSED → OPEN → HALF_OPEN state machine — tests recovery before fully closing
- Circuit breaker state exposed at `GET /api/health/api-status` and resettable via API

### WebSocket Live Scores via Redis Pub/Sub — [ADR-003](docs/adr/003-websocket-redis-pubsub.md)

The background worker and API server run as separate processes. Score updates are published to a Redis channel by the worker; the API's `ScoreManager` subscribes and forwards to all connected WebSocket clients. This decouples score ingestion from delivery and keeps the architecture horizontally scalable.

- Subscriber loop reconnects with exponential backoff on Redis failures
- Frontend `useLiveScores` hook mirrors this with client-side auto-reconnect
- Falls back to direct in-process broadcast in single-process dev mode

### JWT Dual Authentication — [ADR-001](docs/adr/001-jwt-dual-auth.md)

Mobile Safari's Intelligent Tracking Prevention (ITP) blocks cross-origin `SameSite=None` cookies from `*.onrender.com` subdomains. The solution: httpOnly cookie auth for browsers that support it, Bearer token (stored in memory) as the primary path, refresh token in localStorage with short TTL and rotation. `get_current_user` checks Bearer first, then falls back to cookies.

### Async-First Backend

SQLAlchemy 2.0 async throughout — no sync sessions leaking into request handlers. Background jobs run in-process via APScheduler with async task execution to avoid blocking the event loop.

## Tech Stack

**Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL 15 · Redis · Alembic · APScheduler

**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · Zustand · Vitest

**Infrastructure:** Docker Compose · GitHub Actions (CI + E2E + Lighthouse) · Render · Neon (Postgres) · Upstash (Redis)

## Getting Started

### Quick Start with Docker

```bash
git clone https://github.com/colehellman/united-degenerates-league.git
cd united-degenerates-league
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY and optionally add sports API keys
docker-compose up --build
```

Then in a second terminal:

```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m scripts.seed_data
```

- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000/docs

### Local Dev (without Docker)

**Backend (Python 3.11):**
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install && npm run dev
```

**Environment variables** (all optional except `SECRET_KEY` and `DATABASE_URL`):

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret (required) |
| `DATABASE_URL` | PostgreSQL DSN |
| `REDIS_URL` | Redis URL |
| `THE_ODDS_API_KEY` | Sports odds data (free tier available) |
| `ESPN_API_KEY` | ESPN data (paid, most reliable) |
| `RAPIDAPI_KEY` | RapidAPI sports aggregator |

MLB and NHL Stats APIs require no key and work automatically.

## Project Structure

```
udl/
├── backend/
│   ├── alembic/versions/        # 8 migration versions
│   ├── app/
│   │   ├── api/                 # Endpoints: auth, competitions, picks, leaderboards, admin, ws
│   │   ├── core/                # Config, security, dependencies
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic validation
│   │   └── services/
│   │       ├── circuit_breaker.py   # Circuit breaker implementation
│   │       ├── ws_manager.py        # WebSocket + Redis pub/sub bridge
│   │       ├── sports_api/          # Multi-provider API clients
│   │       └── background_jobs.py   # APScheduler jobs
│   └── tests/
├── frontend/
│   └── src/
│       ├── hooks/useLiveScores.ts   # WebSocket auto-reconnect hook
│       ├── pages/                   # Competition, picks, leaderboard, admin views
│       └── services/                # API client, auth store (Zustand)
├── docs/adr/                    # Architecture decision records
└── docker-compose.yml
```

## Database Schema

| Model | Purpose |
|---|---|
| `User` | Auth and profile — soft delete with 30-day grace period |
| `Competition` | Daily Picks or Fixed Teams mode, public/private, approval-gated |
| `Game` | Individual games with scores and lock state |
| `Pick` | User prediction for a game — locked when game starts |
| `FixedTeamSelection` | Pre-season team selection, locked at competition start |
| `Participant` | User membership in a competition |
| `InviteLink` | Shareable tokens for joining private competitions |
| `AuditLog` | Immutable log of all admin actions |

## API Reference

Full interactive docs at `/docs` when running. Key endpoints:

**Auth:** `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/refresh` · `POST /api/auth/logout`

**Competitions:** `GET/POST /api/competitions` · `GET /api/competitions/{id}/games` · `POST /api/competitions/{id}/join`

**Picks & Leaderboards:** `GET /api/picks/{competition_id}/my-picks` · `GET /api/leaderboards/{competition_id}`

**Admin:** Score correction · user management · audit logs · competition control · join request approval

**Health:** `GET /health` (deep check — DB + Redis) · `GET /api/health/api-status` (circuit breaker states) · `POST /api/health/reset-circuit-breakers`

**WebSocket:** `WS /ws/scores` — live score stream

## Background Jobs

| Job | Interval | Description |
|---|---|---|
| Score updates | 60s | Fetch scores via failover chain, push to Redis, recalculate picks |
| Competition status | 5m | Transition upcoming → active → completed, lock selections |
| Pick locking | 60s | Lock picks for games that have started |
| Account cleanup | Daily 2 AM UTC | Hard-delete accounts after 30-day grace period |

## Testing

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# E2E (Playwright)
cd frontend && npx playwright test
```

CI runs all three suites on every push. Lighthouse CI enforces performance budgets on each PR.

## Deployment

Deployed on Render free tier — see [ADR-004](docs/adr/004-render-free-tier-deployment.md) for the full topology and free-tier adaptation decisions (cold start handling, in-process background jobs, UptimeRobot keepalive).

## Roadmap

**v2 (planned):** MLS/EPL/UCL leagues · friend/follower system · push notifications · multi-season tracking · head-to-head analytics

---

Built with FastAPI, React, and PostgreSQL

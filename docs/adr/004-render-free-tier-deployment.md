# ADR-004: Render Free Tier Deployment Strategy

**Status:** Accepted
**Date:** 2026-01-20

## Context

The app needs to be deployed publicly as a portfolio project with zero hosting cost. The stack requires a Python API server, a static frontend, PostgreSQL, and Redis.

## Decision

Deploy on Render.com free tier with the following topology:

| Component | Render Service | Notes |
|-----------|---------------|-------|
| API | Web Service (Docker) | Sleeps after 15min inactivity, 30-60s cold start |
| Frontend | Static Site | CDN-backed, never sleeps |
| PostgreSQL | Neon (external) | Free tier, 0.5GB storage |
| Redis | Upstash (external) | Free tier, 10k commands/day |

Key adaptations for free tier constraints:
- **Cold start handling** — frontend uses 60s timeouts on auth requests and shows "server starting up" messages
- **Background jobs in-process** — APScheduler runs inside the API process (no separate worker on free tier)
- **UptimeRobot keepalive** — `/ping` endpoint prevents the API from sleeping during peak hours
- **Frontend never sleeps** — Render Static Sites are CDN-backed and always available

## Consequences

**Positive:**
- Zero hosting cost for a fully functional deployed app
- CDN-backed frontend provides fast global load times
- Neon PostgreSQL offers connection pooling and serverless scaling

**Negative:**
- 30-60 second cold starts on first API request after inactivity
- Background job intervals are limited by Upstash's 10k commands/day Redis limit
- No horizontal scaling — single API instance handles all traffic
- In-process background jobs compete with request handling for CPU

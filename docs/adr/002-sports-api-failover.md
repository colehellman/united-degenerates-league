# ADR-002: Multi-Provider Sports API with Circuit Breaker

**Status:** Accepted
**Date:** 2025-12-20

## Context

The app needs live game scores and schedules from multiple sports leagues (NFL, NBA, MLB, NHL, NCAA, PGA). No single free API covers all leagues reliably, and free tiers have strict rate limits and occasional outages.

## Decision

Implement a failover chain with circuit breaker pattern:

1. **ESPN API** (primary) — free, no key required, covers most leagues
2. **The Odds API** (secondary) — requires API key, good for odds data
3. **RapidAPI** (tertiary) — aggregator with per-sport hosts
4. **Free league APIs** — MLB Stats API and NHL Stats API as sport-specific fallbacks

Each provider is wrapped in a circuit breaker (`services/circuit_breaker.py`):
- Opens after 5 consecutive failures
- Stays open for 60 seconds before retrying
- Prevents cascading failures from a downed provider

The `SportsService` orchestrator tries providers in order, skipping any with an open circuit breaker.

## Consequences

**Positive:**
- High availability — a single provider outage doesn't break the app
- Graceful degradation — scores may be delayed but the app stays functional
- Cost control — free providers are tried first

**Negative:**
- Score data format differs per provider, requiring normalization
- More complex debugging when scores are stale (which provider failed?)
- Circuit breaker state is in-memory, not shared across worker instances

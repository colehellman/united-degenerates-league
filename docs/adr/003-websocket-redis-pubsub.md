# ADR-003: WebSocket Live Scores via Redis Pub/Sub

**Status:** Accepted
**Date:** 2026-01-10

## Context

Users need to see live score updates without refreshing the page. The background job that fetches scores runs on a timer (every 60s), and scores need to be pushed to all connected browser clients.

## Decision

Use WebSocket with Redis pub/sub as the message bridge:

1. **Background job** fetches scores from sports APIs, then `PUBLISH`es to a Redis channel
2. **WebSocket manager** (`services/ws_manager.py`) subscribes to the Redis channel
3. Connected clients on `/ws/scores` receive score updates as JSON messages
4. Frontend `useLiveScores` hook manages the WebSocket connection with auto-reconnect and exponential backoff

Redis pub/sub decouples the score-fetching process from the WebSocket delivery process. This allows the background job to run in a separate worker process (via `worker.py`) in production while the API process handles WebSocket connections.

## Alternatives Considered

- **Polling** — simpler but wastes bandwidth and adds latency (up to poll interval)
- **Server-Sent Events (SSE)** — one-directional, simpler than WebSocket, but less browser support for reconnection and no binary frames
- **Direct in-process broadcast** — would work for single-process deployment but breaks when scaling to separate worker

## Consequences

**Positive:**
- Real-time updates with sub-second delivery after score fetch
- Worker and API processes can scale independently
- Redis pub/sub is lightweight and doesn't persist messages (appropriate for ephemeral score data)

**Negative:**
- Requires Redis as an infrastructure dependency
- Messages are fire-and-forget — clients that reconnect miss interim updates (mitigated by TanStack Query refetch on reconnect)
- WebSocket connections hold open TCP sockets, limiting concurrent users per process

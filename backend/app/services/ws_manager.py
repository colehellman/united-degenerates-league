"""WebSocket connection manager with Redis pub/sub bridge.

Architecture:
- Worker process publishes score updates to Redis channel "score_updates"
- API process subscribes to that channel and broadcasts to WebSocket clients
- Falls back to direct broadcast when Redis is unavailable (dev mode)
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)

SCORE_CHANNEL = "score_updates"


class ScoreManager:
    """Manages WebSocket connections and bridges Redis pub/sub to clients."""

    def __init__(self):
        self._connections: List[WebSocket] = []
        self._subscriber_task: Optional[asyncio.Task] = None

    # ── WebSocket connection management ────────────────────────────

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"WS client connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(f"WS client disconnected. Total: {len(self._connections)}")

    async def broadcast_score_update(self, games: List[Dict[str, Any]]):
        """Push score update directly to all connected WebSocket clients."""
        if not self._connections:
            return

        message = json.dumps({"type": "score_update", "games": games})
        stale: List[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)

        for ws in stale:
            self.disconnect(ws)

        if games:
            logger.debug(f"Broadcast {len(games)} score updates to {len(self._connections)} clients")

    # ── Redis pub/sub: publisher side (used by worker) ─────────────

    @staticmethod
    async def publish_score_update(games: List[Dict[str, Any]]):
        """Publish score update to Redis channel.

        Called by background_jobs.py — works from both worker and API process.
        When Redis is unavailable, falls back to direct broadcast.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.REDIS_URL)
            message = json.dumps({"type": "score_update", "games": games})
            await r.publish(SCORE_CHANNEL, message)
            await r.aclose()
            logger.debug(f"Published {len(games)} score updates to Redis channel")
        except Exception as e:
            logger.warning(f"Redis publish failed, falling back to direct broadcast: {e}")
            # Fallback: direct broadcast (works in single-process dev mode)
            await score_manager.broadcast_score_update(games)

    # ── Redis pub/sub: subscriber side (used by API process) ───────

    async def start_subscriber(self):
        """Start listening to Redis score_updates channel.

        Runs as a background task in the API process. When a message
        arrives, it's forwarded to all connected WebSocket clients.
        """
        self._subscriber_task = asyncio.create_task(self._subscribe_loop())
        logger.info("Redis score subscriber started")

    async def stop_subscriber(self):
        """Stop the Redis subscriber task."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None
            logger.info("Redis score subscriber stopped")

    async def _subscribe_loop(self):
        """Subscribe to Redis channel and forward messages to WebSocket clients.

        Reconnects automatically on connection loss with exponential backoff.
        """
        import redis.asyncio as aioredis

        retry_delay = 1
        while True:
            try:
                r = aioredis.from_url(settings.REDIS_URL)
                pubsub = r.pubsub()
                await pubsub.subscribe(SCORE_CHANNEL)
                logger.info(f"Subscribed to Redis channel: {SCORE_CHANNEL}")
                retry_delay = 1  # Reset on successful connection

                async for raw_message in pubsub.listen():
                    if raw_message["type"] != "message":
                        continue
                    try:
                        data = json.loads(raw_message["data"])
                        if data.get("type") == "score_update":
                            await self.broadcast_score_update(data["games"])
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Malformed message on score channel: {e}")

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Redis subscriber error: {e}, retrying in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)


# Singleton instance
score_manager = ScoreManager()

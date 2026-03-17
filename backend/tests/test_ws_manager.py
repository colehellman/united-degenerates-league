import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ws_manager import SCORE_CHANNEL, ScoreManager


@pytest.fixture
def manager():
    return ScoreManager()


@pytest.mark.asyncio
async def test_connect_disconnect(manager: ScoreManager):
    """Test that websockets can connect and disconnect."""
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    await manager.connect(ws1)
    await manager.connect(ws2)
    assert len(manager._connections) == 2

    manager.disconnect(ws1)
    assert len(manager._connections) == 1
    assert ws2 in manager._connections


@pytest.mark.asyncio
async def test_broadcast(manager: ScoreManager):
    """Test broadcasting a message to all connected clients."""
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect(ws1)
    await manager.connect(ws2)

    games = [{"id": "1", "score": "10-7"}]
    await manager.broadcast_score_update(games)

    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_publish_to_redis(manager: ScoreManager):
    """Test publishing a score update to Redis."""
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis

        games = [{"id": "1", "score": "14-7"}]
        await manager.publish_score_update(games)

        mock_redis.publish.assert_called_with(
            SCORE_CHANNEL, '{"type": "score_update", "games": [{"id": "1", "score": "14-7"}]}'
        )


@pytest.mark.asyncio
async def test_disconnect_nonexistent_does_not_raise(manager: ScoreManager):
    """Disconnecting a WS that was never connected should not raise."""
    ws = AsyncMock()
    manager.disconnect(ws)  # no-op


@pytest.mark.asyncio
async def test_broadcast_empty_connections(manager: ScoreManager):
    """Broadcast with no connections is a no-op."""
    await manager.broadcast_score_update([{"id": "1"}])  # should not raise


@pytest.mark.asyncio
async def test_broadcast_removes_stale_connections(manager: ScoreManager):
    """Stale WebSocket connections are pruned on send failure."""
    ws_good = AsyncMock()
    ws_bad = AsyncMock()
    ws_bad.send_text.side_effect = RuntimeError("connection closed")

    await manager.connect(ws_good)
    await manager.connect(ws_bad)
    await manager.broadcast_score_update([{"id": "g1"}])

    assert ws_bad not in manager._connections
    assert ws_good in manager._connections


@pytest.mark.asyncio
async def test_broadcast_empty_games_list(manager: ScoreManager):
    """Broadcast with empty games list sends message but skips debug log."""
    ws = AsyncMock()
    await manager.connect(ws)
    await manager.broadcast_score_update([])
    ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_stop_subscriber_without_start(manager: ScoreManager):
    """stop_subscriber is a no-op when subscriber was never started."""
    await manager.stop_subscriber()  # should not raise


@pytest.mark.asyncio
async def test_start_and_stop_subscriber(manager: ScoreManager):
    """start_subscriber creates a task; stop_subscriber cancels it cleanly."""
    with patch.object(manager, "_subscribe_loop", new_callable=AsyncMock):
        await manager.start_subscriber()
        assert manager._subscriber_task is not None
        await manager.stop_subscriber()
        assert manager._subscriber_task is None


# ── _subscribe_loop ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscribe_loop_score_update_broadcast():
    """_subscribe_loop forwards score_update messages to connected WebSocket clients."""
    manager = ScoreManager()
    ws = AsyncMock()
    await manager.connect(ws)

    async def fake_listen():
        yield {"type": "subscribe", "data": 1}  # non-message: skipped
        yield {
            "type": "message",
            "data": json.dumps({"type": "score_update", "games": [{"id": "g1"}]}),
        }
        raise asyncio.CancelledError()

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = fake_listen
    mock_r = MagicMock()
    mock_r.pubsub.return_value = mock_pubsub

    with patch("redis.asyncio.from_url", return_value=mock_r):
        with pytest.raises(asyncio.CancelledError):
            await manager._subscribe_loop()

    ws.send_text.assert_called_once()
    manager.disconnect(ws)


@pytest.mark.asyncio
async def test_subscribe_loop_malformed_json_continues():
    """_subscribe_loop logs a warning and continues on malformed JSON."""
    manager = ScoreManager()

    async def fake_listen():
        yield {"type": "message", "data": "not-valid-json"}
        raise asyncio.CancelledError()

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = fake_listen
    mock_r = MagicMock()
    mock_r.pubsub.return_value = mock_pubsub

    with patch("redis.asyncio.from_url", return_value=mock_r):
        with pytest.raises(asyncio.CancelledError):
            await manager._subscribe_loop()  # should not raise on bad JSON


@pytest.mark.asyncio
async def test_subscribe_loop_retries_after_connection_error():
    """_subscribe_loop catches connection errors and retries with backoff."""
    manager = ScoreManager()

    async def fake_listen_ok():
        # yield makes this an async generator; raising CancelledError exits the for-loop
        raise asyncio.CancelledError()
        yield  # unreachable but needed to make this an async generator

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = fake_listen_ok
    mock_r2 = MagicMock()
    mock_r2.pubsub.return_value = mock_pubsub

    # First call raises, second call succeeds then CancelledError exits the loop
    with patch("redis.asyncio.from_url", side_effect=[RuntimeError("refused"), mock_r2]):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(asyncio.CancelledError):
                await manager._subscribe_loop()


@pytest.mark.asyncio
async def test_publish_redis_failure_falls_back_to_direct_broadcast():
    """When Redis publish fails, direct broadcast is used as fallback."""
    from app.services.ws_manager import score_manager  # module-level singleton used by fallback

    ws = AsyncMock()
    await score_manager.connect(ws)
    try:
        with patch("redis.asyncio.from_url", side_effect=ConnectionError("no redis")):
            await score_manager.publish_score_update([{"id": "1"}])
        ws.send_text.assert_called_once()
    finally:
        score_manager.disconnect(ws)

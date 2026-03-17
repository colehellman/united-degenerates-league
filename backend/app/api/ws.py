"""WebSocket endpoint for live score updates.

Clients connect to /ws/scores and receive JSON messages whenever
the background job updates game scores. No auth required — score
data is public.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import score_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/scores")
async def scores_websocket(websocket: WebSocket):
    """Stream live score updates to connected clients."""
    await score_manager.connect(websocket)
    try:
        # Keep connection alive — listen for client pings/messages
        while True:
            # We don't expect meaningful messages from the client,
            # but we need to await to detect disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        score_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}", exc_info=True)
        score_manager.disconnect(websocket)

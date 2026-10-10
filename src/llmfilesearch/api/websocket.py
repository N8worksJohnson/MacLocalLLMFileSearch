"""WebSocket endpoint for real-time scan progress."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from llmfilesearch.core.indexer import get_indexer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/progress")
async def progress_ws(websocket: WebSocket) -> None:
    """Push indexing progress updates to connected clients."""
    await websocket.accept()

    try:
        while True:
            indexer = get_indexer()
            data = indexer.progress.to_dict()
            await websocket.send_json(data)

            # Poll interval: faster when actively indexing
            if data["state"] in ("scanning", "indexing"):
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket closed: %s", e)

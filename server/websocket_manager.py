"""
WebSocket Connection Manager for Arceux SOC

Thread-safe broadcast to all connected clients. Supports both async
(FastAPI endpoint) and sync (threaded crew_system.py) call sites.
"""

import asyncio
import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        async with self._lock:
            connections = list(self.active_connections)
        if not connections:
            return
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in connections],
            return_exceptions=True,
        )
        dead = {
            ws for ws, result in zip(connections, results, strict=True)
            if isinstance(result, Exception)
        }
        if dead:
            async with self._lock:
                self.active_connections = [ws for ws in self.active_connections if ws not in dead]


manager = ConnectionManager()

# ── Sync broadcast (for threaded contexts such as crew_system.py) ─────────────

_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def broadcast_sync(message: dict) -> None:
    """Fire-and-forget broadcast from a sync (thread-pool) context."""
    if _main_loop is None or not _main_loop.is_running():
        return
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), _main_loop)
    except Exception:
        logger.debug("broadcast_sync: failed to schedule broadcast", exc_info=True)

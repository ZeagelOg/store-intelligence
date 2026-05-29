"""
websocket.py — Live event broadcasting to connected dashboard clients.
"""
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


async def broadcast_event(event_data: dict):
    """Called from the ingest router to push events to all dashboard clients."""
    if manager.active:
        await manager.broadcast({"type": "event", "data": event_data})


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("ws_client_connected", total=len(manager.active))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("ws_client_disconnected", total=len(manager.active))

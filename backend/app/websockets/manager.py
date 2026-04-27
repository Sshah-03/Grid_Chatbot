import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, dict[WebSocket, str]] = defaultdict(dict)

    async def connect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[room_id][websocket] = user_id
        logger.info(
            "websocket_accepted",
            extra={"event": "websocket_accepted", "room_id": room_id, "user_id": user_id},
        )

    async def disconnect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        self.active_connections[room_id].pop(websocket, None)
        if not self.active_connections[room_id]:
            self.active_connections.pop(room_id, None)
        logger.info(
            "websocket_disconnected",
            extra={"event": "websocket_disconnected", "room_id": room_id, "user_id": user_id},
        )

    async def broadcast(self, room_id: str, payload: dict) -> None:
        dead_connections: list[WebSocket] = []
        for websocket in list(self.active_connections.get(room_id, {})):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                dead_connections.append(websocket)
        for websocket in dead_connections:
            self.active_connections[room_id].pop(websocket, None)


manager = ConnectionManager()

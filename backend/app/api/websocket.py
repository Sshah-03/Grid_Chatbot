import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.session import get_db
from app.schemas.websocket import IncomingWebSocketMessage
from app.services.auth_service import get_user_for_token
from app.services.message_service import create_message
from app.services.room_service import user_is_room_member
from app.websockets.manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/rooms/{room_id}")
async def websocket_room(
    websocket: WebSocket,
    room_id: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_for_token(db, token or "")
    if not user or not await user_is_room_member(db, room_id, user.id):
        await websocket.close(code=1008)
        logger.info(
            "websocket_rejected",
            extra={"event": "websocket_rejected", "room_id": room_id},
        )
        return

    await manager.connect(room_id, user.id, websocket)
    await manager.broadcast(
        room_id,
        {
            "type": "user_joined",
            "room_id": room_id,
            "user_id": user.id,
            "timestamp": utc_now().isoformat(),
        },
    )
    try:
        while True:
            payload = await websocket.receive_json()
            try:
                incoming = IncomingWebSocketMessage.model_validate(payload)
            except ValidationError:
                await websocket.send_json(
                    {"type": "error", "code": "INVALID_PAYLOAD", "message": "Invalid message payload."}
                )
                continue
            if incoming.type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": utc_now().isoformat()})
                continue
            if incoming.type != "message" or not incoming.body or not incoming.body.strip():
                await websocket.send_json(
                    {"type": "error", "code": "INVALID_MESSAGE", "message": "Message body is required."}
                )
                continue
            try:
                message = await create_message(
                    db, room_id, user.id, incoming.body.strip(), websocket.app.state.http_client
                )
            except Exception:
                logger.exception(
                    "message_persistence_failed",
                    extra={"event": "message_persistence_failed", "room_id": room_id, "user_id": user.id},
                )
                await websocket.send_json(
                    {"type": "error", "code": "PERSISTENCE_FAILED", "message": "Message could not be saved."}
                )
                continue
            await manager.broadcast(
                room_id,
                {
                    "type": "message_created",
                    "client_message_id": incoming.client_message_id,
                    "message": {
                        "id": message.id,
                        "room_id": message.room_id,
                        "user_id": message.user_id,
                        "body": message.body,
                        "created_at": message.created_at.isoformat(),
                        "link_previews": [
                            {
                                "url": preview.url,
                                "title": preview.title,
                                "description": preview.description,
                                "image_url": preview.image_url,
                                "site_name": preview.site_name,
                                "status": preview.status,
                                "error": preview.error,
                            }
                            for preview in message.link_previews
                        ],
                    },
                },
            )
    except WebSocketDisconnect:
        await manager.disconnect(room_id, user.id, websocket)
        await manager.broadcast(
            room_id,
            {
                "type": "user_left",
                "room_id": room_id,
                "user_id": user.id,
                "timestamp": utc_now().isoformat(),
            },
        )

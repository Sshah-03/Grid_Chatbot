import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import User
from app.schemas.messages import MessageHistoryResponse
from app.services.auth_service import get_current_user
from app.services.message_service import get_message_history, iter_message_batches
from app.services.room_service import user_is_room_member

router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])


@router.get("", response_model=MessageHistoryResponse)
async def message_history(
    room_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_is_room_member(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="Not a room member")
    messages = await get_message_history(db, room_id, limit, before)
    next_cursor = messages[-1].created_at.isoformat() if len(messages) == limit else None
    return MessageHistoryResponse(items=messages, next_cursor=next_cursor)


@router.get("/export")
async def export_messages(
    room_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_is_room_member(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="Not a room member")

    async def stream():
        async for batch in iter_message_batches(db, room_id):
            for message in batch:
                yield json.dumps(
                    {
                        "id": message.id,
                        "room_id": message.room_id,
                        "user_id": message.user_id,
                        "body": message.body,
                        "created_at": message.created_at.isoformat(),
                    }
                ) + "\n"

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="room-{room_id}-messages.ndjson"'},
    )

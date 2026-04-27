from datetime import datetime

from pydantic import BaseModel


class LinkPreviewResponse(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    site_name: str | None = None
    status: str
    error: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    room_id: str
    user_id: str
    body: str
    created_at: datetime
    link_previews: list[LinkPreviewResponse] = []

    model_config = {"from_attributes": True}


class MessageHistoryResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None = None

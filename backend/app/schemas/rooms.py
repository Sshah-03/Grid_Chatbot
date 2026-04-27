from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.auth import UserResponse


class RoomCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    type: str = Field(pattern="^(group|direct)$")
    visibility: str = Field(default="private", pattern="^(public|private)$")
    member_ids: list[str] = Field(default_factory=list)


class RoomResponse(BaseModel):
    id: str
    name: str | None
    type: str
    visibility: str
    invite_code: str | None = None
    created_by_user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomListItem(BaseModel):
    id: str
    name: str | None
    type: str
    visibility: str
    created_at: datetime
    last_message_at: datetime | None = None
    unread_count: int = 0


class RoomMemberAddRequest(BaseModel):
    user_id: str = Field(min_length=1)


class RoomInviteResponse(BaseModel):
    invite_code: str
    invite_url: str


class RoomListResponse(BaseModel):
    items: list[RoomListItem]
    page: int
    page_size: int
    total: int


class RoomDetailResponse(RoomResponse):
    members: list[UserResponse]

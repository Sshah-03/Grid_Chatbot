from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Room, User
from app.schemas.rooms import (
    RoomInviteResponse,
    RoomMemberAddRequest,
    RoomCreateRequest,
    RoomDetailResponse,
    RoomListItem,
    RoomListResponse,
    RoomResponse,
)
from app.services.auth_service import get_current_user
from app.services.room_service import (
    add_room_member,
    create_room,
    get_room_by_invite_code,
    get_room_with_members,
    last_message_at,
    list_public_groups,
    list_user_rooms,
    mark_room_read,
    refresh_room_invite_code,
    unread_count,
    user_is_room_member,
    user_is_room_owner,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room_endpoint(
    payload: RoomCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_room(
            db, payload.name, payload.type, payload.visibility, user.id, payload.member_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=RoomListResponse)
async def list_rooms_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    type: str | None = Query(default=None, pattern="^(group|direct)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rooms, total = await list_user_rooms(db, user.id, page, page_size, type)
    items = [
        RoomListItem(
            id=room.id,
            name=room.name,
            type=room.type,
            visibility=room.visibility,
            created_at=room.created_at,
            last_message_at=await last_message_at(db, room.id),
            unread_count=await unread_count(db, room.id, user.id),
        )
        for room in rooms
    ]
    return RoomListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/public", response_model=RoomListResponse)
async def list_public_groups_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rooms, total = await list_public_groups(db, user.id, page, page_size)
    items = [
        RoomListItem(
            id=room.id,
            name=room.name,
            type=room.type,
            visibility=room.visibility,
            created_at=room.created_at,
            last_message_at=await last_message_at(db, room.id),
            unread_count=0,
        )
        for room in rooms
    ]
    return RoomListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room_endpoint(
    room_id: str,
    mark_read: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_is_room_member(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="Not a room member")
    room = await get_room_with_members(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if mark_read:
        await mark_room_read(db, room_id, user.id)
    return RoomDetailResponse(
        id=room.id,
        name=room.name,
        type=room.type,
        visibility=room.visibility,
        invite_code=room.invite_code if await user_is_room_owner(db, room_id, user.id) else None,
        created_by_user_id=room.created_by_user_id,
        created_at=room.created_at,
        members=[membership.user for membership in room.memberships],
    )


@router.post("/{room_id}/join", response_model=RoomResponse)
async def join_public_group(
    room_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    room = await db.get(Room, room_id)
    if not room or room.type != "group":
        raise HTTPException(status_code=404, detail="Room not found")
    if room.visibility != "public":
        raise HTTPException(status_code=403, detail="Private rooms require an invite")
    await add_room_member(db, room.id, user.id)
    await db.refresh(room)
    return room


@router.post("/join/{invite_code}", response_model=RoomResponse)
async def join_group_by_invite(
    invite_code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    room = await get_room_by_invite_code(db, invite_code)
    if not room:
        raise HTTPException(status_code=404, detail="Invite not found")
    await add_room_member(db, room.id, user.id)
    return room


@router.post("/{room_id}/members", status_code=204)
async def add_member_endpoint(
    room_id: str,
    payload: RoomMemberAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_is_room_owner(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="Only the group owner can add members")
    room = await db.get(Room, room_id)
    target = await db.get(User, payload.user_id)
    if not room or room.type != "group":
        raise HTTPException(status_code=404, detail="Room not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await add_room_member(db, room_id, payload.user_id)


@router.post("/{room_id}/invite", response_model=RoomInviteResponse)
async def create_invite_endpoint(
    room_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await user_is_room_owner(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="Only the group owner can create invite links")
    room = await db.get(Room, room_id)
    if not room or room.type != "group":
        raise HTTPException(status_code=404, detail="Room not found")
    invite_code = room.invite_code or await refresh_room_invite_code(db, room)
    return RoomInviteResponse(invite_code=invite_code, invite_url=f"/join/{invite_code}")

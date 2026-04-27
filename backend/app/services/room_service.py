import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Message, Room, RoomMembership, User


async def user_is_room_member(db: AsyncSession, room_id: str, user_id: str) -> bool:
    membership = await db.scalar(
        select(RoomMembership).where(
            RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
        )
    )
    return membership is not None


async def mark_room_read(db: AsyncSession, room_id: str, user_id: str) -> None:
    membership = await db.scalar(
        select(RoomMembership).where(
            RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
        )
    )
    if membership:
        from app.core.time import utc_now

        membership.last_read_at = utc_now()
        await db.commit()


async def unread_count(db: AsyncSession, room_id: str, user_id: str) -> int:
    membership = await db.scalar(
        select(RoomMembership).where(
            RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
        )
    )
    if not membership:
        return 0
    query = select(func.count()).select_from(Message).where(
        Message.room_id == room_id,
        Message.user_id != user_id,
    )
    if membership.last_read_at:
        query = query.where(Message.created_at > membership.last_read_at)
    total = await db.scalar(query)
    return int(total or 0)


async def user_is_room_owner(db: AsyncSession, room_id: str, user_id: str) -> bool:
    membership = await db.scalar(
        select(RoomMembership).where(
            RoomMembership.room_id == room_id,
            RoomMembership.user_id == user_id,
            RoomMembership.role == "owner",
        )
    )
    return membership is not None


async def find_direct_room(
    db: AsyncSession, current_user_id: str, other_user_id: str
) -> Room | None:
    rooms = await db.scalars(
        select(Room)
        .join(RoomMembership)
        .where(Room.type == "direct", RoomMembership.user_id.in_([current_user_id, other_user_id]))
        .options(selectinload(Room.memberships))
    )
    for room in rooms.unique():
        member_ids = {membership.user_id for membership in room.memberships}
        if member_ids == {current_user_id, other_user_id}:
            return room
    return None


async def create_room(
    db: AsyncSession,
    name: str | None,
    room_type: str,
    visibility: str,
    creator_id: str,
    member_ids: list[str],
) -> Room:
    all_member_ids = list(dict.fromkeys([creator_id, *member_ids]))
    if room_type == "direct" and len(all_member_ids) != 2:
        raise ValueError("Direct rooms require exactly two members")
    if room_type == "direct" and visibility != "private":
        raise ValueError("Direct rooms must be private")
    if room_type == "direct":
        existing = await find_direct_room(db, all_member_ids[0], all_member_ids[1])
        if existing:
            return existing
    room = Room(
        name=name if room_type == "group" else None,
        type=room_type,
        visibility=visibility if room_type == "group" else "private",
        invite_code=str(uuid.uuid4()) if room_type == "group" and visibility == "private" else None,
        created_by_user_id=creator_id,
    )
    room.memberships = [
        RoomMembership(user_id=user_id, role="owner" if user_id == creator_id else "member")
        for user_id in all_member_ids
    ]
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def list_user_rooms(
    db: AsyncSession, user_id: str, page: int, page_size: int, room_type: str | None
) -> tuple[list[Room], int]:
    base: Select = select(Room).join(RoomMembership).where(RoomMembership.user_id == user_id)
    if room_type:
        base = base.where(Room.type == room_type)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rooms = await db.scalars(
        base.order_by(Room.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rooms), int(total or 0)


async def list_public_groups(
    db: AsyncSession, user_id: str, page: int, page_size: int
) -> tuple[list[Room], int]:
    member_room_ids = select(RoomMembership.room_id).where(RoomMembership.user_id == user_id)
    base = (
        select(Room)
        .where(Room.type == "group", Room.visibility == "public")
        .where(Room.id.not_in(member_room_ids))
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rooms = await db.scalars(
        base.order_by(Room.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rooms), int(total or 0)


async def add_room_member(
    db: AsyncSession, room_id: str, user_id: str, role: str = "member"
) -> RoomMembership:
    existing = await db.scalar(
        select(RoomMembership).where(
            RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
        )
    )
    if existing:
        return existing
    membership = RoomMembership(room_id=room_id, user_id=user_id, role=role)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def get_room_by_invite_code(db: AsyncSession, invite_code: str) -> Room | None:
    return await db.scalar(select(Room).where(Room.invite_code == invite_code, Room.type == "group"))


async def refresh_room_invite_code(db: AsyncSession, room: Room) -> str:
    room.invite_code = str(uuid.uuid4())
    await db.commit()
    await db.refresh(room)
    return room.invite_code


async def get_room_with_members(db: AsyncSession, room_id: str) -> Room | None:
    return await db.scalar(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.memberships).selectinload(RoomMembership.user))
    )


async def last_message_at(db: AsyncSession, room_id: str):
    return await db.scalar(
        select(func.max(Message.created_at)).where(Message.room_id == room_id)
    )

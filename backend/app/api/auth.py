from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse, UserUpdateRequest
from app.services.auth_service import get_current_user, login_user, logout_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_user(
        db, payload.email, payload.password, payload.username, payload.full_name
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_session = await login_user(db, payload.email, payload.password)
    return LoginResponse(
        token=auth_session.token,
        expires_at=auth_session.expires_at,
        user=auth_session.user,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if authorization and authorization.lower().startswith("bearer "):
        await logout_token(db, authorization.split(" ", 1)[1])
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    username = payload.username.strip().lower()
    existing = await db.scalar(select(User).where(User.username == username, User.id != user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Username already registered")
    user.username = username
    user.full_name = payload.full_name.strip() if payload.full_name else None
    user.display_name = username
    user.profile_bio = payload.profile_bio.strip() if payload.profile_bio else None
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/search", response_model=list[UserResponse])
async def search_users(
    q: str = Query(min_length=1, max_length=80),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q.strip().lower()}%"
    users = await db.scalars(
        select(User)
        .where(User.id != user.id)
        .where(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
        .order_by(User.username.asc(), User.email.asc())
        .limit(10)
    )
    return list(users)

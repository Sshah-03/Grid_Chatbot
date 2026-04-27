import logging
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.core.time import utc_now
from app.db.session import get_db
from app.models import AuthSession, User

logger = logging.getLogger(__name__)


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    username: str,
    full_name: str | None = None,
) -> User:
    normalized_email = email.lower()
    normalized_username = username.strip().lower()
    logger.info("register_attempt", extra={"event": "register_attempt", "email": normalized_email})
    existing = await db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        logger.warning(
            "register_rejected",
            extra={"event": "register_rejected", "email": normalized_email, "reason": "email_exists"},
        )
        raise HTTPException(status_code=409, detail="Email already registered")
    existing_username = await db.scalar(select(User).where(User.username == normalized_username))
    if existing_username:
        logger.warning(
            "register_rejected",
            extra={
                "event": "register_rejected",
                "email": normalized_email,
                "reason": "username_exists",
            },
        )
        raise HTTPException(status_code=409, detail="Username already registered")
    user = User(
        email=normalized_email,
        username=normalized_username,
        full_name=full_name.strip() if full_name else None,
        display_name=normalized_username,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(
        "register_success",
        extra={"event": "register_success", "email": normalized_email, "user_id": user.id},
    )
    return user


async def login_user(db: AsyncSession, email: str, password: str) -> AuthSession:
    identifier = email.strip().lower()
    logger.info("login_attempt", extra={"event": "login_attempt", "identifier": identifier})
    user = await db.scalar(
        select(User).where((User.email == identifier) | (User.username == identifier))
    )
    if not user or not verify_password(password, user.password_hash):
        logger.warning(
            "login_failed",
            extra={"event": "login_failed", "identifier": identifier, "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    settings = get_settings()
    session = AuthSession(
        user_id=user.id,
        expires_at=utc_now() + timedelta(seconds=settings.token_ttl_seconds),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    session.user = user
    logger.info(
        "login_success",
        extra={
            "event": "login_success",
            "email": user.email,
            "user_id": user.id,
            "session_id": session.id,
        },
    )
    return session


async def get_user_for_token(db: AsyncSession, token: str) -> User | None:
    auth_session = await db.scalar(
        select(AuthSession).where(AuthSession.token == token)
    )
    expires_at = auth_session.expires_at if auth_session else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        not auth_session
        or auth_session.revoked_at is not None
        or expires_at < utc_now()
    ):
        return None
    return await db.get(User, auth_session.user_id)


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    user = await get_user_for_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


async def logout_token(db: AsyncSession, token: str) -> None:
    auth_session = await db.scalar(select(AuthSession).where(AuthSession.token == token))
    if auth_session:
        auth_session.revoked_at = utc_now()
        await db.commit()
        logger.info(
            "logout_success",
            extra={
                "event": "logout_success",
                "user_id": auth_session.user_id,
                "session_id": auth_session.id,
            },
        )

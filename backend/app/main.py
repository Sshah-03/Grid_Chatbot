from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth, health, integrations, messages, rooms, websocket
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.models import Base


async def ensure_development_schema(conn) -> None:
    await conn.run_sync(Base.metadata.create_all)

    async def column_exists(table_name: str, column_name: str) -> bool:
        return bool(
            await conn.scalar(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() "
                    "AND table_name = :table_name "
                    "AND column_name = :column_name"
                ),
                {"table_name": table_name, "column_name": column_name},
            )
        )

    if not await column_exists("users", "display_name"):
        await conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(80) NULL"))
    if not await column_exists("users", "username"):
        await conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80) NULL"))
        await conn.execute(text("CREATE INDEX ix_users_username ON users (username)"))
    if not await column_exists("users", "full_name"):
        await conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NULL"))
    if not await column_exists("users", "profile_bio"):
        await conn.execute(text("ALTER TABLE users ADD COLUMN profile_bio VARCHAR(500) NULL"))
    await conn.execute(
        text(
            "UPDATE users SET display_name = SUBSTRING_INDEX(email, '@', 1) "
            "WHERE display_name IS NULL OR display_name = ''"
        )
    )
    await conn.execute(
        text(
            "UPDATE users SET username = LOWER(display_name) "
            "WHERE username IS NULL OR username = ''"
        )
    )
    if not await column_exists("rooms", "visibility"):
        await conn.execute(
            text("ALTER TABLE rooms ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private'")
        )
    if not await column_exists("rooms", "invite_code"):
        await conn.execute(text("ALTER TABLE rooms ADD COLUMN invite_code VARCHAR(36) NULL"))
    if not await column_exists("room_memberships", "last_read_at"):
        await conn.execute(text("ALTER TABLE room_memberships ADD COLUMN last_read_at DATETIME NULL"))
    await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=settings.httpx_timeout_connect,
        read=settings.httpx_timeout_read,
        write=5.0,
        pool=5.0,
    )
    app.state.http_client = httpx.AsyncClient(timeout=timeout)
    if settings.environment == "development":
        async with engine.begin() as conn:
            await ensure_development_schema(conn)
    yield
    await app.state.http_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_file_path)
    app = FastAPI(title="Grid Chatbot Realtime Chat API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(rooms.router)
    app.include_router(messages.router)
    app.include_router(integrations.router)
    app.include_router(websocket.router)
    return app


app = create_app()

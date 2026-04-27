from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
    "pool_pre_ping": True,
}

if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine = create_async_engine(settings.database_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

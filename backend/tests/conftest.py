from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import create_app
from app.models import Base


@pytest.fixture()
async def session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture()
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture()
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def register_user(
    client: httpx.AsyncClient,
    email: str,
    username: str,
    password: str = "StrongPassword123",
    full_name: str | None = None,
) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login_user(
    client: httpx.AsyncClient,
    identifier: str,
    password: str = "StrongPassword123",
) -> tuple[str, dict]:
    response = await client.post(
        "/auth/login",
        json={"email": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload["token"], payload["user"]

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import engine  # noqa: E402


async def main() -> None:
    settings = get_settings()
    print(f"Checking DATABASE_URL: {settings.database_url}")
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT DATABASE(), CURRENT_USER()"))
            database, current_user = result.one()
            print(f"Connected to database={database}, user={current_user}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

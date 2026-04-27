import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import engine  # noqa: E402
from app.models import Base  # noqa: E402


TABLES = (
    "users",
    "rooms",
    "room_memberships",
    "messages",
    "auth_sessions",
    "external_fetch_runs",
)


def read_rows(sqlite_path: Path, table: str) -> list[dict]:
    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def upsert_statement(table: str, columns: list[str]) -> str:
    column_list = ", ".join(f"`{column}`" for column in columns)
    value_list = ", ".join(f":{column}" for column in columns)
    updates = ", ".join(
        f"`{column}` = VALUES(`{column}`)" for column in columns if column != "id"
    )
    return (
        f"INSERT INTO `{table}` ({column_list}) VALUES ({value_list}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )


async def migrate(sqlite_path: Path) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for table in TABLES:
            rows = read_rows(sqlite_path, table)
            if not rows:
                print(f"{table}: 0 rows")
                continue
            statement = text(upsert_statement(table, list(rows[0].keys())))
            await connection.execute(statement, rows)
            print(f"{table}: migrated {len(rows)} rows")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local SQLite data into MySQL.")
    parser.add_argument(
        "--sqlite-path",
        default=str(BACKEND_DIR / "chat_app_dev.db"),
        help="Path to the old SQLite database file.",
    )
    args = parser.parse_args()
    asyncio.run(migrate(Path(args.sqlite_path)))


if __name__ == "__main__":
    main()

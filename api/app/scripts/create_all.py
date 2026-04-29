"""Provision all tables from SQLAlchemy metadata. Idempotent. Use for dev/Railway bootstrap."""
import asyncio

from app.db import engine
from app.models import Base


async def run() -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.run_sync(Base.metadata.create_all)
    print("Schema provisioned.")


if __name__ == "__main__":
    asyncio.run(run())

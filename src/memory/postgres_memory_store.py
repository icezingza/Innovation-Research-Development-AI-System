import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.memory.schema import Base


class PostgresMemoryStore:
    """Structured persistence layer backed by PostgreSQL."""

    def __init__(self, url: str | None = None) -> None:
        resolved_url = url or os.getenv(
            "POSTGRES_URL",
            "postgresql+asyncpg://cognitive:cognitive@localhost/cognition",
        )
        self.engine: AsyncEngine = create_async_engine(resolved_url, echo=False)

    async def init_schema(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def healthcheck(self) -> bool:
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()

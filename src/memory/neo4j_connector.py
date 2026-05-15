import os
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase


class Neo4jKnowledgeConnector:
    """Knowledge graph connector backed by Neo4j."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        resolved_uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        resolved_user = user or os.getenv("NEO4J_USER", "neo4j")
        resolved_password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            resolved_uri, auth=(resolved_user, resolved_password)
        )

    async def healthcheck(self) -> bool:
        async with self.driver.session() as session:
            await session.run("RETURN 1")
        return True

    async def run_query(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(cypher, parameters or {})
            records = await result.data()
        return records

    async def close(self) -> None:
        await self.driver.close()

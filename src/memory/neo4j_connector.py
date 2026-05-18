import os
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    RetryHandler,
)


class Neo4jKnowledgeConnector:
    """Knowledge graph connector backed by Neo4j with Circuit Breaker & Retry resilience."""

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

        # Instantiate resilience mechanisms tailored for Neo4j Graph queries
        self.cb = CircuitBreaker(
            name="neo4j_connector",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=15.0,
                success_threshold=2,
                timeout=10.0,
            ),
        )
        self.retry = RetryHandler(
            config=RetryConfig(
                max_attempts=3,
                initial_delay=0.5,
                max_delay=5.0,
                jitter=True,
            )
        )

    async def healthcheck(self) -> bool:
        """Verify Neo4j connectivity wrapped with Circuit Breaker and Retry protections."""

        async def _check() -> bool:
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            return True

        # Wrap with outer Circuit Breaker and inner Retry Handler
        resilient_check = self.cb(self.retry(exceptions=(Exception,))(_check))
        return await resilient_check()

    async def run_query(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run Cypher query with automatic retry backoff and fast-fail circuit breaker."""

        async def _execute() -> list[dict[str, Any]]:
            async with self.driver.session() as session:
                result = await session.run(cypher, parameters or {})
                records = await result.data()
            return records

        # Wrap with outer Circuit Breaker and inner Retry Handler
        resilient_execute = self.cb(self.retry(exceptions=(Exception,))(_execute))
        return await resilient_execute()

    async def close(self) -> None:
        """Gracefully release Neo4j driver connection resources."""
        await self.driver.close()

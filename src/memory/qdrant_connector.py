from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.memory.interfaces import VectorMemory
from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    RetryHandler,
)


class QdrantMemoryConnector(VectorMemory):
    """Semantic vector memory backed by Qdrant with Circuit Breaker & Retry resilience."""

    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self.client = AsyncQdrantClient(host=host, port=port)

        # Instantiate resilience mechanisms tailored for Qdrant Vector Search
        self.cb = CircuitBreaker(
            name="qdrant_connector",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=15.0,
                success_threshold=2,
                timeout=8.0,
            ),
        )
        self.retry = RetryHandler(
            config=RetryConfig(
                max_attempts=3,
                initial_delay=0.3,
                max_delay=4.0,
                jitter=True,
            )
        )

    async def healthcheck(self) -> dict[str, Any]:
        """Check Qdrant server health wrapped with circuit protection."""

        async def _check() -> dict[str, Any]:
            collections = await self.client.get_collections()
            return {"collections": len(collections.collections)}

        resilient_check = self.cb(self.retry(exceptions=(Exception,))(_check))
        return await resilient_check()

    async def ensure_collection(
        self, name: str, vector_size: int, distance: Distance = Distance.COSINE
    ) -> None:
        """Create standard collection with safe resilience policies."""

        async def _ensure() -> None:
            existing = await self.client.get_collections()
            names = {c.name for c in existing.collections}
            if name not in names:
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=vector_size, distance=distance),
                )

        resilient_ensure = self.cb(self.retry(exceptions=(Exception,))(_ensure))
        await resilient_ensure()

    async def store(self, embedding: list[float], metadata: dict[str, Any]) -> bool:
        """Store semantic vectors into Qdrant."""
        return await self.store_embedding(embedding, metadata)

    async def store_embedding(
        self, embedding: list[float], metadata: dict[str, Any]
    ) -> bool:
        """Upsert point embeddings into Qdrant database wrapped with resilience logic."""

        async def _upsert() -> bool:
            collection = metadata.get("collection", "default")
            point_id = metadata.get("id", 0)
            await self.client.upsert(
                collection_name=collection,
                points=[PointStruct(id=point_id, vector=embedding, payload=metadata)],
            )
            return True

        resilient_upsert = self.cb(self.retry(exceptions=(Exception,))(_upsert))
        return await resilient_upsert()

    async def search(self, query_embedding: list[float]) -> list[dict[str, Any]]:
        """Search similar matches within default collection."""
        return await self.search_similar(query_embedding)

    async def search_similar(
        self,
        query_embedding: list[float],
        collection: str = "default",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Perform semantic nearest neighbor searches wrapped with resilience policies."""

        async def _search() -> list[dict[str, Any]]:
            # qdrant-client ≥ 1.7: client.search() deprecated/removed → use query_points()
            # Returns a QueryResponse containing ScoredPoints (which have .payload) or mapped models.
            response = await self.client.query_points(
                collection_name=collection,
                query=query_embedding,
                limit=limit,
                with_payload=True,
            )
            results = response.points if hasattr(response, "points") else response
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": getattr(r, "payload", getattr(r, "metadata", {})),
                }
                for r in results
            ]

        resilient_search = self.cb(self.retry(exceptions=(Exception,))(_search))
        return await resilient_search()

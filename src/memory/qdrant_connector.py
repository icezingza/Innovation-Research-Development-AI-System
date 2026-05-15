from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.memory.interfaces import VectorMemory


class QdrantMemoryConnector(VectorMemory):
    """Semantic vector memory backed by Qdrant."""

    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self.client = AsyncQdrantClient(host=host, port=port)

    async def healthcheck(self) -> dict[str, Any]:
        collections = await self.client.get_collections()
        return {"collections": len(collections.collections)}

    async def ensure_collection(
        self, name: str, vector_size: int, distance: Distance = Distance.COSINE
    ) -> None:
        existing = await self.client.get_collections()
        names = {c.name for c in existing.collections}
        if name not in names:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )

    async def store(self, embedding: list[float], metadata: dict[str, Any]) -> bool:
        return await self.store_embedding(embedding, metadata)

    async def store_embedding(
        self, embedding: list[float], metadata: dict[str, Any]
    ) -> bool:
        collection = metadata.get("collection", "default")
        point_id = metadata.get("id", 0)
        await self.client.upsert(
            collection_name=collection,
            points=[PointStruct(id=point_id, vector=embedding, payload=metadata)],
        )
        return True

    async def search(self, query_embedding: list[float]) -> list[dict[str, Any]]:
        return await self.search_similar(query_embedding)

    async def search_similar(
        self,
        query_embedding: list[float],
        collection: str = "default",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        results = await self.client.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=limit,
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]

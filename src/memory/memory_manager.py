from typing import Any


class MemoryManager:
    """Unified cognitive memory manager coordinating all persistence layers."""

    def __init__(
        self,
        vector_store: Any,
        graph_store: Any,
        runtime_store: Any,
        persistence_store: Any,
    ) -> None:
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.runtime_store = runtime_store
        self.persistence_store = persistence_store

    async def healthcheck(self) -> dict[str, Any]:
        return {
            "vector": await self.vector_store.healthcheck(),
            "graph": await self.graph_store.healthcheck(),
            "runtime": await self.runtime_store.healthcheck(),
            "persistence": await self.persistence_store.healthcheck(),
        }

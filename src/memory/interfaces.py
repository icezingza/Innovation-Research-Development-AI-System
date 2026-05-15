from abc import ABC, abstractmethod


class VectorMemory(ABC):
    """Abstract vector memory interface."""

    @abstractmethod
    async def store(self, embedding, metadata):
        pass

    @abstractmethod
    async def search(self, query_embedding):
        pass

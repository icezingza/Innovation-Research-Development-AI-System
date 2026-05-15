class QdrantMemoryConnector:
    """Semantic vector memory connector."""

    async def store_embedding(self, embedding, metadata):
        return True

    async def search_similar(self, embedding):
        return []

class MemoryManager:
    """Unified cognitive memory manager."""

    def __init__(
        self,
        vector_store,
        graph_store,
        runtime_store,
        history_store
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.runtime_store = runtime_store
        self.history_store = history_store

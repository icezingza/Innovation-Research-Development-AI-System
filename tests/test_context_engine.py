"""Tests for ContextEngine — mocked Qdrant + embedding provider."""

import pytest

from src.inference.embedding_provider import DisabledEmbeddingProvider
from src.memory.context_engine import ContextEngine, ContextPacket


class _MockEmbeddingProvider:
    enabled = True
    dimensions = 4

    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]


class _MockVectorStore:
    def __init__(self, results: list[dict]) -> None:
        self._results = results

    async def search_similar(self, query_embedding, collection, limit):
        return self._results

    async def store_embedding(self, embedding, metadata):
        return True


@pytest.mark.asyncio
async def test_context_engine_returns_similar_hypotheses():
    store = _MockVectorStore(
        results=[
            {"score": 0.9, "payload": {"statement": "X causes Y", "confidence": 0.7}},
            {"score": 0.8, "payload": {"statement": "A leads to B", "confidence": 0.6}},
        ]
    )
    engine = ContextEngine(
        vector_store=store, embedding_provider=_MockEmbeddingProvider()
    )
    packet = await engine.build("Does X cause Y?")
    assert isinstance(packet, ContextPacket)
    assert len(packet.similar_hypotheses) == 2
    assert packet.continuity_score > 0.0


@pytest.mark.asyncio
async def test_context_engine_disabled_provider_returns_empty():
    store = _MockVectorStore(results=[])
    engine = ContextEngine(
        vector_store=store, embedding_provider=DisabledEmbeddingProvider()
    )
    packet = await engine.build("Does X cause Y?")
    assert packet.similar_hypotheses == []
    assert packet.continuity_score == 0.0


@pytest.mark.asyncio
async def test_context_engine_handles_vector_store_failure():
    class _FailingStore:
        async def search_similar(self, **kwargs):
            raise ConnectionError("Qdrant unreachable")

    engine = ContextEngine(
        vector_store=_FailingStore(), embedding_provider=_MockEmbeddingProvider()
    )
    packet = await engine.build("Some question")
    assert packet.similar_hypotheses == []
    assert packet.continuity_score == 0.0


@pytest.mark.asyncio
async def test_context_engine_store_hypothesis():
    stored = []

    class _TrackingStore:
        async def search_similar(self, **kwargs):
            return []

        async def store_embedding(self, embedding, metadata):
            stored.append(metadata)
            return True

    engine = ContextEngine(
        vector_store=_TrackingStore(), embedding_provider=_MockEmbeddingProvider()
    )
    await engine.store_hypothesis(
        hypothesis={"statement": "X causes Y", "confidence": 0.7, "generation": 1},
        question="Does X cause Y?",
        task_id="task-123",
    )
    assert len(stored) == 1
    assert stored[0]["statement"] == "X causes Y"
    assert stored[0]["task_id"] == "task-123"

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.reasoning.meta_learning import MetaLearningPipeline


@pytest.mark.asyncio
async def test_ingest_calls_store_speculative_knowledge():
    kg = MagicMock()
    kg.store_speculative_knowledge = AsyncMock()
    pipeline = MetaLearningPipeline(knowledge_graph=kg)

    await pipeline.ingest({"source": "critique_agent", "content": "Low coherence", "confidence": 0.7})

    kg.store_speculative_knowledge.assert_called_once()
    call_kwargs = kg.store_speculative_knowledge.call_args.kwargs
    assert call_kwargs["source"] == "critique_agent"
    assert call_kwargs["content"] == "Low coherence"
    assert call_kwargs["confidence"] == 0.7
    assert "node_id" in call_kwargs


@pytest.mark.asyncio
async def test_ingest_without_knowledge_graph_is_noop():
    pipeline = MetaLearningPipeline(knowledge_graph=None)
    # Should complete without raising
    await pipeline.ingest({"source": "test", "content": "feedback", "confidence": 0.5})


@pytest.mark.asyncio
async def test_ingest_uses_default_confidence():
    kg = MagicMock()
    kg.store_speculative_knowledge = AsyncMock()
    pipeline = MetaLearningPipeline(knowledge_graph=kg)

    await pipeline.ingest({"source": "agent", "content": "Some feedback"})

    call_kwargs = kg.store_speculative_knowledge.call_args.kwargs
    assert call_kwargs["confidence"] == 0.5


@pytest.mark.asyncio
async def test_ingest_tolerates_store_failure():
    kg = MagicMock()
    kg.store_speculative_knowledge = AsyncMock(side_effect=RuntimeError("Neo4j down"))
    pipeline = MetaLearningPipeline(knowledge_graph=kg)

    # Should log warning and not raise
    await pipeline.ingest({"source": "agent", "content": "feedback", "confidence": 0.6})

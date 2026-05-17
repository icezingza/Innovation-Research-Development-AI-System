"""Unit tests for KnowledgeGraph — queries are validated against a mock connector."""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.memory.knowledge_graph import KnowledgeGraph


def _make_graph() -> tuple[KnowledgeGraph, AsyncMock]:
    connector = AsyncMock()
    connector.run_query = AsyncMock(return_value=[])
    return KnowledgeGraph(connector=connector), connector


@pytest.mark.asyncio
async def test_store_hypothesis_calls_merge_query():
    graph, connector = _make_graph()
    hyp_id = str(uuid.uuid4())
    await graph.store_hypothesis(
        hypothesis_id=hyp_id,
        statement="Sleep consolidates memory",
        confidence=0.8,
        generation=1,
        task_id="task-123",
    )
    connector.run_query.assert_called_once()
    cypher, params = connector.run_query.call_args[0]
    assert "MERGE" in cypher
    assert "Hypothesis" in cypher
    assert params["id"] == hyp_id
    assert params["confidence"] == 0.8


@pytest.mark.asyncio
async def test_link_evolution_calls_match_merge():
    graph, connector = _make_graph()
    parent_id = str(uuid.uuid4())
    child_id = str(uuid.uuid4())
    await graph.link_evolution(parent_id=parent_id, child_id=child_id)
    connector.run_query.assert_called_once()
    cypher, params = connector.run_query.call_args[0]
    assert "EVOLVED_TO" in cypher
    assert params["parent_id"] == parent_id
    assert params["child_id"] == child_id


@pytest.mark.asyncio
async def test_store_contradiction_wires_relationship():
    graph, connector = _make_graph()
    await graph.store_contradiction(
        stmt_a="X causes Y",
        stmt_b="X does not cause Y",
        contradiction_type="direct_negation",
        severity=0.9,
    )
    connector.run_query.assert_called_once()
    cypher, params = connector.run_query.call_args[0]
    assert "CONTRADICTS" in cypher
    assert params["severity"] == 0.9


@pytest.mark.asyncio
async def test_get_hypothesis_lineage_returns_connector_result():
    connector = AsyncMock()
    connector.run_query = AsyncMock(
        return_value=[
            {"id": "h1", "statement": "root", "confidence": 0.5, "generation": 0},
            {"id": "h2", "statement": "child", "confidence": 0.7, "generation": 1},
        ]
    )
    graph = KnowledgeGraph(connector=connector)
    lineage = await graph.get_hypothesis_lineage("h2")
    assert len(lineage) == 2
    assert lineage[0]["generation"] == 0


@pytest.mark.asyncio
async def test_find_related_passes_depth():
    graph, connector = _make_graph()
    hyp_id = str(uuid.uuid4())
    await graph.find_related(hypothesis_id=hyp_id, max_depth=3)
    _, params = connector.run_query.call_args[0]
    assert params["depth"] == 3

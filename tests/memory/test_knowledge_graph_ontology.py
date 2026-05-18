"""Tests for KnowledgeGraph cross-domain ontology methods."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.memory.knowledge_graph import KnowledgeGraph


@pytest.mark.asyncio
async def test_store_domain_concept():
    mock_connector = MagicMock()
    mock_connector.run_query = AsyncMock(return_value=None)
    kg = KnowledgeGraph(connector=mock_connector)

    await kg.store_domain_concept(
        domain="finance",
        concept="Basel III Capital Adequacy",
        properties={"source": "BIS", "year": 2010},
    )

    mock_connector.run_query.assert_called_once()
    query, params = mock_connector.run_query.call_args.args
    assert "Domain" in query
    assert "Concept" in query
    assert params["domain"] == "finance"
    assert params["concept"] == "Basel III Capital Adequacy"


@pytest.mark.asyncio
async def test_link_domains():
    mock_connector = MagicMock()
    mock_connector.run_query = AsyncMock(return_value=None)
    kg = KnowledgeGraph(connector=mock_connector)

    await kg.link_domains(source_domain="finance", target_domain="legal", relation="REGULATED_BY")

    mock_connector.run_query.assert_called_once()
    query, _ = mock_connector.run_query.call_args.args
    assert "REGULATED_BY" in query


@pytest.mark.asyncio
async def test_link_domains_creates_domain_nodes():
    mock_connector = MagicMock()
    mock_connector.run_query = AsyncMock(return_value=None)
    kg = KnowledgeGraph(connector=mock_connector)

    await kg.link_domains("health", "legal", "GOVERNED_BY")

    _, params = mock_connector.run_query.call_args.args
    assert params["source"] == "health"
    assert params["target"] == "legal"

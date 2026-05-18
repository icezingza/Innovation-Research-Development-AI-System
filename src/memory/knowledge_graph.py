import logging
from typing import Any

from src.memory.neo4j_connector import Neo4jKnowledgeConnector

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Semantic hypothesis and contradiction graph backed by Neo4j.

    Nodes:
      (:Hypothesis)  — evolved hypothesis with confidence + generation
      (:Statement)   — raw statement involved in a contradiction

    Relationships:
      -[:EVOLVED_TO]->   — parent hypothesis → child hypothesis
      -[:CONTRADICTS]->  — statement A contradicts statement B
    """

    def __init__(self, connector: Neo4jKnowledgeConnector) -> None:
        self._connector = connector

    async def store_hypothesis(
        self,
        hypothesis_id: str,
        statement: str,
        confidence: float,
        generation: int,
        task_id: str,
    ) -> None:
        await self._connector.run_query(
            """
            MERGE (h:Hypothesis {id: $id})
            SET h.statement  = $statement,
                h.confidence = $confidence,
                h.generation = $generation,
                h.task_id    = $task_id
            """,
            {
                "id": hypothesis_id,
                "statement": statement,
                "confidence": confidence,
                "generation": generation,
                "task_id": task_id,
            },
        )

    async def link_evolution(self, parent_id: str, child_id: str) -> None:
        await self._connector.run_query(
            """
            MATCH (parent:Hypothesis {id: $parent_id})
            MATCH (child:Hypothesis  {id: $child_id})
            MERGE (parent)-[:EVOLVED_TO]->(child)
            """,
            {"parent_id": parent_id, "child_id": child_id},
        )

    async def store_contradiction(
        self,
        stmt_a: str,
        stmt_b: str,
        contradiction_type: str,
        severity: float,
    ) -> None:
        await self._connector.run_query(
            """
            MERGE (a:Statement {text: $text_a})
            MERGE (b:Statement {text: $text_b})
            MERGE (a)-[r:CONTRADICTS]->(b)
            SET r.type = $type, r.severity = $severity
            """,
            {
                "text_a": stmt_a,
                "text_b": stmt_b,
                "type": contradiction_type,
                "severity": severity,
            },
        )

    async def get_hypothesis_lineage(self, hypothesis_id: str) -> list[dict[str, Any]]:
        return await self._connector.run_query(
            """
            MATCH path = (root:Hypothesis)-[:EVOLVED_TO*0..]->(h:Hypothesis {id: $id})
            WITH nodes(path) AS hypotheses
            UNWIND hypotheses AS hyp
            RETURN DISTINCT
                hyp.id         AS id,
                hyp.statement  AS statement,
                hyp.confidence AS confidence,
                hyp.generation AS generation
            ORDER BY hyp.generation
            """,
            {"id": hypothesis_id},
        )

    async def find_related(
        self, hypothesis_id: str, max_depth: int = 2
    ) -> list[dict[str, Any]]:
        return await self._connector.run_query(
            """
            MATCH (h:Hypothesis {id: $id})-[:EVOLVED_TO*1..$depth]-(rel:Hypothesis)
            WHERE rel.id <> $id
            RETURN DISTINCT
                rel.id         AS id,
                rel.statement  AS statement,
                rel.confidence AS confidence,
                rel.generation AS generation
            """,
            {"id": hypothesis_id, "depth": max_depth},
        )

    async def store_domain_concept(
        self,
        domain: str,
        concept: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create (:Domain)-[:CONTAINS]->(:Concept) in the knowledge graph."""
        props = properties or {}
        await self._connector.run_query(
            """
            MERGE (d:Domain {name: $domain})
            MERGE (c:Concept {name: $concept})
            SET c += $properties
            MERGE (d)-[:CONTAINS]->(c)
            """,
            {"domain": domain, "concept": concept, "properties": props},
        )

    async def store_speculative_knowledge(
        self,
        node_id: str,
        source: str,
        content: str,
        confidence: float,
    ) -> None:
        """Persist a (:SpeculativeKnowledge) node from meta-learning feedback."""
        await self._connector.run_query(
            """
            MERGE (sk:SpeculativeKnowledge {id: $id})
            SET sk.source     = $source,
                sk.content    = $content,
                sk.confidence = $confidence
            """,
            {
                "id": node_id,
                "source": source,
                "content": content,
                "confidence": confidence,
            },
        )

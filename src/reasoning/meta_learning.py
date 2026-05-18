import logging
import uuid
from typing import Any

from src.memory.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class MetaLearningPipeline:
    """Persists critique-agent feedback as SpeculativeKnowledge nodes in Neo4j.

    Works in degraded mode (no-op) when KnowledgeGraph is unavailable.
    """

    def __init__(self, knowledge_graph: KnowledgeGraph | None = None) -> None:
        self._kg = knowledge_graph

    async def ingest(self, feedback: dict[str, Any]) -> None:
        """Store a feedback record as a (:SpeculativeKnowledge) node.

        Args:
            feedback: Dict with keys: source (str), content (str),
                      confidence (float, default 0.5).
        """
        if self._kg is None:
            logger.debug("meta_learning_skipped: knowledge_graph unavailable")
            return

        source = str(feedback.get("source", "unknown"))
        content = str(feedback.get("content", ""))
        confidence = float(feedback.get("confidence", 0.5))
        node_id = str(uuid.uuid4())

        try:
            await self._kg.store_speculative_knowledge(
                node_id=node_id,
                source=source,
                content=content,
                confidence=confidence,
            )
            logger.info(
                "speculative_knowledge_stored",
                extra={"node_id": node_id, "source": source},
            )
        except Exception as exc:
            logger.warning(
                "meta_learning_ingest_failed", extra={"error": str(exc)}
            )

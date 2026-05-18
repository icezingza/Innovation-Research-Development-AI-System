import asyncio
import logging
from typing import Any

from pydantic import BaseModel

from src.memory.corpus_ingestion import SPECIALIZED_CORPUS_COLLECTION

logger = logging.getLogger(__name__)

RESEARCH_COLLECTION = "research_hypotheses"


class ContextPacket(BaseModel):
    """Enriched context built from semantic memory for an agent's next cycle."""

    question: str
    similar_hypotheses: list[dict]
    specialized_results: list[dict] = []
    continuity_score: float  # 0.0 = no prior context, 1.0 = rich context


class ContextEngine:
    """Builds semantic context for agents by querying vector memory.

    When Qdrant and an embedding provider are available, the agent receives
    semantically similar past hypotheses and specialized corpus chunks so
    reasoning can accumulate across tasks and domain knowledge.
    """

    def __init__(self, vector_store: Any, embedding_provider: Any) -> None:
        self._vector_store = vector_store
        self._embedding = embedding_provider

    async def build(self, question: str, limit: int = 5) -> ContextPacket:
        if not self._embedding.enabled:
            return ContextPacket(
                question=question, similar_hypotheses=[], continuity_score=0.0
            )
        try:
            embedding = await self._embedding.embed(question)
            
            # Parallel search for hypotheses and specialized knowledge
            h_task = self._vector_store.search_similar(
                query_embedding=embedding,
                collection=RESEARCH_COLLECTION,
                limit=limit,
            )
            s_task = self._vector_store.search_similar(
                query_embedding=embedding,
                collection=SPECIALIZED_CORPUS_COLLECTION,
                limit=limit,
            )
            
            h_results, s_results = await asyncio.gather(h_task, s_task)

            score = min(1.0, (len(h_results) + len(s_results)) / max(limit * 2, 1))
            return ContextPacket(
                question=question,
                similar_hypotheses=[r["payload"] for r in h_results if r.get("payload")],
                specialized_results=[r["payload"] for r in s_results if r.get("payload")],
                continuity_score=round(score, 2),
            )
        except Exception as exc:
            logger.warning("context_build_failed", extra={"error": str(exc)})
            return ContextPacket(
                question=question, similar_hypotheses=[], continuity_score=0.0
            )

    async def store_hypothesis(
        self, hypothesis: dict[str, Any], question: str, task_id: str
    ) -> None:
        """Embed and persist a hypothesis into vector memory."""
        if not self._embedding.enabled:
            return
        try:
            text = f"{question} — {hypothesis.get('statement', '')}"
            embedding = await self._embedding.embed(text)
            import hashlib

            point_id = int(hashlib.md5(task_id.encode()).hexdigest()[:8], 16)
            await self._vector_store.store_embedding(
                embedding=embedding,
                metadata={
                    "collection": RESEARCH_COLLECTION,
                    "id": point_id,
                    "task_id": task_id,
                    "question": question,
                    "statement": hypothesis.get("statement", ""),
                    "confidence": hypothesis.get("confidence", 0.0),
                    "generation": hypothesis.get("generation", 0),
                },
            )
        except Exception as exc:
            logger.warning(
                "hypothesis_store_failed", extra={"task_id": task_id, "error": str(exc)}
            )

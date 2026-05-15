from typing import Any

from src.agents.base_agent import BaseAgent
from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_CRITIQUED,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.reasoning.contradiction_analyzer import ContradictionAnalyzer
from src.reasoning.reflection_engine import ReflectionEngine


class CritiqueAgent(BaseAgent):
    """Stress-tests a hypothesis — identifies contradictions, gaps, and weaknesses.

    Takes an existing hypothesis from context["hypothesis"] and produces a
    critique alongside a refined version with improved confidence calibration.
    Publishes hypothesis.critiqued events when a bus is wired.
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        contradiction_analyzer: ContradictionAnalyzer | None = None,
        inference_router: Any | None = None,
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        super().__init__()
        self._reflection = reflection_engine or ReflectionEngine()
        self._contradiction = contradiction_analyzer or ContradictionAnalyzer()
        self._inference = inference_router
        self._bus = event_bus

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        hypothesis = context.get("hypothesis", {})
        return {
            "statement": str(hypothesis.get("statement", "")),
            "confidence": float(hypothesis.get("confidence", 0.5)),
            "evidence": list(hypothesis.get("evidence", [])),
            "hypothesis_id": str(hypothesis.get("id", "")),
            "question": str(context.get("question", "")),
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        statement = perception["statement"]
        question = perception["question"]

        counter_statement = f"Counter-argument: {statement} may be insufficient"
        if self._inference is not None and self._inference.enabled:
            output = await self._inference.complete(
                prompt=(
                    f"Identify the main weakness or untested assumption in this "
                    f"hypothesis: '{statement}'. "
                    f"Context question: {question}"
                ),
                system=(
                    "You are a scientific peer reviewer. Be concise and specific. "
                    "One sentence identifying the primary weakness."
                ),
            )
            if output:
                counter_statement = output.strip()

        contradiction_report = await self._contradiction.analyze(
            [statement, counter_statement]
        )

        reflection = await self._reflection.reflect(
            {
                "statement": statement,
                "evidence": perception["evidence"],
                "conclusion": statement,
                "confidence": perception["confidence"],
            }
        )

        refined_confidence = max(
            0.1, perception["confidence"] - (0.1 if reflection.gaps else 0.0)
        )

        return {
            "original_statement": statement,
            "critique": counter_statement,
            "contradictions_found": len(contradiction_report.contradictions),
            "is_consistent": contradiction_report.is_consistent,
            "gaps": reflection.gaps,
            "quality_score": reflection.quality_score,
            "refined_confidence": refined_confidence,
            "hypothesis_id": perception["hypothesis_id"],
            "question": question,
        }

    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        result = {
            "critique": reasoning["critique"],
            "gaps": reasoning["gaps"],
            "contradictions_found": reasoning["contradictions_found"],
            "is_consistent": reasoning["is_consistent"],
            "quality_score": reasoning["quality_score"],
            "refined_confidence": reasoning["refined_confidence"],
            "original_statement": reasoning["original_statement"],
        }

        if self._bus is not None:
            await self._bus.publish(
                RuntimeEvent(
                    topic=TOPIC_HYPOTHESIS_CRITIQUED,
                    source_agent_id=self.agent_id,
                    payload={
                        "hypothesis_id": reasoning["hypothesis_id"],
                        "critique": reasoning["critique"],
                        "refined_confidence": reasoning["refined_confidence"],
                        "is_consistent": reasoning["is_consistent"],
                    },
                )
            )
        return result

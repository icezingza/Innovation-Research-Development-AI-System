import uuid
from typing import Any

from src.agents.base_agent import BaseAgent
from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_GENERATED,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.reasoning.reflection_engine import ReflectionEngine
from src.research.hypothesis_evolution import Hypothesis, HypothesisEvolutionEngine


class HypothesisAgent(BaseAgent):
    """Generates and evolves a single hypothesis for a given research question.

    Focused counterpart to ResearchAgent — no debate or recursion overhead.
    Publishes hypothesis.generated events when a bus is wired.
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        hypothesis_engine: HypothesisEvolutionEngine | None = None,
        inference_router: Any | None = None,
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        super().__init__()
        self._reflection = reflection_engine or ReflectionEngine()
        self._hypothesis = hypothesis_engine or HypothesisEvolutionEngine(
            self._reflection
        )
        self._inference = inference_router
        self._bus = event_bus

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "question": str(context.get("question", "")),
            "prior_evidence": list(context.get("prior_evidence", [])),
            "generation": int(context.get("generation", 0)),
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        question = perception["question"]
        statement = f"Hypothesis for: {question}"

        if self._inference is not None and self._inference.enabled:
            output = await self._inference.complete(
                prompt=(
                    f"Generate one concise, falsifiable scientific hypothesis for: "
                    f"{question}"
                ),
                system=(
                    "You are a scientific reasoning assistant. "
                    "One sentence only. Be precise and testable."
                ),
            )
            if output:
                statement = output.strip()

        initial = Hypothesis(
            id=str(uuid.uuid4()),
            statement=statement,
            confidence=0.5,
            evidence=perception["prior_evidence"] or [f"Derived from: {question}"],
            generation=perception["generation"],
        )
        evolution = await self._hypothesis.evolve(initial)
        reflection = await self._reflection.reflect(
            {
                "statement": evolution.evolved.statement,
                "evidence": evolution.evolved.evidence,
                "conclusion": evolution.evolved.statement,
            }
        )
        return {
            "question": question,
            "hypothesis": evolution.evolved.model_dump(),
            "quality_score": reflection.quality_score,
            "gaps": reflection.gaps,
        }

    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        hypothesis = reasoning["hypothesis"]
        result = {
            "hypothesis": hypothesis,
            "quality_score": reasoning["quality_score"],
            "gaps": reasoning["gaps"],
        }

        if self._bus is not None:
            await self._bus.publish(
                RuntimeEvent(
                    topic=TOPIC_HYPOTHESIS_GENERATED,
                    source_agent_id=self.agent_id,
                    payload={
                        "question": reasoning["question"],
                        "hypothesis_id": hypothesis.get("id", ""),
                        "statement": hypothesis.get("statement", ""),
                        "confidence": hypothesis.get("confidence", 0.0),
                    },
                )
            )
        return result

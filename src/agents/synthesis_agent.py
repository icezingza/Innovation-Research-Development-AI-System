from typing import Any

from src.agents.base_agent import BaseAgent
from src.infrastructure.event_bus import (
    TOPIC_SYNTHESIS_READY,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.reasoning.reflection_engine import ReflectionEngine


class SynthesisAgent(BaseAgent):
    """Synthesizes multiple hypotheses into a single coherent conclusion.

    Receives a list of hypotheses from context["hypotheses"] and a goal from
    context["goal"]. Scores each via ReflectionEngine, selects the best, and
    produces a synthesized conclusion.
    Publishes synthesis.ready events when a bus is wired.
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        inference_router: Any | None = None,
        event_bus: RuntimeEventBus | None = None,
    ) -> None:
        super().__init__()
        self._reflection = reflection_engine or ReflectionEngine()
        self._inference = inference_router
        self._bus = event_bus

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "goal": str(context.get("goal", "")),
            "hypotheses": list(context.get("hypotheses", [])),
            "critiques": list(context.get("critiques", [])),
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        goal = perception["goal"]
        hypotheses = perception["hypotheses"]
        critiques = perception["critiques"]

        if not hypotheses:
            return {
                "goal": goal,
                "conclusion": f"No hypotheses provided for: {goal}",
                "confidence": 0.0,
                "evidence_count": 0,
                "source_count": 0,
            }

        scored: list[tuple[float, dict]] = []
        for h in hypotheses:
            r = await self._reflection.reflect(
                {
                    "statement": h.get("statement", ""),
                    "evidence": h.get("evidence", []),
                    "conclusion": h.get("statement", ""),
                    "confidence": h.get("confidence", 0.5),
                }
            )
            scored.append((r.quality_score, h))

        scored.sort(key=lambda t: t[0], reverse=True)
        best_score, best_hypothesis = scored[0]
        all_evidence: list[str] = []
        for _, h in scored:
            all_evidence.extend(h.get("evidence", []))

        conclusion = best_hypothesis.get("statement", f"Synthesized finding for: {goal}")

        if self._inference is not None and self._inference.enabled:
            hyp_text = "\n".join(
                f"- {h.get('statement', '')} (q={s:.2f})" for s, h in scored
            )
            critique_text = ""
            if critiques:
                critique_text = "\nCritiques:\n" + "\n".join(
                    f"- {c.get('critique', '')}" for c in critiques
                )
            output = await self._inference.complete(
                prompt=(
                    f"Synthesize these hypotheses into one coherent conclusion "
                    f"for: {goal}\n\nHypotheses:\n{hyp_text}{critique_text}"
                ),
                system=(
                    "You are a scientific synthesis expert. "
                    "Be concise and evidence-based. One paragraph."
                ),
            )
            if output:
                conclusion = output.strip()

        return {
            "goal": goal,
            "conclusion": conclusion,
            "confidence": best_score,
            "evidence_count": len(set(all_evidence)),
            "source_count": len(hypotheses),
            "best_hypothesis_id": best_hypothesis.get("id", ""),
        }

    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        result = {
            "goal": reasoning["goal"],
            "conclusion": reasoning["conclusion"],
            "confidence": reasoning["confidence"],
            "evidence_count": reasoning["evidence_count"],
            "source_count": reasoning["source_count"],
        }

        if self._bus is not None:
            await self._bus.publish(
                RuntimeEvent(
                    topic=TOPIC_SYNTHESIS_READY,
                    source_agent_id=self.agent_id,
                    payload={
                        "goal": reasoning["goal"],
                        "confidence": reasoning["confidence"],
                        "source_count": reasoning["source_count"],
                        "best_hypothesis_id": reasoning.get("best_hypothesis_id", ""),
                    },
                )
            )
        return result

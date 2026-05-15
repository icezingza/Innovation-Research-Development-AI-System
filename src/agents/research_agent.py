import uuid
from typing import Any

from src.agents.base_agent import BaseAgent
from src.reasoning.contradiction_analyzer import ContradictionAnalyzer
from src.reasoning.reflection_engine import ReflectionEngine
from src.research.hypothesis_evolution import Hypothesis, HypothesisEvolutionEngine


class ResearchAgent(BaseAgent):
    """Cognitive agent that forms, evolves, and validates scientific hypotheses.

    Operates in three modes:
      - Heuristic: no inference router, no context engine (always available)
      - LLM-augmented: inference router available, enhances hypothesis generation
      - Memory-aware: context engine available, retrieves similar past work from
        Qdrant and stores evolved hypotheses back for future continuity
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        contradiction_analyzer: ContradictionAnalyzer | None = None,
        hypothesis_engine: HypothesisEvolutionEngine | None = None,
        inference_router: Any | None = None,
        context_engine: Any | None = None,
    ) -> None:
        super().__init__()
        self._reflection = reflection_engine or ReflectionEngine()
        self._contradiction = contradiction_analyzer or ContradictionAnalyzer()
        self._hypothesis = hypothesis_engine or HypothesisEvolutionEngine(
            self._reflection
        )
        self._inference = inference_router
        self._context = context_engine

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        question = str(context.get("question", ""))
        prior_hypotheses = list(context.get("prior_hypotheses", []))
        constraints = list(context.get("constraints", []))

        # Enrich perception with semantic memory when context engine is available
        semantic_context: dict[str, Any] = {}
        if self._context is not None:
            packet = await self._context.build(question)
            semantic_context = {
                "similar_hypotheses": packet.similar_hypotheses,
                "continuity_score": packet.continuity_score,
            }
            # Inject similar past hypotheses into prior context
            for h in packet.similar_hypotheses:
                statement = h.get("statement", "")
                if statement and statement not in prior_hypotheses:
                    prior_hypotheses.append(statement)

        return {
            "question": question,
            "prior_hypotheses": prior_hypotheses,
            "constraints": constraints,
            **semantic_context,
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        question = perception["question"]
        statement = f"Initial hypothesis for: {question}"

        # LLM augmentation when inference router is available
        if self._inference is not None and self._inference.enabled:
            llm_output = await self._inference.complete(
                prompt=f"Generate one testable scientific hypothesis for: {question}",
                system=(
                    "You are a scientific reasoning assistant. "
                    "Be concise, falsifiable, and precise. One sentence only."
                ),
            )
            if llm_output:
                statement = llm_output.strip()

        initial = Hypothesis(
            id=str(uuid.uuid4()),
            statement=statement,
            confidence=0.5,
            evidence=[f"Derived from question: {question}"],
            generation=0,
        )

        evolution = await self._hypothesis.evolve(initial)

        reflection = await self._reflection.reflect(
            {
                "question": question,
                "statement": evolution.evolved.statement,
                "evidence": evolution.evolved.evidence,
                "conclusion": evolution.evolved.statement,
                "confidence": evolution.evolved.confidence,
            }
        )

        contradiction_report = None
        prior = perception["prior_hypotheses"]
        if prior:
            candidates = [str(h) for h in prior] + [evolution.evolved.statement]
            contradiction_report = await self._contradiction.analyze(candidates)

        return {
            "question": question,
            "initial_hypothesis": initial.model_dump(),
            "evolved_hypothesis": evolution.evolved.model_dump(),
            "evolution_changes": evolution.changes,
            "reflection": reflection.model_dump(),
            "contradictions": (
                contradiction_report.model_dump() if contradiction_report else None
            ),
        }

    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        contradictions = reasoning.get("contradictions")
        return {
            "hypothesis": reasoning["evolved_hypothesis"],
            "quality_score": reasoning["reflection"]["quality_score"],
            "gaps": reasoning["reflection"]["gaps"],
            "suggestions": reasoning["reflection"]["suggestions"],
            "is_consistent": (
                contradictions["is_consistent"] if contradictions else True
            ),
        }

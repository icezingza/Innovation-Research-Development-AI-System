import uuid
from typing import Any

from src.agents.base_agent import BaseAgent
from src.reasoning.contradiction_analyzer import ContradictionAnalyzer
from src.reasoning.reflection_engine import ReflectionEngine
from src.research.hypothesis_evolution import Hypothesis, HypothesisEvolutionEngine


class ResearchAgent(BaseAgent):
    """Cognitive agent that forms, evolves, and validates scientific hypotheses.

    Works without an inference client (heuristic mode). When an InferenceClient
    is injected and enabled it augments hypothesis generation with LLM output.
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        contradiction_analyzer: ContradictionAnalyzer | None = None,
        hypothesis_engine: HypothesisEvolutionEngine | None = None,
        inference_client: Any | None = None,
    ) -> None:
        super().__init__()
        self._reflection = reflection_engine or ReflectionEngine()
        self._contradiction = contradiction_analyzer or ContradictionAnalyzer()
        self._hypothesis = hypothesis_engine or HypothesisEvolutionEngine(
            self._reflection
        )
        self._inference = inference_client

    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "question": str(context.get("question", "")),
            "prior_hypotheses": list(context.get("prior_hypotheses", [])),
            "constraints": list(context.get("constraints", [])),
        }

    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        question = perception["question"]

        statement = f"Initial hypothesis for: {question}"

        # Augment with LLM when available
        if self._inference is not None and self._inference.enabled:
            llm_output = await self._inference.complete(
                prompt=f"Generate one testable scientific hypothesis for: {question}"
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

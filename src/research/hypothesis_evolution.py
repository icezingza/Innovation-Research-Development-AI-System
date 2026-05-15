import time
import uuid

from pydantic import BaseModel

from src.reasoning.reflection_engine import ReflectionEngine
from src.telemetry.runtime_metrics import reasoning_latency
from src.telemetry.tracing import tracer


class Hypothesis(BaseModel):
    id: str
    statement: str
    confidence: float
    evidence: list[str]
    generation: int = 0


class EvolutionResult(BaseModel):
    original: Hypothesis
    evolved: Hypothesis
    improvement_delta: float
    changes: list[str]


class HypothesisEvolutionEngine:
    """Recursively refines scientific hypotheses using structured reflection."""

    def __init__(self, reflection_engine: ReflectionEngine | None = None) -> None:
        self._reflection = reflection_engine or ReflectionEngine()

    async def evolve(self, hypothesis: Hypothesis) -> EvolutionResult:
        with tracer.start_as_current_span("research.evolve_hypothesis"):
            start = time.monotonic()
            result = await self._evolve(hypothesis)
            reasoning_latency.observe(time.monotonic() - start)
            return result

    async def _evolve(self, hypothesis: Hypothesis) -> EvolutionResult:
        reflection = await self._reflection.reflect(
            {
                "statement": hypothesis.statement,
                "confidence": hypothesis.confidence,
                "evidence": hypothesis.evidence,
                "conclusion": hypothesis.statement,
                "assumptions": None,
            }
        )
        evolved_statement = self._refine_statement(
            hypothesis.statement, reflection.gaps
        )
        new_confidence = min(
            1.0, hypothesis.confidence + reflection.quality_score * 0.1
        )
        evolved = Hypothesis(
            id=str(uuid.uuid4()),
            statement=evolved_statement,
            confidence=round(new_confidence, 4),
            evidence=hypothesis.evidence,
            generation=hypothesis.generation + 1,
        )
        return EvolutionResult(
            original=hypothesis,
            evolved=evolved,
            improvement_delta=round(new_confidence - hypothesis.confidence, 4),
            changes=reflection.suggestions,
        )

    @staticmethod
    def _refine_statement(statement: str, gaps: list[str]) -> str:
        if not gaps:
            return statement
        qualifications = "; ".join(gaps[:2])
        return f"{statement} [requires: {qualifications}]"

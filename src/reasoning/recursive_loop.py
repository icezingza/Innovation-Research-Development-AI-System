import time

from pydantic import BaseModel

from src.reasoning.reasoning_trace import ReasoningTrace, TraceEntry
from src.reasoning.reflection_engine import ReflectionEngine
from src.research.hypothesis_evolution import Hypothesis, HypothesisEvolutionEngine
from src.telemetry.runtime_metrics import reasoning_latency
from src.telemetry.tracing import tracer


class RecursiveConfig(BaseModel):
    max_depth: int = 5
    convergence_threshold: float = 0.85
    min_improvement: float = 0.02


class IterationRecord(BaseModel):
    depth: int
    hypothesis: Hypothesis
    quality_score: float
    changes: list[str]
    improvement_delta: float


class RecursiveReasoningResult(BaseModel):
    question: str
    initial_hypothesis: Hypothesis
    final_hypothesis: Hypothesis
    iterations: list[IterationRecord]
    final_quality: float
    depth_reached: int
    converged: bool
    convergence_reason: str
    duration_seconds: float


class RecursiveReasoningLoop:
    """Iteratively evolves a hypothesis until quality converges or max depth is reached.

    Convergence conditions (checked in order):
      1. quality_score >= convergence_threshold  → quality_threshold_reached
      2. improvement < min_improvement (after depth > 1)  → no_improvement
      3. depth == max_depth  → max_depth_reached (not converged)
    """

    def __init__(
        self,
        hypothesis_engine: HypothesisEvolutionEngine | None = None,
        reflection_engine: ReflectionEngine | None = None,
        trace: ReasoningTrace | None = None,
        config: RecursiveConfig | None = None,
    ) -> None:
        self._hypothesis = hypothesis_engine or HypothesisEvolutionEngine()
        self._reflection = reflection_engine or ReflectionEngine()
        self._trace = trace
        self._config = config or RecursiveConfig()

    async def run(
        self, initial_hypothesis: Hypothesis, question: str = ""
    ) -> RecursiveReasoningResult:
        with tracer.start_as_current_span("reasoning.recursive_loop"):
            start = time.monotonic()
            result = await self._loop(initial_hypothesis, question)
            elapsed = time.monotonic() - start
            reasoning_latency.observe(elapsed)
            return result.model_copy(update={"duration_seconds": round(elapsed, 4)})

    async def _loop(
        self, initial: Hypothesis, question: str
    ) -> RecursiveReasoningResult:
        cfg = self._config
        current = initial
        iterations: list[IterationRecord] = []
        prev_quality = 0.0
        convergence_reason = "max_depth_reached"

        for depth in range(1, cfg.max_depth + 1):
            evolution = await self._hypothesis.evolve(current)
            reflection = await self._reflection.reflect(
                {
                    "statement": evolution.evolved.statement,
                    "evidence": evolution.evolved.evidence,
                    "conclusion": evolution.evolved.statement,
                    "confidence": evolution.evolved.confidence,
                }
            )

            improvement = abs(reflection.quality_score - prev_quality)
            iterations.append(
                IterationRecord(
                    depth=depth,
                    hypothesis=evolution.evolved,
                    quality_score=reflection.quality_score,
                    changes=evolution.changes,
                    improvement_delta=round(improvement, 4),
                )
            )

            if self._trace is not None:
                await self._trace.record(
                    TraceEntry(
                        operation="recursive_evolution",
                        input_hash=ReasoningTrace.hash_input(current.model_dump()),
                        output_summary=(
                            f"depth={depth} quality={reflection.quality_score:.2f} "
                            f"delta={improvement:.3f}"
                        ),
                    )
                )

            current = evolution.evolved

            if reflection.quality_score >= cfg.convergence_threshold:
                convergence_reason = "quality_threshold_reached"
                break

            if depth > 1 and improvement < cfg.min_improvement:
                convergence_reason = "no_improvement"
                break

            prev_quality = reflection.quality_score

        final_reflection = await self._reflection.reflect(
            {
                "statement": current.statement,
                "evidence": current.evidence,
                "conclusion": current.statement,
                "confidence": current.confidence,
            }
        )

        return RecursiveReasoningResult(
            question=question,
            initial_hypothesis=initial,
            final_hypothesis=current,
            iterations=iterations,
            final_quality=final_reflection.quality_score,
            depth_reached=len(iterations),
            converged=convergence_reason != "max_depth_reached",
            convergence_reason=convergence_reason,
            duration_seconds=0.0,
        )

import hashlib
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel

from src.reasoning.contradiction_analyzer import ContradictionAnalyzer
from src.reasoning.math_engine.golden_bayesian import GoldenBayesian
from src.reasoning.reflection_engine import ReflectionEngine
from src.telemetry.runtime_metrics import runtime_events
from src.telemetry.tracing import tracer
from src.reasoning.adaptive_reasoning import AdaptiveReasoningEngine
from src.reasoning.self_healing import SelfHealingOptimizer


class DebatePosition(BaseModel):
    agent_id: str
    role: Literal["proponent", "opponent"]
    argument: str
    confidence: float
    round_number: int


class DebateRound(BaseModel):
    round_number: int
    proponent: DebatePosition
    opponent: DebatePosition
    contradictions_found: int
    is_consistent: bool


class DebateResult(BaseModel):
    debate_id: str
    hypothesis: str
    rounds: list[DebateRound]
    winner: Literal["proponent", "opponent", "draw"]
    winner_argument: str
    proponent_final_quality: float
    opponent_final_quality: float
    converged: bool
    convergence_reason: str = ""
    total_rounds: int
    duration_seconds: float


class DebateRuntime:
    """Structured adversarial debate between two reasoning agents.

    Each round: Proponent generates supporting argument, Opponent generates
    counter-argument. ContradictionAnalyzer finds logical conflicts. If no
    contradictions remain, debate converges early. ReflectionEngine scores
    final positions to determine the winner.

    Works in heuristic mode (no LLM) and LLM-augmented mode.
    """

    def __init__(
        self,
        contradiction_analyzer: ContradictionAnalyzer | None = None,
        reflection_engine: ReflectionEngine | None = None,
        inference_router: Any | None = None,
    ) -> None:
        self._contradiction = contradiction_analyzer or ContradictionAnalyzer()
        self._reflection = reflection_engine or ReflectionEngine()
        self._inference = inference_router
        self._proponent_id = f"proponent-{str(uuid.uuid4())[:8]}"
        self._opponent_id = f"opponent-{str(uuid.uuid4())[:8]}"
        self._adaptive_engine = AdaptiveReasoningEngine(self._inference)
        self._self_healing = SelfHealingOptimizer()

    async def debate(self, hypothesis: str, max_rounds: int = 3) -> DebateResult:
        with tracer.start_as_current_span("orchestration.debate"):
            start = time.monotonic()
            result = await self._run(hypothesis, max_rounds)
            elapsed = time.monotonic() - start
            return result.model_copy(update={"duration_seconds": round(elapsed, 4)})

    async def _generate(
        self,
        hypothesis: str,
        role: Literal["proponent", "opponent"],
        prior_argument: str | None,
    ) -> tuple[str, float]:
        if self._inference is not None and self._inference.enabled:
            if role == "proponent":
                prompt = (
                    "Generate a concise scientific supporting argument for: "
                    f"{hypothesis}"
                    + (
                        f"\nAddress this counter-argument: {prior_argument}"
                        if prior_argument
                        else ""
                    )
                )
            else:
                prompt = (
                    "Generate a concise scientific counter-argument against: "
                    f"{hypothesis}"
                    + (
                        f"\nAddress this supporting argument: {prior_argument}"
                        if prior_argument
                        else ""
                    )
                )
            system_prompt = (
                "You are a scientific debate participant. "
                "Be precise, use evidence-based reasoning, one paragraph only."
            )
            # Apply active ASI self-healing optimizations
            optimizations = self._self_healing.get_active_optimizations("global")
            for opt in optimizations:
                if opt.get("prompt_injection"):
                    system_prompt += f" {opt['prompt_injection']}"

            try:
                output = await self._inference.complete(
                    prompt=prompt,
                    system=system_prompt,
                    temperature=0.75,
                )
                if output:
                    return output.strip(), 0.72
            except Exception as e:
                # Trigger self-healing on failure
                await self._self_healing.ingest_failure_event(
                    "inference_error", {"agent_id": "global", "error": str(e)}
                )
                raise

        # Heuristic fallback
        if role == "proponent":
            base = (
                f"Supporting evidence for '{hypothesis}': empirical observations "
                "align with this mechanism under controlled conditions, and prior "
                "literature reinforces the causal relationship."
            )
        else:
            base = (
                f"Counter-evidence against '{hypothesis}': confounding variables "
                "have not been ruled out, and alternative mechanisms produce "
                "equivalent observed effects without requiring this hypothesis."
            )
        return base, 0.55

    @staticmethod
    def _argument_hash(proponent: str, opponent: str) -> str:
        combined = f"{proponent}|||{opponent}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _detect_circuit_breaker(self, rounds: list[DebateRound]) -> bool:
        """Return True if any two consecutive rounds share identical argument hashes."""
        if len(rounds) < 2:
            return False
        hashes = [
            self._argument_hash(r.proponent.argument, r.opponent.argument)
            for r in rounds
        ]
        return any(hashes[i] == hashes[i + 1] for i in range(len(hashes) - 1))

    async def _run(self, hypothesis: str, max_rounds: int) -> DebateResult:
        # Adaptive Reasoning check
        complexity_data = await self._adaptive_engine.evaluate_task_complexity(
            hypothesis
        )
        if complexity_data["complexity_score"] <= 3:
            # Fast track without full debate
            return DebateResult(
                debate_id=str(uuid.uuid4()),
                hypothesis=hypothesis,
                rounds=[],
                winner="proponent",
                winner_argument=f"Fast resolution (Complexity: {complexity_data['complexity_score']}): {hypothesis}",
                proponent_final_quality=0.85,
                opponent_final_quality=0.0,
                converged=True,
                convergence_reason="adaptive_fast_track",
                total_rounds=0,
                duration_seconds=0.0,
            )

        rounds: list[DebateRound] = []
        proponent_arg: str | None = None
        opponent_arg: str | None = None

        for round_num in range(1, max_rounds + 1):
            proponent_text, proponent_conf = await self._generate(
                hypothesis, "proponent", prior_argument=opponent_arg
            )
            opponent_text, opponent_conf = await self._generate(
                hypothesis, "opponent", prior_argument=proponent_arg
            )
            proponent_arg = proponent_text
            opponent_arg = opponent_text

            report = await self._contradiction.analyze([proponent_text, opponent_text])

            rounds.append(
                DebateRound(
                    round_number=round_num,
                    proponent=DebatePosition(
                        agent_id=self._proponent_id,
                        role="proponent",
                        argument=proponent_text,
                        confidence=proponent_conf,
                        round_number=round_num,
                    ),
                    opponent=DebatePosition(
                        agent_id=self._opponent_id,
                        role="opponent",
                        argument=opponent_text,
                        confidence=opponent_conf,
                        round_number=round_num,
                    ),
                    contradictions_found=len(report.contradictions),
                    is_consistent=report.is_consistent,
                )
            )
            runtime_events.labels(event_type="debate_round_complete").inc()

            if report.is_consistent:
                break

        # Circuit breaker: stale debate detected → force Bayesian synthesis
        circuit_breaker_triggered = not (
            bool(rounds) and rounds[-1].is_consistent
        ) and self._detect_circuit_breaker(rounds)
        convergence_reason = ""
        if circuit_breaker_triggered:
            evidence_scores = [
                (r.proponent.confidence + r.opponent.confidence) / 2 for r in rounds
            ]
            contradiction_flags = [not r.is_consistent for r in rounds]
            GoldenBayesian.batch_update(
                prior=0.5,
                evidence_scores=evidence_scores,
                contradiction_flags=contradiction_flags,
            )
            convergence_reason = "circuit_breaker"
            runtime_events.labels(event_type="debate_circuit_breaker").inc()

        # Score final positions with reflection engine
        p_reflection = await self._reflection.reflect(
            {
                "statement": proponent_arg or "",
                "evidence": [hypothesis],
                "conclusion": proponent_arg or "",
            }
        )
        o_reflection = await self._reflection.reflect(
            {
                "statement": opponent_arg or "",
                "evidence": [hypothesis],
                "conclusion": opponent_arg or "",
            }
        )

        p_score = p_reflection.quality_score
        o_score = o_reflection.quality_score

        if p_score > o_score:
            winner: Literal["proponent", "opponent", "draw"] = "proponent"
            winner_argument = proponent_arg or ""
        elif o_score > p_score:
            winner = "opponent"
            winner_argument = opponent_arg or ""
        else:
            winner = "draw"
            winner_argument = f"Both positions have equal merit regarding: {hypothesis}"

        converged = bool(rounds) and rounds[-1].is_consistent
        runtime_events.labels(event_type="debate_complete").inc()

        return DebateResult(
            debate_id=str(uuid.uuid4()),
            hypothesis=hypothesis,
            rounds=rounds,
            winner=winner,
            winner_argument=winner_argument,
            proponent_final_quality=p_score,
            opponent_final_quality=o_score,
            converged=converged,
            convergence_reason=convergence_reason,
            total_rounds=len(rounds),
            duration_seconds=0.0,
        )

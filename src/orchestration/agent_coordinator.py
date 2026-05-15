import asyncio
import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.infrastructure.event_bus import (
    TOPIC_COORDINATION_COMPLETE,
    TOPIC_COORDINATION_STARTED,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.telemetry.runtime_metrics import runtime_events
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


class CoordinatorConfig(BaseModel):
    max_sub_questions: int = 3
    run_critique: bool = True
    heuristic_sub_question_templates: list[str] = [
        "What mechanisms explain: {goal}?",
        "What evidence supports or refutes: {goal}?",
        "What are the boundary conditions of: {goal}?",
    ]


class CoordinatedResult(BaseModel):
    session_id: str
    goal: str
    sub_questions: list[str]
    hypotheses: list[dict[str, Any]]
    critiques: list[dict[str, Any]]
    synthesis: dict[str, Any]
    events_published: int
    duration_seconds: float


class AgentCoordinator:
    """Orchestrates HypothesisAgent → CritiqueAgent → SynthesisAgent pipeline.

    Flow:
    1. Decompose goal into sub-questions (heuristic or LLM via inference_router)
    2. Run HypothesisAgents in parallel (one per sub-question)
    3. Run CritiqueAgents on all hypotheses (parallel)
    4. Run SynthesisAgent across all hypotheses + critiques
    5. Publish coordination lifecycle events to EventBus

    Agents are loosely coupled through the EventBus — each agent publishes
    domain events that can be consumed by external subscribers independently
    of the coordinator's direct calls.
    """

    def __init__(
        self,
        event_bus: RuntimeEventBus,
        hypothesis_agents: list[HypothesisAgent],
        critique_agents: list[CritiqueAgent],
        synthesis_agent: SynthesisAgent,
        inference_router: Any | None = None,
        research_memory: Any | None = None,
        config: CoordinatorConfig | None = None,
    ) -> None:
        self._bus = event_bus
        self._hypothesis_agents = hypothesis_agents
        self._critique_agents = critique_agents
        self._synthesis = synthesis_agent
        self._inference = inference_router
        self._memory = research_memory
        self._config = config or CoordinatorConfig()

    async def coordinate(self, goal: str) -> CoordinatedResult:
        with tracer.start_as_current_span("orchestration.agent_coordinator"):
            start = time.monotonic()
            result = await self._run(goal)
            elapsed = time.monotonic() - start
            runtime_events.labels(event_type="coordination_complete").inc()
            return result.model_copy(update={"duration_seconds": round(elapsed, 4)})

    async def _run(self, goal: str) -> CoordinatedResult:
        session_id = str(uuid.uuid4())
        cfg = self._config

        await self._bus.publish(
            RuntimeEvent(
                topic=TOPIC_COORDINATION_STARTED,
                source_agent_id="coordinator",
                payload={"session_id": session_id, "goal": goal},
            )
        )

        # --- Prior knowledge recall ---
        prior_evidence: list[str] = []
        if self._memory is not None:
            try:
                prior = await self._memory.recall(goal, limit=3)
                prior_evidence = [e.statement for e in prior if e.statement]
            except Exception as exc:
                logger.warning("coordinator_prior_recall_failed", extra={"error": str(exc)})

        sub_questions = await self._plan(goal, cfg.max_sub_questions)

        # --- Phase 1: Parallel hypothesis generation ---
        hypothesis_tasks = []
        for i, question in enumerate(sub_questions):
            agent = self._hypothesis_agents[i % len(self._hypothesis_agents)]
            hypothesis_tasks.append(
                agent.run({
                    "question": question,
                    "generation": 0,
                    "prior_evidence": prior_evidence,
                })
            )

        h_messages = await asyncio.gather(*hypothesis_tasks, return_exceptions=True)
        hypotheses: list[dict[str, Any]] = []
        for msg in h_messages:
            if isinstance(msg, Exception):
                logger.warning(
                    "hypothesis_agent_failed", extra={"error": str(msg)}
                )
                continue
            action = msg.content.get("action", {})
            hyp = action.get("hypothesis", {})
            if hyp:
                hypotheses.append(hyp)

        # --- Phase 2: Parallel critique ---
        critiques: list[dict[str, Any]] = []
        if cfg.run_critique and hypotheses and self._critique_agents:
            critique_tasks = []
            for i, hyp in enumerate(hypotheses):
                agent = self._critique_agents[i % len(self._critique_agents)]
                critique_tasks.append(
                    agent.run({"hypothesis": hyp, "question": goal})
                )
            c_messages = await asyncio.gather(*critique_tasks, return_exceptions=True)
            for msg in c_messages:
                if isinstance(msg, Exception):
                    logger.warning(
                        "critique_agent_failed", extra={"error": str(msg)}
                    )
                    continue
                action = msg.content.get("action", {})
                if action:
                    critiques.append(action)

        # --- Phase 3: Synthesis ---
        s_message = await self._synthesis.run(
            {
                "goal": goal,
                "hypotheses": hypotheses,
                "critiques": critiques,
            }
        )
        synthesis = s_message.content.get("action", {
            "goal": goal,
            "conclusion": "Synthesis unavailable",
            "confidence": 0.0,
        })

        events_published = self._bus.event_count

        await self._bus.publish(
            RuntimeEvent(
                topic=TOPIC_COORDINATION_COMPLETE,
                source_agent_id="coordinator",
                payload={
                    "session_id": session_id,
                    "hypotheses_count": len(hypotheses),
                    "critiques_count": len(critiques),
                },
            )
        )

        return CoordinatedResult(
            session_id=session_id,
            goal=goal,
            sub_questions=sub_questions,
            hypotheses=hypotheses,
            critiques=critiques,
            synthesis=synthesis,
            events_published=self._bus.event_count - events_published + 1,
            duration_seconds=0.0,
        )

    async def _plan(self, goal: str, max_questions: int) -> list[str]:
        if self._inference is not None and self._inference.enabled:
            prompt = (
                f"Break this research goal into exactly {max_questions} specific, "
                f"testable sub-questions. Return only the questions, one per line, "
                f"no numbering or extra text.\nGoal: {goal}"
            )
            output = await self._inference.complete(
                prompt=prompt,
                system="You are a scientific research planner.",
                temperature=0.6,
            )
            if output:
                lines = [ln.strip() for ln in output.strip().splitlines() if ln.strip()]
                if lines:
                    return lines[:max_questions]

        templates = self._config.heuristic_sub_question_templates
        return [t.format(goal=goal) for t in templates[:max_questions]]

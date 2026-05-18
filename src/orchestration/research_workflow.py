import asyncio
import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel

from src.telemetry.runtime_metrics import runtime_events
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


class WorkflowConfig(BaseModel):
    max_sub_questions: int = 3
    run_debate: bool = True
    run_recursive_reasoning: bool = True
    recursive_max_depth: int = 3
    debate_max_rounds: int = 2


class SubQuestionResult(BaseModel):
    sub_question: str
    hypothesis: dict[str, Any]
    quality_score: float


class WorkflowResult(BaseModel):
    workflow_id: str
    goal: str
    sub_questions: list[str]
    sub_results: list[SubQuestionResult]
    primary_hypothesis: dict[str, Any]
    debate_result: dict[str, Any] | None
    recursive_result: dict[str, Any] | None
    synthesis: dict[str, Any]
    duration_seconds: float


class ResearchWorkflow:
    """Autonomous research workflow: plan → parallel research → debate → recursive refinement → synthesis.

    Operates in two modes:
      - Heuristic: generates sub-questions from templates, synthesizes via confidence ranking
      - LLM-augmented: uses inference_router for intelligent decomposition and synthesis
    """

    def __init__(
        self,
        pipeline: Any,
        debate_runtime: Any,
        recursive_loop: Any,
        inference_router: Any | None = None,
        knowledge_graph: Any | None = None,
        research_memory: Any | None = None,
        stream_manager: Any | None = None,
        config: WorkflowConfig | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._debate = debate_runtime
        self._recursive = recursive_loop
        self._inference = inference_router
        self._graph = knowledge_graph
        self._memory = research_memory
        self._stream = stream_manager
        self._config = config or WorkflowConfig()

    async def run(self, goal: str, workflow_id: str | None = None) -> WorkflowResult:
        with tracer.start_as_current_span("orchestration.research_workflow"):
            start = time.monotonic()
            result = await self._execute(goal, workflow_id=workflow_id)
            elapsed = time.monotonic() - start
            runtime_events.labels(event_type="workflow_complete").inc()
            return result.model_copy(update={"duration_seconds": round(elapsed, 4)})

    async def _execute(
        self, goal: str, workflow_id: str | None = None
    ) -> WorkflowResult:
        workflow_id = workflow_id or str(uuid.uuid4())
        cfg = self._config

        if self._stream:
            await self._stream.publish(
                workflow_id,
                {"type": "started", "goal": goal, "workflow_id": workflow_id},
            )

        # --- Prior knowledge recall ---
        prior_context: list[str] = []
        if self._memory is not None:
            try:
                prior = await self._memory.recall(goal, limit=3)
                prior_context = [e.statement for e in prior if e.statement]
                if prior_context and self._stream:
                    await self._stream.publish(
                        workflow_id,
                        {"type": "prior_context", "count": len(prior_context)},
                    )
            except Exception as exc:
                logger.warning("prior_recall_failed", extra={"error": str(exc)})

        # --- Plan ---
        sub_questions = await self._plan(goal, cfg.max_sub_questions, prior_context)

        if self._stream:
            await self._stream.publish(
                workflow_id, {"type": "planning_done", "sub_questions": sub_questions}
            )

        # --- Parallel research on each sub-question ---
        research_tasks = [
            self._pipeline.run({"question": q, "prior_hypotheses": prior_context})
            for q in sub_questions
        ]
        agent_messages = await asyncio.gather(*research_tasks, return_exceptions=True)

        sub_results: list[SubQuestionResult] = []
        for q, result in zip(sub_questions, agent_messages):
            if isinstance(result, Exception):
                logger.warning(
                    "sub_question_failed",
                    extra={"question": q, "error": str(result)},
                )
                continue
            for msg in result:
                action = msg.content.get("action", {})
                sub_results.append(
                    SubQuestionResult(
                        sub_question=q,
                        hypothesis=action.get("hypothesis", {}),
                        quality_score=float(action.get("quality_score", 0.0)),
                    )
                )

        if not sub_results:
            return self._empty_result(workflow_id, goal, sub_questions)

        # --- Select primary hypothesis (highest quality) ---
        primary_result = max(sub_results, key=lambda r: r.quality_score)
        primary_hypothesis = primary_result.hypothesis

        # --- Optional: Debate ---
        debate_result = None
        if cfg.run_debate and primary_hypothesis.get("statement"):
            try:
                dr = await self._debate.debate(
                    hypothesis=primary_hypothesis["statement"],
                    max_rounds=cfg.debate_max_rounds,
                )
                debate_result = dr.model_dump()
            except Exception as exc:
                logger.warning("debate_failed", extra={"error": str(exc)})

        # --- Optional: Recursive reasoning ---
        recursive_result = None
        if cfg.run_recursive_reasoning and primary_hypothesis:
            try:
                from src.research.hypothesis_evolution import Hypothesis

                h = Hypothesis(
                    id=str(uuid.uuid4()),
                    statement=primary_hypothesis.get(
                        "statement", f"Hypothesis for: {goal}"
                    ),
                    confidence=primary_hypothesis.get("confidence", 0.5),
                    evidence=primary_hypothesis.get("evidence", []),
                    generation=primary_hypothesis.get("generation", 0),
                )
                from src.reasoning.recursive_loop import RecursiveConfig

                self._recursive._config = RecursiveConfig(
                    max_depth=cfg.recursive_max_depth
                )
                rr = await self._recursive.run(h, question=goal)
                recursive_result = rr.model_dump()
                # Update primary with recursively refined hypothesis
                primary_hypothesis = rr.final_hypothesis.model_dump()
            except Exception as exc:
                logger.warning("recursive_reasoning_failed", extra={"error": str(exc)})

        # --- Optional: Knowledge graph storage ---
        if self._graph and primary_hypothesis.get("id"):
            try:
                await self._graph.store_hypothesis(
                    hypothesis_id=primary_hypothesis["id"],
                    statement=primary_hypothesis.get("statement", ""),
                    confidence=primary_hypothesis.get("confidence", 0.0),
                    generation=primary_hypothesis.get("generation", 0),
                    task_id=workflow_id,
                )
            except Exception as exc:
                logger.warning("graph_store_failed", extra={"error": str(exc)})

        synthesis = await self._synthesize(goal, sub_results, primary_hypothesis)

        # --- Store synthesis to cross-session memory ---
        if self._memory is not None:
            try:
                from src.memory.research_memory import MemoryEntry

                await self._memory.store(
                    MemoryEntry(
                        topic=goal,
                        statement=synthesis.get("conclusion", ""),
                        confidence=synthesis.get("primary_confidence", 0.0),
                        source="workflow",
                        session_id=workflow_id,
                        evidence=list(
                            set(
                                e
                                for r in sub_results
                                for e in r.hypothesis.get("evidence", [])
                            )
                        ),
                    )
                )
            except Exception as exc:
                logger.warning("memory_store_failed", extra={"error": str(exc)})

        if self._stream:
            await self._stream.publish(
                workflow_id,
                {
                    "type": "synthesis_done",
                    "conclusion": synthesis.get("conclusion", ""),
                },
            )
            await self._stream.close(workflow_id)

        return WorkflowResult(
            workflow_id=workflow_id,
            goal=goal,
            sub_questions=sub_questions,
            sub_results=sub_results,
            primary_hypothesis=primary_hypothesis,
            debate_result=debate_result,
            recursive_result=recursive_result,
            synthesis=synthesis,
            duration_seconds=0.0,
        )

    async def _plan(
        self, goal: str, max_questions: int, prior_context: list[str] | None = None
    ) -> list[str]:
        if self._inference is not None and self._inference.enabled:
            prior_str = ""
            if prior_context:
                prior_str = "\n\nPrior research context:\n" + "\n".join(
                    f"- {s}" for s in prior_context[:3]
                )
            prompt = (
                f"Break this research goal into exactly {max_questions} specific, "
                f"testable sub-questions. Return only the questions, one per line, "
                f"no numbering or extra text.\nGoal: {goal}{prior_str}"
            )
            output = await self._inference.complete(
                prompt=prompt,
                system="You are a scientific research planner.",
                temperature=0.6,
            )
            if output:
                lines = [
                    line.strip() for line in output.strip().splitlines() if line.strip()
                ]
                if lines:
                    return lines[:max_questions]
        return self._heuristic_sub_questions(goal, max_questions)

    @staticmethod
    def _heuristic_sub_questions(goal: str, n: int) -> list[str]:
        templates = [
            f"What mechanisms explain: {goal}?",
            f"What evidence supports or refutes: {goal}?",
            f"What are boundary conditions or limitations of: {goal}?",
        ]
        return templates[:n]

    async def _synthesize(
        self,
        goal: str,
        sub_results: list[SubQuestionResult],
        primary: dict[str, Any],
    ) -> dict[str, Any]:
        all_evidence: list[str] = []
        all_suggestions: list[str] = []
        for r in sub_results:
            all_evidence.extend(r.hypothesis.get("evidence", []))

        if self._inference is not None and self._inference.enabled:
            hypotheses_text = "\n".join(
                f"- {r.hypothesis.get('statement', '')} (confidence={r.quality_score:.2f})"
                for r in sub_results
            )
            prompt = (
                f"Synthesize these research findings into a single coherent conclusion "
                f"for the goal: {goal}\n\nFindings:\n{hypotheses_text}"
            )
            synthesis_text = await self._inference.complete(
                prompt=prompt,
                system="You are a scientific synthesis expert. Be concise and evidence-based.",
            )
            conclusion = synthesis_text or primary.get("statement", goal)
        else:
            conclusion = primary.get("statement", f"Synthesized finding for: {goal}")

        return {
            "goal": goal,
            "conclusion": conclusion,
            "primary_confidence": primary.get("confidence", 0.0),
            "evidence_count": len(set(all_evidence)),
            "sub_questions_researched": len(sub_results),
            "suggestions": all_suggestions[:5],
        }

    @staticmethod
    def _empty_result(
        workflow_id: str, goal: str, sub_questions: list[str]
    ) -> WorkflowResult:
        return WorkflowResult(
            workflow_id=workflow_id,
            goal=goal,
            sub_questions=sub_questions,
            sub_results=[],
            primary_hypothesis={},
            debate_result=None,
            recursive_result=None,
            synthesis={
                "goal": goal,
                "conclusion": "No results produced",
                "error": True,
            },
            duration_seconds=0.0,
        )

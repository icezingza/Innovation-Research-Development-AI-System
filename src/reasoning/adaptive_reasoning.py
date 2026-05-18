import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AdaptiveReasoningEngine:
    """
    ASI Feature: Adaptive Reasoning Adaption
    Dynamically adjusts the reasoning strategy and cognitive depth based on task complexity.
    Saves processing resources on simple tasks, and deploys full multi-agent DebateRuntime for complex ones.
    """

    def __init__(self, inference_router=None):
        self.inference_router = inference_router
        self._strategy_cache = {}

    def _heuristic_complexity_check(self, task_description: str) -> int:
        """Fallback rule-based complexity scoring if inference is unavailable."""
        complexity = 1
        keywords_hard = [
            "synthesize",
            "debate",
            "compare",
            "analyze",
            "strategy",
            "architecture",
        ]
        keywords_medium = ["summarize", "extract", "format", "translate"]

        lower_task = task_description.lower()
        if any(k in lower_task for k in keywords_hard):
            complexity += 6
        elif any(k in lower_task for k in keywords_medium):
            complexity += 3

        if len(lower_task) > 500:
            complexity += 2

        return min(complexity, 10)

    async def evaluate_task_complexity(self, task_description: str) -> Dict[str, Any]:
        """
        Evaluate task complexity (1-10) to determine the best reasoning strategy.
        """
        complexity_score = self._heuristic_complexity_check(task_description)

        # In a fully connected mode, we might ask the InferenceRouter for a meta-score
        # But for ultra-fast latency, heuristic evaluation is preferred first.

        strategy = "heuristic"
        tier = "fast"
        agents_required = 1

        if complexity_score > 7:
            strategy = "bayesian_debate"
            tier = "deep"
            agents_required = 3
        elif complexity_score > 3:
            strategy = "chain_of_thought"
            tier = "balanced"
            agents_required = 1

        logger.info(
            "adaptive_reasoning_evaluated",
            extra={
                "complexity_score": complexity_score,
                "strategy": strategy,
                "tier": tier,
            },
        )

        return {
            "complexity_score": complexity_score,
            "strategy": strategy,
            "inference_tier": tier,
            "agents_required": agents_required,
            "allocated_tokens": complexity_score * 500,
        }

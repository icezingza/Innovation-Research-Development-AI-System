"""Adaptive configuration manager for self-improving cognition.

Reads QualityTracker analysis to auto-tune RecursiveConfig max_depth
and WorkflowConfig parameters, closing the feedback loop between
observed reasoning quality and runtime configuration.
"""
import logging
import time
from typing import Any

from pydantic import BaseModel

from src.orchestration.research_workflow import WorkflowConfig
from src.reasoning.quality_tracker import QualityTracker
from src.reasoning.recursive_loop import RecursiveConfig

logger = logging.getLogger(__name__)

_MIN_DEPTH = 2
_MAX_DEPTH = 8
_MIN_SUB_QUESTIONS = 2
_MAX_SUB_QUESTIONS = 6


class ConfigSnapshot(BaseModel):
    timestamp: float
    recursive_max_depth: int
    workflow_max_sub_questions: int
    workflow_run_debate: bool
    workflow_run_recursive: bool
    trigger_trend: str
    recommendation: str


class AdaptiveConfigManager:
    """Monitors QualityTracker trends and adjusts runtime configs in-place.

    Applies conservative adjustments: ±1 depth per cycle, bounded by
    _MIN_DEPTH and _MAX_DEPTH to prevent runaway recursion or starvation.
    """

    def __init__(
        self,
        quality_tracker: QualityTracker,
        recursive_config: RecursiveConfig | None = None,
        workflow_config: WorkflowConfig | None = None,
    ) -> None:
        self._tracker = quality_tracker
        self.recursive_config = recursive_config or RecursiveConfig()
        self.workflow_config = workflow_config or WorkflowConfig()
        self._history: list[ConfigSnapshot] = []
        self._cycle_count = 0

    async def optimize(self) -> ConfigSnapshot:
        """Run one optimization cycle and return the resulting snapshot."""
        self._cycle_count += 1
        report = await self._tracker.analyze()

        dominant_trend = self._dominant_trend(report.operations)
        recommendation = report.recommendation

        self._apply_adjustments(dominant_trend)

        snapshot = ConfigSnapshot(
            timestamp=time.time(),
            recursive_max_depth=self.recursive_config.max_depth,
            workflow_max_sub_questions=self.workflow_config.max_sub_questions,
            workflow_run_debate=self.workflow_config.run_debate,
            workflow_run_recursive=self.workflow_config.run_recursive_reasoning,
            trigger_trend=dominant_trend,
            recommendation=recommendation,
        )
        self._history.append(snapshot)
        logger.info(
            "adaptive_config_optimized",
            extra={
                "cycle": self._cycle_count,
                "trend": dominant_trend,
                "max_depth": self.recursive_config.max_depth,
                "sub_questions": self.workflow_config.max_sub_questions,
            },
        )
        return snapshot

    def _dominant_trend(self, operations: list[Any]) -> str:
        if not operations:
            return "insufficient_data"
        trends = [op.trend for op in operations]
        if trends.count("improving") >= len(trends) / 2:
            return "improving"
        if trends.count("declining") >= len(trends) / 2:
            return "declining"
        return "stable"

    def _apply_adjustments(self, trend: str) -> None:
        if trend == "declining":
            # Reduce complexity to avoid degrading quality further
            new_depth = max(_MIN_DEPTH, self.recursive_config.max_depth - 1)
            new_sub = max(_MIN_SUB_QUESTIONS, self.workflow_config.max_sub_questions - 1)
            self.recursive_config = RecursiveConfig(
                max_depth=new_depth,
                convergence_threshold=self.recursive_config.convergence_threshold,
                min_improvement=self.recursive_config.min_improvement,
            )
            self.workflow_config = WorkflowConfig(
                max_sub_questions=new_sub,
                run_debate=self.workflow_config.run_debate,
                run_recursive_reasoning=self.workflow_config.run_recursive_reasoning,
                recursive_max_depth=new_depth,
                debate_max_rounds=self.workflow_config.debate_max_rounds,
            )
        elif trend == "improving":
            # Gradually increase depth to exploit quality headroom
            new_depth = min(_MAX_DEPTH, self.recursive_config.max_depth + 1)
            new_sub = min(_MAX_SUB_QUESTIONS, self.workflow_config.max_sub_questions + 1)
            self.recursive_config = RecursiveConfig(
                max_depth=new_depth,
                convergence_threshold=self.recursive_config.convergence_threshold,
                min_improvement=self.recursive_config.min_improvement,
            )
            self.workflow_config = WorkflowConfig(
                max_sub_questions=new_sub,
                run_debate=self.workflow_config.run_debate,
                run_recursive_reasoning=self.workflow_config.run_recursive_reasoning,
                recursive_max_depth=new_depth,
                debate_max_rounds=self.workflow_config.debate_max_rounds,
            )

    def history(self) -> list[ConfigSnapshot]:
        return list(self._history)

    def current_snapshot(self) -> dict[str, Any]:
        return {
            "recursive_max_depth": self.recursive_config.max_depth,
            "workflow_max_sub_questions": self.workflow_config.max_sub_questions,
            "workflow_run_debate": self.workflow_config.run_debate,
            "workflow_run_recursive": self.workflow_config.run_recursive_reasoning,
            "cycle_count": self._cycle_count,
        }

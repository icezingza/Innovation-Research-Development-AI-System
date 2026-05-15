import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_MIN_SAMPLES_FOR_TREND = 4


class OperationQuality(BaseModel):
    operation: str
    avg_quality: float
    min_quality: float
    max_quality: float
    sample_count: int
    trend: str  # "improving" | "stable" | "declining" | "insufficient_data"


class QualityReport(BaseModel):
    total_entries_analyzed: int
    operations: list[OperationQuality]
    overall_avg_quality: float
    recommendation: str


class QualityTracker:
    """Analyzes ReasoningTrace entries to surface quality trends and tuning hints.

    Reads recent trace entries, groups by operation, computes descriptive
    statistics, and detects simple linear trend (first vs second half avg).
    Produces a QualityReport with a plain-language recommendation.
    """

    def __init__(self, reasoning_trace: Any) -> None:
        self._trace = reasoning_trace

    async def analyze(self, limit: int = 200) -> QualityReport:
        entries = await self._trace.get_recent(limit=limit)

        ops: dict[str, list[float]] = {}
        for entry in entries:
            op = entry.operation
            duration = entry.duration_seconds
            if duration > 0:
                ops.setdefault(op, []).append(duration)

        if not ops:
            return QualityReport(
                total_entries_analyzed=0,
                operations=[],
                overall_avg_quality=0.0,
                recommendation="No trace data available yet.",
            )

        operation_results: list[OperationQuality] = []
        all_durations: list[float] = []

        for op, durations in ops.items():
            all_durations.extend(durations)
            trend = self._detect_trend(durations)
            operation_results.append(
                OperationQuality(
                    operation=op,
                    avg_quality=round(sum(durations) / len(durations), 4),
                    min_quality=round(min(durations), 4),
                    max_quality=round(max(durations), 4),
                    sample_count=len(durations),
                    trend=trend,
                )
            )

        operation_results.sort(key=lambda o: o.avg_quality, reverse=True)
        overall = round(sum(all_durations) / len(all_durations), 4)
        recommendation = self._recommend(operation_results)

        return QualityReport(
            total_entries_analyzed=len(entries),
            operations=operation_results,
            overall_avg_quality=overall,
            recommendation=recommendation,
        )

    @staticmethod
    def _detect_trend(values: list[float]) -> str:
        if len(values) < _MIN_SAMPLES_FOR_TREND:
            return "insufficient_data"
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        delta = second_half - first_half
        threshold = first_half * 0.05  # 5% change threshold
        if delta > threshold:
            return "declining"  # higher duration = slower = declining perf
        if delta < -threshold:
            return "improving"
        return "stable"

    @staticmethod
    def _recommend(operations: list[OperationQuality]) -> str:
        declining = [o for o in operations if o.trend == "declining"]
        if not operations:
            return "No operations tracked yet."
        if declining:
            names = ", ".join(o.operation for o in declining[:3])
            return (
                f"Operations showing performance decline: {names}. "
                "Consider reducing recursive depth or debate rounds."
            )
        improving = [o for o in operations if o.trend == "improving"]
        if improving:
            return (
                "System performance is improving. "
                "Safe to increase max_depth or max_sub_questions for richer results."
            )
        return "Performance is stable. Current configuration is well-balanced."

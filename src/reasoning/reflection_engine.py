import time
from typing import Any

from pydantic import BaseModel

from src.telemetry.runtime_metrics import reasoning_latency
from src.telemetry.tracing import tracer


class ReflectionResult(BaseModel):
    original: dict[str, Any]
    quality_score: float
    gaps: list[str]
    strengths: list[str]
    suggestions: list[str]


class ReflectionEngine:
    """Analyzes reasoning quality and identifies structural gaps."""

    _REQUIRED_FIELDS = ("evidence", "conclusion")
    _QUALITY_FIELDS = ("confidence", "assumptions", "alternatives", "caveats")

    async def reflect(self, reasoning: dict[str, Any]) -> ReflectionResult:
        with tracer.start_as_current_span("reasoning.reflect"):
            start = time.monotonic()
            result = self._analyze(reasoning)
            reasoning_latency.observe(time.monotonic() - start)
            return result

    def _analyze(self, reasoning: dict[str, Any]) -> ReflectionResult:
        gaps = self._detect_gaps(reasoning)
        strengths = self._detect_strengths(reasoning)
        quality = self._score_quality(gaps, strengths)
        suggestions = [f"Address gap: {g}" for g in gaps] + [
            f"Consider adding: {f}"
            for f in self._QUALITY_FIELDS
            if not reasoning.get(f)
        ]
        return ReflectionResult(
            original=reasoning,
            quality_score=quality,
            gaps=gaps,
            strengths=strengths,
            suggestions=suggestions[:5],
        )

    def _detect_gaps(self, reasoning: dict[str, Any]) -> list[str]:
        return [
            f"Missing required field: '{field}'"
            for field in self._REQUIRED_FIELDS
            if not reasoning.get(field)
        ]

    def _detect_strengths(self, reasoning: dict[str, Any]) -> list[str]:
        strengths = []
        if reasoning.get("evidence"):
            strengths.append("Evidence-backed claims")
        if reasoning.get("conclusion"):
            strengths.append("Clear conclusion")
        if reasoning.get("confidence") is not None:
            strengths.append("Explicit confidence scoring")
        if reasoning.get("alternatives"):
            strengths.append("Alternative hypotheses considered")
        return strengths

    def _score_quality(self, gaps: list[str], strengths: list[str]) -> float:
        total = len(gaps) + len(strengths)
        if total == 0:
            return 0.5
        return round(len(strengths) / total, 2)

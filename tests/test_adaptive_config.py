"""Tests for AdaptiveConfigManager self-improvement loop."""

import pytest

from src.reasoning.adaptive_config import AdaptiveConfigManager, _MAX_DEPTH, _MIN_DEPTH
from src.reasoning.quality_tracker import QualityReport, QualityTracker


def _make_tracker_with_trend(trend: str) -> QualityTracker:
    """Return a QualityTracker whose analyze() returns a fixed trend."""
    from unittest.mock import AsyncMock, MagicMock
    from src.reasoning.quality_tracker import OperationQuality

    tracker = MagicMock(spec=QualityTracker)
    op = OperationQuality(
        operation="reasoning",
        avg_quality=0.7,
        min_quality=0.5,
        max_quality=0.9,
        sample_count=10,
        trend=trend,
    )
    report = QualityReport(
        operations=[op],
        total_entries_analyzed=10,
        overall_avg_quality=0.7,
        recommendation="increase depth" if trend == "improving" else "reduce depth",
    )
    tracker.analyze = AsyncMock(return_value=report)
    return tracker


class TestAdaptiveConfigManager:
    @pytest.mark.asyncio
    async def test_returns_snapshot(self) -> None:
        mgr = AdaptiveConfigManager(_make_tracker_with_trend("stable"))
        snap = await mgr.optimize()
        assert snap.trigger_trend == "stable"
        assert snap.recursive_max_depth >= _MIN_DEPTH

    @pytest.mark.asyncio
    async def test_declining_reduces_depth(self) -> None:
        from src.reasoning.recursive_loop import RecursiveConfig

        mgr = AdaptiveConfigManager(
            _make_tracker_with_trend("declining"),
            recursive_config=RecursiveConfig(max_depth=5),
        )
        await mgr.optimize()
        assert mgr.recursive_config.max_depth == 4

    @pytest.mark.asyncio
    async def test_improving_increases_depth(self) -> None:
        from src.reasoning.recursive_loop import RecursiveConfig

        mgr = AdaptiveConfigManager(
            _make_tracker_with_trend("improving"),
            recursive_config=RecursiveConfig(max_depth=3),
        )
        await mgr.optimize()
        assert mgr.recursive_config.max_depth == 4

    @pytest.mark.asyncio
    async def test_stable_does_not_change_depth(self) -> None:
        from src.reasoning.recursive_loop import RecursiveConfig

        mgr = AdaptiveConfigManager(
            _make_tracker_with_trend("stable"),
            recursive_config=RecursiveConfig(max_depth=4),
        )
        await mgr.optimize()
        assert mgr.recursive_config.max_depth == 4

    @pytest.mark.asyncio
    async def test_depth_clamped_at_min(self) -> None:
        from src.reasoning.recursive_loop import RecursiveConfig

        mgr = AdaptiveConfigManager(
            _make_tracker_with_trend("declining"),
            recursive_config=RecursiveConfig(max_depth=_MIN_DEPTH),
        )
        await mgr.optimize()
        assert mgr.recursive_config.max_depth == _MIN_DEPTH

    @pytest.mark.asyncio
    async def test_depth_clamped_at_max(self) -> None:
        from src.reasoning.recursive_loop import RecursiveConfig

        mgr = AdaptiveConfigManager(
            _make_tracker_with_trend("improving"),
            recursive_config=RecursiveConfig(max_depth=_MAX_DEPTH),
        )
        await mgr.optimize()
        assert mgr.recursive_config.max_depth == _MAX_DEPTH

    @pytest.mark.asyncio
    async def test_history_accumulates(self) -> None:
        mgr = AdaptiveConfigManager(_make_tracker_with_trend("stable"))
        await mgr.optimize()
        await mgr.optimize()
        assert len(mgr.history()) == 2

    @pytest.mark.asyncio
    async def test_current_snapshot(self) -> None:
        mgr = AdaptiveConfigManager(_make_tracker_with_trend("stable"))
        snap = mgr.current_snapshot()
        assert "recursive_max_depth" in snap
        assert snap["cycle_count"] == 0
        await mgr.optimize()
        assert mgr.current_snapshot()["cycle_count"] == 1

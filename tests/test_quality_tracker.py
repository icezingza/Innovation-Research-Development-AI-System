from unittest.mock import AsyncMock

import pytest

from src.reasoning.quality_tracker import QualityTracker
from src.reasoning.reasoning_trace import TraceEntry


def _entry(operation: str, duration: float) -> TraceEntry:
    return TraceEntry(
        operation=operation,
        input_hash="abc12345",
        output_summary="test",
        duration_seconds=duration,
    )


def _mock_trace(entries: list[TraceEntry]):
    trace = AsyncMock()
    trace.get_recent = AsyncMock(return_value=entries)
    return trace


@pytest.mark.asyncio
async def test_quality_tracker_empty_trace():
    tracker = QualityTracker(reasoning_trace=_mock_trace([]))
    report = await tracker.analyze()
    assert report.total_entries_analyzed == 0
    assert report.overall_avg_quality == 0.0
    assert report.operations == []


@pytest.mark.asyncio
async def test_quality_tracker_groups_by_operation():
    entries = [
        _entry("recursive_evolution", 0.1),
        _entry("recursive_evolution", 0.2),
        _entry("reflection", 0.05),
    ]
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    ops = {o.operation: o for o in report.operations}
    assert "recursive_evolution" in ops
    assert "reflection" in ops
    assert ops["recursive_evolution"].sample_count == 2


@pytest.mark.asyncio
async def test_quality_tracker_computes_avg():
    entries = [_entry("op", 0.1), _entry("op", 0.3)]
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert abs(report.operations[0].avg_quality - 0.2) < 0.001


@pytest.mark.asyncio
async def test_quality_tracker_detects_stable_trend():
    entries = [_entry("op", 0.1)] * 8
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert report.operations[0].trend == "stable"


@pytest.mark.asyncio
async def test_quality_tracker_detects_declining():
    # Second half is significantly slower
    entries = [_entry("op", 0.1)] * 4 + [_entry("op", 0.5)] * 4
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert report.operations[0].trend == "declining"


@pytest.mark.asyncio
async def test_quality_tracker_detects_improving():
    # Second half is significantly faster
    entries = [_entry("op", 0.5)] * 4 + [_entry("op", 0.1)] * 4
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert report.operations[0].trend == "improving"


@pytest.mark.asyncio
async def test_quality_tracker_insufficient_data_trend():
    entries = [_entry("op", 0.1), _entry("op", 0.2)]
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert report.operations[0].trend == "insufficient_data"


@pytest.mark.asyncio
async def test_quality_tracker_recommendation_non_empty():
    entries = [_entry("op", 0.1)] * 6
    tracker = QualityTracker(reasoning_trace=_mock_trace(entries))
    report = await tracker.analyze()
    assert isinstance(report.recommendation, str)
    assert len(report.recommendation) > 0

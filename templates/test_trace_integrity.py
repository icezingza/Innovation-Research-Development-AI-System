"""Dimension 3: Cognitive & Reasoning Integrity (Intelligence Level)

ตรวจสอบว่า ReasoningTrace บันทึกขั้นตอนถูกต้อง และ QualityTracker
ตรวจจับแนวโน้มประสิทธิภาพ (improving / declining / stable) ได้จริง
"""
import pytest

from src.reasoning.quality_tracker import QualityTracker
from src.reasoning.reasoning_trace import ReasoningTrace, TraceEntry


def _entry(operation: str, duration: float) -> TraceEntry:
    return TraceEntry(
        operation=operation,
        input_hash=ReasoningTrace.hash_input({"op": operation, "d": duration}),
        output_summary=f"{operation} completed",
        agent_id="TestAgent",
        duration_seconds=duration,
    )


@pytest.mark.asyncio
async def test_reasoning_trace_records_steps():
    """ร่องรอยทางปัญญา (ReasoningTrace) บันทึก steps และ recall ได้ถูกต้อง"""
    trace = ReasoningTrace()

    await trace.record(_entry("hypothesis", 0.5))
    await trace.record(_entry("critique", 0.6))

    recent = await trace.get_recent()
    assert len(recent) == 2
    assert recent[0].operation == "hypothesis"
    assert recent[1].operation == "critique"
    assert recent[1].duration_seconds == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_quality_tracker_detects_declining_trend():
    """QualityTracker ตรวจจับ trend = 'declining' เมื่อ duration เพิ่มขึ้นต่อเนื่อง

    declining หมาย: second-half avg > first-half avg by >5%
    ต้องการอย่างน้อย 4 samples (_MIN_SAMPLES_FOR_TREND)
    """
    trace = ReasoningTrace()

    # 4 entries: duration เพิ่มขึ้น — first half avg 0.10s, second half avg 0.30s → +200%
    for duration in [0.10, 0.10, 0.30, 0.30]:
        await trace.record(_entry("reasoning", duration))

    tracker = QualityTracker(reasoning_trace=trace)
    report = await tracker.analyze()

    assert report.total_entries_analyzed == 4
    reasoning_op = next(o for o in report.operations if o.operation == "reasoning")
    assert reasoning_op.trend == "declining", (
        f"Expected 'declining', got '{reasoning_op.trend}'"
    )


@pytest.mark.asyncio
async def test_quality_tracker_detects_improving_trend():
    """QualityTracker ตรวจจับ trend = 'improving' เมื่อ duration ลดลงต่อเนื่อง"""
    trace = ReasoningTrace()

    # first half avg 0.50s, second half avg 0.10s → improving
    for duration in [0.50, 0.50, 0.10, 0.10]:
        await trace.record(_entry("synthesis", duration))

    tracker = QualityTracker(reasoning_trace=trace)
    report = await tracker.analyze()

    synthesis_op = next(o for o in report.operations if o.operation == "synthesis")
    assert synthesis_op.trend == "improving"


@pytest.mark.asyncio
async def test_quality_tracker_insufficient_data():
    """น้อยกว่า 4 samples ต้องได้ trend = 'insufficient_data'"""
    trace = ReasoningTrace()

    for duration in [0.5, 0.6, 0.7]:  # 3 samples — below threshold
        await trace.record(_entry("debate", duration))

    tracker = QualityTracker(reasoning_trace=trace)
    report = await tracker.analyze()

    debate_op = next(o for o in report.operations if o.operation == "debate")
    assert debate_op.trend == "insufficient_data"


@pytest.mark.asyncio
async def test_quality_tracker_empty_trace():
    """ไม่มี trace data ต้องคืน QualityReport ที่ว่าง (ไม่ crash)"""
    trace = ReasoningTrace()
    tracker = QualityTracker(reasoning_trace=trace)
    report = await tracker.analyze()

    assert report.total_entries_analyzed == 0
    assert report.operations == []
    assert "No trace data" in report.recommendation

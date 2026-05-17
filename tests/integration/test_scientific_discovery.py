import pytest
from unittest.mock import AsyncMock
from src.orchestration.scientific_discovery_engine import (
    ScientificDiscoveryEngine,
    DiscoveryTask,
)
from src.orchestration.agent_coordinator import CoordinatedResult


@pytest.mark.asyncio
async def test_scientific_discovery_engine_loop():
    """ทดสอบการทำงานของ ScientificDiscoveryEngine ในการรันลูปวิจัย 2 รอบ"""

    # 1. Mock Dependencies
    mock_coordinator = AsyncMock()
    # Mock ผลลัพธ์จาก Coordinator
    mock_coordinator.coordinate.return_value = CoordinatedResult(
        session_id="test-session",
        goal="วิจัย Empathy",
        hypotheses=[{"statement": "Hypothesis 1"}],
        critiques=[{"critique": "Good"}],
        synthesis={
            "conclusion": "AI Empathy is possible",
            "next_research_question": "How to scale?",
        },
    )

    mock_event_bus = AsyncMock()

    # 2. สร้าง Engine
    engine = ScientificDiscoveryEngine(
        coordinator=mock_coordinator, event_bus=mock_event_bus
    )

    # 3. สร้าง Task
    task = DiscoveryTask(
        task_id="test-task", scientific_goal="วิจัย Empathy", domain="AI", iterations=2
    )

    # 4. รันลูปวิจัย
    result = await engine.execute_discovery_loop(task)

    # 5. ตรวจสอบผลลัพธ์
    assert result["task_id"] == "test-task"
    assert len(result["history"]) == 2  # ต้องรันครบ 2 รอบ
    assert mock_coordinator.coordinate.call_count == 2

    print(
        f"\n✅ [PASS] การทดสอบลูปวิจัยอัตโนมัติสำเร็จ! (รอบการทดสอบ: {len(result['history'])})"
    )

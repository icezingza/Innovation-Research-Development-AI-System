import pytest
from unittest.mock import AsyncMock
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.governance.policy_enforcer import PolicyDecision, PolicyEnforcer, PolicyResult
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_policy_bypass_blocked_stage():
    """จำลองสถานการณ์ที่สเตจถูกบล็อกโดย PolicyEnforcer"""

    # 1. สร้าง Mock PolicyEnforcer ที่บล็อกทุกอย่าง
    mock_policy = MagicMock(spec=PolicyEnforcer)
    mock_policy.evaluate = AsyncMock(
        return_value=PolicyResult(
            decision=PolicyDecision.DENY,
            reason="Bypassing safety protocols",
            message_id="test-id",
        )
    )

    # 2. สร้าง Pipeline พร้อมนโยบายที่บล็อก
    pipeline = CognitivePipeline(agents={}, policy_enforcer=mock_policy)

    # 3. เตรียม Context
    context = {"session_id": "bypass-test-123"}

    # 4. ทดสอบว่าสเตจแรก (semantic_understanding) จะต้องถูกบล็อก
    with pytest.raises(
        PermissionError, match="Stage semantic_understanding blocked by policy."
    ):
        await pipeline.process(context)

    # ยืนยันว่า Policy ถูกเรียกตรวจสอบจริง
    mock_policy.evaluate.assert_called()
    print("\n✅ [PASS] ระบบสามารถบล็อกการเข้าถึงสเตจที่ผิดนโยบายได้อย่างถูกต้อง!")


@pytest.mark.asyncio
async def test_policy_allows_execution():
    """จำลองสถานการณ์ที่นโยบายอนุญาตการทำงานปกติ"""

    # 1. สร้าง Mock PolicyEnforcer ที่อนุญาตทุกอย่าง
    mock_policy = MagicMock(spec=PolicyEnforcer)
    mock_policy.evaluate = AsyncMock(
        return_value=PolicyResult(
            decision=PolicyDecision.ALLOW, reason="Allowed", message_id="test-id"
        )
    )

    # 2. สร้าง Pipeline พร้อม Agent ที่ mock มา
    mock_agent = AsyncMock()
    mock_agent.run.return_value = type("obj", (object,), {"content": "result"})

    pipeline = CognitivePipeline(
        agents={"semantic": mock_agent, "reasoning": mock_agent},
        policy_enforcer=mock_policy,
    )

    context = {"session_id": "allow-test-123"}

    # 3. รัน Pipeline
    result = await pipeline.process(context)

    # 4. ยืนยันว่าผลลัพธ์ผ่าน และได้ข้อมูลครบ
    assert "semantic_output" in result
    assert result["semantic_output"] == "result"
    print("\n✅ [PASS] ระบบอนุญาตให้ทำงานตามนโยบายปกติได้สำเร็จ!")

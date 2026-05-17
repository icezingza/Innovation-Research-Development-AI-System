import pytest
from src.governance.policy_enforcer import PolicyDecision, PolicyEnforcer
from src.protocols.agent_message import AgentMessage, MessageType


def _make_message(sender_id: str, text: str) -> AgentMessage:
    return AgentMessage(
        sender_id=sender_id,
        message_type=MessageType.REASONING,
        content={"text": text},
    )


@pytest.mark.asyncio
async def test_pdpa_blocking_logic():
    """ทดสอบว่าระบบต้อง Block ข้อมูลเลขบัตรประชาชนไทย (PII)"""
    enforcer = PolicyEnforcer()

    message = _make_message(
        sender_id="TestAgent",
        text="วิเคราะห์พฤติกรรมของลูกค้าเลขบัตร 1-2345-67890-12-3",
    )
    result = await enforcer.evaluate(message)

    assert result.decision == PolicyDecision.DENY
    assert "PDPA-001" in result.reason
    print(f"Successfully blocked PII: {result.reason}")


@pytest.mark.asyncio
async def test_financial_advice_guardrail():
    """ทดสอบการ Block คำแนะนำการลงทุนที่ไม่ได้รับอนุญาต"""
    enforcer = PolicyEnforcer()

    message = _make_message(
        sender_id="Agent",
        text="แนะนำให้ซื้อหุ้น DELTA วันนี้เลยครับ",
    )
    result = await enforcer.evaluate(message)

    assert result.decision == PolicyDecision.DENY
    assert "FIN-001" in result.reason
    print(f"Successfully blocked financial advice: {result.reason}")

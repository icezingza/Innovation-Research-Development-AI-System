import pytest

from src.governance.policy_enforcer import (
    PolicyDecision,
    PolicyEnforcer,
    PolicyViolationError,
)
from src.protocols.agent_message import AgentMessage, MessageType


def _make_message(content: dict, sender_id: str = "agent-1") -> AgentMessage:
    return AgentMessage(
        sender_id=sender_id,
        message_type=MessageType.ACTION,
        content=content,
    )


@pytest.mark.asyncio
async def test_policy_enforcer_allows_valid_message():
    enforcer = PolicyEnforcer()
    msg = _make_message({"action": "analyze", "result": "ok"})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.ALLOW


@pytest.mark.asyncio
async def test_policy_enforcer_denies_oversized_content():
    enforcer = PolicyEnforcer(max_content_bytes=10)
    msg = _make_message({"data": "x" * 1000})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.DENY
    assert "exceeds limit" in result.reason


@pytest.mark.asyncio
async def test_policy_enforcer_raises_on_enforce_deny():
    enforcer = PolicyEnforcer(max_content_bytes=10)
    msg = _make_message({"data": "x" * 1000})
    with pytest.raises(PolicyViolationError):
        await enforcer.enforce(msg)


@pytest.mark.asyncio
async def test_policy_enforcer_denies_empty_sender():
    enforcer = PolicyEnforcer()
    msg = AgentMessage(
        sender_id="",
        message_type=MessageType.ACTION,
        content={"result": "ok"},
    )
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.DENY


@pytest.mark.asyncio
async def test_policy_enforcer_blocks_thai_pdpa_violation():
    enforcer = PolicyEnforcer()
    # Thai citizen ID 13 digits
    msg = _make_message({"text": "บัตรของผมเลขที่ 1234567890123 ครับ"})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.DENY
    assert "Regulatory violation" in result.reason
    assert "PDPA-001" in result.reason


@pytest.mark.asyncio
async def test_policy_enforcer_blocks_thai_finance_violation():
    enforcer = PolicyEnforcer()
    msg = _make_message({"advice": "ผมแนะนำให้ซื้อหุ้นตัวนี้ครับ รับประกันผลตอบแทนสูง"})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.DENY
    assert "Regulatory violation" in result.reason
    assert "FIN-001" in result.reason


@pytest.mark.asyncio
async def test_policy_enforcer_allows_normal_thai_text():
    enforcer = PolicyEnforcer()
    msg = _make_message({"query": "การวิเคราะห์โครงสร้างภาษาบาลีในพระไตรปิฎก"})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.ALLOW


@pytest.mark.asyncio
async def test_policy_enforcer_respects_disabled_guard():
    enforcer = PolicyEnforcer(enable_regulatory_guard=False)
    # Even if it contains citizen ID, it should allow since regulatory guard is disabled
    msg = _make_message({"text": "บัตรของผมเลขที่ 1234567890123 ครับ"})
    result = await enforcer.evaluate(msg)
    assert result.decision == PolicyDecision.ALLOW

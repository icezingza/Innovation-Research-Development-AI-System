import pytest

from src.orchestration.agent_registry import AgentRegistry
from src.runtime.state_manager import RuntimeStateManager


@pytest.mark.asyncio
async def test_state_manager_register_and_deregister():
    manager = RuntimeStateManager()
    await manager.register_agent("agent-a")
    await manager.register_agent("agent-b")
    state = await manager.get_state()
    assert "agent-a" in state["active_agents"]
    assert "agent-b" in state["active_agents"]

    await manager.deregister_agent("agent-a")
    state = await manager.get_state()
    assert "agent-a" not in state["active_agents"]
    assert "agent-b" in state["active_agents"]


@pytest.mark.asyncio
async def test_state_manager_no_duplicate_registration():
    manager = RuntimeStateManager()
    await manager.register_agent("agent-x")
    await manager.register_agent("agent-x")
    state = await manager.get_state()
    assert state["active_agents"].count("agent-x") == 1


@pytest.mark.asyncio
async def test_state_manager_cycle_counter():
    manager = RuntimeStateManager()
    count = await manager.increment_cycle()
    assert count == 1
    count = await manager.increment_cycle()
    assert count == 2


def test_agent_registry_register_and_list():
    class _FakeAgent:
        agent_id = "test-agent-1"

    registry = AgentRegistry()
    agent = _FakeAgent()
    registry.register(agent)
    assert "test-agent-1" in registry.list_ids()
    assert registry.count() == 1


def test_agent_registry_deregister():
    class _FakeAgent:
        agent_id = "test-agent-2"

    registry = AgentRegistry()
    agent = _FakeAgent()
    registry.register(agent)
    registry.deregister("test-agent-2")
    assert registry.count() == 0
    assert registry.get("test-agent-2") is None


@pytest.mark.asyncio
async def test_orchestration_pipeline_with_governed_agent():
    from src.agents.base_agent import BaseAgent
    from src.orchestration.cognitive_pipeline import CognitivePipeline

    class EchoAgent(BaseAgent):
        async def perceive(self, context):
            return context

        async def reason(self, perception):
            return {"conclusion": "echo", "evidence": [str(perception)]}

        async def act(self, reasoning):
            return {"output": reasoning["conclusion"]}

    agent = EchoAgent()
    pipeline = CognitivePipeline(agents=[agent])
    messages = await pipeline.run({"input": "hello"})
    assert len(messages) == 1
    assert messages[0].sender_id == agent.agent_id

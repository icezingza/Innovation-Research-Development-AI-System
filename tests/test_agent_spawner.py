"""Tests for AgentSpawner dynamic agent creation."""

import pytest

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.infrastructure.event_bus import RuntimeEventBus
from src.runtime.agent_spawner import AgentSpawner


@pytest.fixture
def spawner() -> AgentSpawner:
    return AgentSpawner(event_bus=RuntimeEventBus())


class TestAgentSpawner:
    def test_spawn_hypothesis_agent(self, spawner: AgentSpawner) -> None:
        record = spawner.spawn("hypothesis")
        assert isinstance(record.agent, HypothesisAgent)
        assert record.agent_type == "hypothesis"
        assert "hypothesis:" in record.agent_id

    def test_spawn_critique_agent(self, spawner: AgentSpawner) -> None:
        record = spawner.spawn("critique")
        assert isinstance(record.agent, CritiqueAgent)

    def test_spawn_synthesis_agent(self, spawner: AgentSpawner) -> None:
        record = spawner.spawn("synthesis")
        assert isinstance(record.agent, SynthesisAgent)

    def test_spawn_unknown_raises(self, spawner: AgentSpawner) -> None:
        with pytest.raises(ValueError, match="Unknown agent type"):
            spawner.spawn("unknown_type")

    def test_spawned_agents_tracked(self, spawner: AgentSpawner) -> None:
        spawner.spawn("hypothesis")
        spawner.spawn("critique")
        agents = spawner.list_agents()
        assert len(agents) == 2

    def test_terminate_removes_agent(self, spawner: AgentSpawner) -> None:
        record = spawner.spawn("hypothesis")
        ok = spawner.terminate(record.agent_id)
        assert ok
        remaining = spawner.list_agents()
        assert not any(a["agent_id"] == record.agent_id for a in remaining)

    def test_terminate_unknown_returns_false(self, spawner: AgentSpawner) -> None:
        assert not spawner.terminate("nonexistent-id")

    def test_stats_by_type(self, spawner: AgentSpawner) -> None:
        spawner.spawn("hypothesis")
        spawner.spawn("hypothesis")
        spawner.spawn("critique")
        stats = spawner.stats()
        assert stats["total_spawned"] == 3
        assert stats["by_type"]["hypothesis"] == 2
        assert stats["by_type"]["critique"] == 1

    def test_scale_coordinator_injects_hypothesis(self, spawner: AgentSpawner) -> None:
        class FakeCoordinator:
            hypothesis_agents: list = []
            critique_agents: list = []

        coord = FakeCoordinator()
        record = spawner.scale_coordinator(coord, "hypothesis")
        assert len(coord.hypothesis_agents) == 1
        assert coord.hypothesis_agents[0] is record.agent

    def test_scale_coordinator_injects_critique(self, spawner: AgentSpawner) -> None:
        class FakeCoordinator:
            hypothesis_agents: list = []
            critique_agents: list = []

        coord = FakeCoordinator()
        spawner.scale_coordinator(coord, "critique")
        assert len(coord.critique_agents) == 1

    def test_scale_coordinator_swaps_synthesis(self, spawner: AgentSpawner) -> None:
        class FakeCoordinator:
            synthesis_agent = None

        coord = FakeCoordinator()
        record = spawner.scale_coordinator(coord, "synthesis")
        assert coord.synthesis_agent is record.agent

"""Tests for AgentCoordinator multi-agent orchestration."""

import pytest

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.infrastructure.event_bus import (
    TOPIC_COORDINATION_COMPLETE,
    TOPIC_COORDINATION_STARTED,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.orchestration.agent_coordinator import (
    AgentCoordinator,
    CoordinatedResult,
    CoordinatorConfig,
)


def _make_coordinator(
    run_critique: bool = True,
    max_sub_questions: int = 2,
) -> tuple[AgentCoordinator, RuntimeEventBus]:
    bus = RuntimeEventBus()
    coordinator = AgentCoordinator(
        event_bus=bus,
        hypothesis_agents=[HypothesisAgent(event_bus=bus)],
        critique_agents=[CritiqueAgent(event_bus=bus)],
        synthesis_agent=SynthesisAgent(event_bus=bus),
        config=CoordinatorConfig(
            max_sub_questions=max_sub_questions,
            run_critique=run_critique,
        ),
    )
    return coordinator, bus


@pytest.mark.asyncio
async def test_coordinator_returns_coordinated_result():
    coordinator, _ = _make_coordinator()
    result = await coordinator.coordinate(
        "How does exercise affect cognitive function?"
    )
    assert isinstance(result, CoordinatedResult)
    assert result.goal == "How does exercise affect cognitive function?"
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_coordinator_generates_sub_questions():
    coordinator, _ = _make_coordinator(max_sub_questions=3)
    result = await coordinator.coordinate("What drives neuroplasticity?")
    assert len(result.sub_questions) == 3


@pytest.mark.asyncio
async def test_coordinator_produces_hypotheses():
    coordinator, _ = _make_coordinator(max_sub_questions=2)
    result = await coordinator.coordinate("What is the role of sleep?")
    assert len(result.hypotheses) == 2
    for h in result.hypotheses:
        assert "statement" in h


@pytest.mark.asyncio
async def test_coordinator_runs_critique_when_enabled():
    coordinator, _ = _make_coordinator(run_critique=True, max_sub_questions=2)
    result = await coordinator.coordinate("Does caffeine improve focus?")
    assert len(result.critiques) == 2
    for c in result.critiques:
        assert "critique" in c


@pytest.mark.asyncio
async def test_coordinator_skips_critique_when_disabled():
    coordinator, _ = _make_coordinator(run_critique=False, max_sub_questions=2)
    result = await coordinator.coordinate("Does caffeine improve focus?")
    assert result.critiques == []


@pytest.mark.asyncio
async def test_coordinator_produces_synthesis():
    coordinator, _ = _make_coordinator()
    result = await coordinator.coordinate("What causes cognitive decline?")
    assert "conclusion" in result.synthesis
    assert "confidence" in result.synthesis


@pytest.mark.asyncio
async def test_coordinator_publishes_lifecycle_events():
    coordinator, bus = _make_coordinator()
    lifecycle: list[str] = []

    async def capture(event: RuntimeEvent) -> None:
        lifecycle.append(event.topic)

    bus.subscribe(TOPIC_COORDINATION_STARTED, capture)
    bus.subscribe(TOPIC_COORDINATION_COMPLETE, capture)
    await coordinator.coordinate("Test goal")
    assert TOPIC_COORDINATION_STARTED in lifecycle
    assert TOPIC_COORDINATION_COMPLETE in lifecycle


@pytest.mark.asyncio
async def test_coordinator_events_published_count():
    coordinator, _ = _make_coordinator(max_sub_questions=2)
    result = await coordinator.coordinate("Goal with events")
    assert result.events_published >= 1


@pytest.mark.asyncio
async def test_coordinator_session_id_is_unique():
    coordinator, _ = _make_coordinator(max_sub_questions=1)
    r1 = await coordinator.coordinate("Goal A")
    r2 = await coordinator.coordinate("Goal B")
    assert r1.session_id != r2.session_id

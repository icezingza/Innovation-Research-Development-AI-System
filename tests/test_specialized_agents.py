"""Tests for HypothesisAgent, CritiqueAgent, and SynthesisAgent."""

import uuid

import pytest

from src.agents.critique_agent import CritiqueAgent
from src.agents.futurist_agent import FuturistAgent, TOPIC_FORECAST_GENERATED
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_CRITIQUED,
    TOPIC_HYPOTHESIS_GENERATED,
    TOPIC_SYNTHESIS_READY,
    RuntimeEvent,
    RuntimeEventBus,
)


# ---------- HypothesisAgent ----------


@pytest.mark.asyncio
async def test_hypothesis_agent_returns_action_message():
    agent = HypothesisAgent()
    msg = await agent.run({"question": "Does sleep improve memory?"})
    action = msg.content["action"]
    assert "hypothesis" in action
    assert "quality_score" in action
    assert 0.0 <= action["quality_score"] <= 1.0


@pytest.mark.asyncio
async def test_hypothesis_agent_publishes_event():
    bus = RuntimeEventBus()
    events: list[RuntimeEvent] = []

    async def capture(e: RuntimeEvent) -> None:
        events.append(e)

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, capture)
    agent = HypothesisAgent(event_bus=bus)
    await agent.run({"question": "What causes neuroplasticity?"})
    assert len(events) == 1
    assert events[0].topic == TOPIC_HYPOTHESIS_GENERATED
    assert "statement" in events[0].payload


@pytest.mark.asyncio
async def test_hypothesis_agent_no_bus_still_works():
    agent = HypothesisAgent(event_bus=None)
    msg = await agent.run({"question": "What is X?"})
    assert msg.content["action"]["hypothesis"]


# ---------- CritiqueAgent ----------


@pytest.mark.asyncio
async def test_critique_agent_returns_critique():
    hypothesis = {
        "id": str(uuid.uuid4()),
        "statement": "Exercise improves cognition",
        "confidence": 0.7,
        "evidence": ["study A"],
    }
    agent = CritiqueAgent()
    msg = await agent.run({"hypothesis": hypothesis, "question": "Does exercise help?"})
    action = msg.content["action"]
    assert "critique" in action
    assert "gaps" in action
    assert "refined_confidence" in action
    assert 0.0 <= action["refined_confidence"] <= 1.0


@pytest.mark.asyncio
async def test_critique_agent_publishes_event():
    bus = RuntimeEventBus()
    events: list[RuntimeEvent] = []

    async def capture(e: RuntimeEvent) -> None:
        events.append(e)

    bus.subscribe(TOPIC_HYPOTHESIS_CRITIQUED, capture)
    hypothesis = {
        "id": str(uuid.uuid4()),
        "statement": "X causes Y",
        "confidence": 0.6,
        "evidence": [],
    }
    agent = CritiqueAgent(event_bus=bus)
    await agent.run({"hypothesis": hypothesis, "question": "Does X cause Y?"})
    assert len(events) == 1
    assert events[0].topic == TOPIC_HYPOTHESIS_CRITIQUED


@pytest.mark.asyncio
async def test_critique_agent_reports_consistency():
    hypothesis = {
        "id": str(uuid.uuid4()),
        "statement": "Sleep always improves memory",
        "confidence": 0.8,
        "evidence": ["paper A"],
    }
    agent = CritiqueAgent()
    msg = await agent.run({"hypothesis": hypothesis, "question": "Sleep and memory?"})
    action = msg.content["action"]
    assert "is_consistent" in action
    assert isinstance(action["is_consistent"], bool)


# ---------- SynthesisAgent ----------


@pytest.mark.asyncio
async def test_synthesis_agent_returns_conclusion():
    hypotheses = [
        {
            "id": "h1",
            "statement": "Sleep consolidates memory",
            "confidence": 0.8,
            "evidence": ["e1"],
        },
        {
            "id": "h2",
            "statement": "Deep sleep is critical for memory",
            "confidence": 0.7,
            "evidence": ["e2"],
        },
    ]
    agent = SynthesisAgent()
    msg = await agent.run(
        {"goal": "How does sleep affect memory?", "hypotheses": hypotheses}
    )
    action = msg.content["action"]
    assert "conclusion" in action
    assert "confidence" in action
    assert action["source_count"] == 2


@pytest.mark.asyncio
async def test_synthesis_agent_publishes_event():
    bus = RuntimeEventBus()
    events: list[RuntimeEvent] = []

    async def capture(e: RuntimeEvent) -> None:
        events.append(e)

    bus.subscribe(TOPIC_SYNTHESIS_READY, capture)
    agent = SynthesisAgent(event_bus=bus)
    hypotheses = [
        {"id": "h1", "statement": "X causes Y", "confidence": 0.7, "evidence": []},
    ]
    await agent.run({"goal": "What causes Y?", "hypotheses": hypotheses})
    assert len(events) == 1
    assert events[0].topic == TOPIC_SYNTHESIS_READY


@pytest.mark.asyncio
async def test_synthesis_agent_empty_hypotheses():
    agent = SynthesisAgent()
    msg = await agent.run({"goal": "Some goal", "hypotheses": []})
    action = msg.content["action"]
    assert "conclusion" in action
    assert action["confidence"] == 0.0


@pytest.mark.asyncio
async def test_synthesis_agent_selects_highest_quality():
    hypotheses = [
        {"id": "h1", "statement": "weak hypothesis", "confidence": 0.1, "evidence": []},
        {
            "id": "h2",
            "statement": "strong hypothesis",
            "confidence": 0.95,
            "evidence": ["lots", "of", "evidence"],
        },
    ]
    agent = SynthesisAgent()
    msg = await agent.run({"goal": "Which is better?", "hypotheses": hypotheses})
    action = msg.content["action"]
    assert action["confidence"] > 0.1


# ---------- FuturistAgent ----------


@pytest.mark.asyncio
async def test_futurist_agent_returns_forecast():
    agent = FuturistAgent()
    msg = await agent.run(
        {"question": "What is the future of Quantum Computing?", "timeframe_years": 8}
    )
    action = msg.content["action"]
    assert "forecast_id" in action
    assert "scenarios" in action
    assert "timeline" in action
    assert "emergence_signals" in action
    assert action["target_horizon_years"] == 8

    scenarios = action["scenarios"]
    assert "optimistic" in scenarios
    assert "pessimistic" in scenarios
    assert "most_likely" in scenarios


@pytest.mark.asyncio
async def test_futurist_agent_publishes_event():
    bus = RuntimeEventBus()
    events: list[RuntimeEvent] = []

    async def capture(e: RuntimeEvent) -> None:
        events.append(e)

    bus.subscribe(TOPIC_FORECAST_GENERATED, capture)
    agent = FuturistAgent(event_bus=bus)
    await agent.run({"question": "AI-driven biology future", "timeframe_years": 10})

    assert len(events) == 1
    assert events[0].topic == TOPIC_FORECAST_GENERATED
    assert "forecast_id" in events[0].payload
    assert "most_likely_path" in events[0].payload


@pytest.mark.asyncio
async def test_futurist_agent_no_bus_still_works():
    agent = FuturistAgent(event_bus=None)
    msg = await agent.run({"question": "Web3 future", "timeframe_years": 5})
    assert msg.content["action"]["scenarios"]["most_likely"]

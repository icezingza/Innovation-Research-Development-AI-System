import pytest

from src.agents.research_agent import ResearchAgent
from src.protocols.agent_message import MessageType


@pytest.mark.asyncio
async def test_research_agent_run_returns_message():
    agent = ResearchAgent()
    message = await agent.run(
        {"question": "Does caffeine improve cognitive performance?"}
    )
    assert message.sender_id == agent.agent_id
    assert message.message_type == MessageType.ACTION
    assert "hypothesis" in message.content["action"]


@pytest.mark.asyncio
async def test_research_agent_perceive_extracts_fields():
    agent = ResearchAgent()
    perception = await agent.perceive(
        {
            "question": "What causes climate change?",
            "constraints": ["use empirical data"],
            "prior_hypotheses": ["CO2 is the primary driver"],
        }
    )
    assert perception["question"] == "What causes climate change?"
    assert perception["constraints"] == ["use empirical data"]
    assert len(perception["prior_hypotheses"]) == 1


@pytest.mark.asyncio
async def test_research_agent_reason_produces_evolved_hypothesis():
    agent = ResearchAgent()
    perception = {
        "question": "Does sleep affect memory consolidation?",
        "prior_hypotheses": [],
        "constraints": [],
    }
    reasoning = await agent.reason(perception)
    assert "evolved_hypothesis" in reasoning
    assert reasoning["evolved_hypothesis"]["generation"] == 1
    assert "reflection" in reasoning
    assert 0.0 <= reasoning["reflection"]["quality_score"] <= 1.0


@pytest.mark.asyncio
async def test_research_agent_act_returns_structured_output():
    agent = ResearchAgent()
    perception = await agent.perceive(
        {"question": "Is exercise beneficial for longevity?"}
    )
    reasoning = await agent.reason(perception)
    action = await agent.act(reasoning)
    assert "hypothesis" in action
    assert "quality_score" in action
    assert "is_consistent" in action
    assert isinstance(action["is_consistent"], bool)


@pytest.mark.asyncio
async def test_research_agent_detects_contradictions_in_priors():
    agent = ResearchAgent()
    perception = await agent.perceive(
        {
            "question": "Is the system reliable?",
            "prior_hypotheses": [
                "The system is always available",
                "The system will never be available",
            ],
        }
    )
    reasoning = await agent.reason(perception)
    assert reasoning["contradictions"] is not None
    assert not reasoning["contradictions"]["is_consistent"]


@pytest.mark.asyncio
async def test_research_agent_consistent_priors_pass():
    agent = ResearchAgent()
    perception = await agent.perceive(
        {
            "question": "What drives innovation?",
            "prior_hypotheses": [
                "Curiosity drives research",
                "Funding enables experiments",
            ],
        }
    )
    reasoning = await agent.reason(perception)
    if reasoning["contradictions"] is not None:
        assert reasoning["contradictions"]["is_consistent"]

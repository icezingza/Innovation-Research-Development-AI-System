"""Tests for ResearchWorkflow — all external deps (pipeline, debate, recursive) mocked."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestration.research_workflow import (
    ResearchWorkflow,
    WorkflowConfig,
    WorkflowResult,
)
from src.protocols.agent_message import AgentMessage, MessageType


def _make_agent_message(hypothesis: dict, quality: float) -> AgentMessage:
    return AgentMessage(
        id=str(uuid.uuid4()),
        sender_id="test-agent",
        message_type=MessageType.ACTION,
        content={
            "action": {
                "hypothesis": hypothesis,
                "quality_score": quality,
            }
        },
    )


def _mock_pipeline(hypothesis: dict, quality: float = 0.8) -> AsyncMock:
    pipeline = AsyncMock()
    pipeline.run = AsyncMock(
        return_value=[_make_agent_message(hypothesis, quality)]
    )
    return pipeline


def _mock_debate() -> AsyncMock:
    debate = AsyncMock()
    result = MagicMock()
    result.model_dump.return_value = {"winner": "proponent", "total_rounds": 1}
    debate.debate = AsyncMock(return_value=result)
    return debate


def _mock_recursive(final_hypothesis: dict) -> AsyncMock:
    recursive = AsyncMock()
    result = MagicMock()
    final = MagicMock()
    final.model_dump.return_value = final_hypothesis
    result.model_dump.return_value = {"depth_reached": 2}
    result.final_hypothesis = final
    recursive.run = AsyncMock(return_value=result)
    return recursive


@pytest.mark.asyncio
async def test_workflow_returns_workflow_result():
    hypothesis = {"statement": "X causes Y", "confidence": 0.75, "evidence": ["e1"]}
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=_mock_debate(),
        recursive_loop=_mock_recursive(hypothesis),
        config=WorkflowConfig(
            max_sub_questions=1, run_debate=False, run_recursive_reasoning=False
        ),
    )
    result = await workflow.run("What causes Y?")
    assert isinstance(result, WorkflowResult)
    assert result.goal == "What causes Y?"
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_workflow_runs_debate_when_enabled():
    hypothesis = {"statement": "X causes Y", "confidence": 0.8, "evidence": []}
    debate = _mock_debate()
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=debate,
        recursive_loop=_mock_recursive(hypothesis),
        config=WorkflowConfig(
            max_sub_questions=1, run_debate=True, run_recursive_reasoning=False
        ),
    )
    result = await workflow.run("What causes Y?")
    debate.debate.assert_called_once()
    assert result.debate_result is not None


@pytest.mark.asyncio
async def test_workflow_skips_debate_when_disabled():
    hypothesis = {"statement": "X causes Y", "confidence": 0.8, "evidence": []}
    debate = _mock_debate()
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=debate,
        recursive_loop=_mock_recursive(hypothesis),
        config=WorkflowConfig(
            max_sub_questions=1, run_debate=False, run_recursive_reasoning=False
        ),
    )
    result = await workflow.run("What causes Y?")
    debate.debate.assert_not_called()
    assert result.debate_result is None


@pytest.mark.asyncio
async def test_workflow_runs_recursive_when_enabled():
    hypothesis = {"statement": "X causes Y", "confidence": 0.8, "evidence": []}
    recursive = _mock_recursive(hypothesis)
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=_mock_debate(),
        recursive_loop=recursive,
        config=WorkflowConfig(
            max_sub_questions=1, run_debate=False, run_recursive_reasoning=True
        ),
    )
    result = await workflow.run("What causes Y?")
    recursive.run.assert_called_once()
    assert result.recursive_result is not None


@pytest.mark.asyncio
async def test_workflow_empty_result_on_all_failures():
    pipeline = AsyncMock()
    pipeline.run = AsyncMock(side_effect=RuntimeError("agent crashed"))
    workflow = ResearchWorkflow(
        pipeline=pipeline,
        debate_runtime=_mock_debate(),
        recursive_loop=_mock_recursive({}),
        config=WorkflowConfig(max_sub_questions=1),
    )
    result = await workflow.run("crash test")
    assert result.sub_results == []
    assert result.synthesis.get("error") is True


@pytest.mark.asyncio
async def test_workflow_stores_to_knowledge_graph():
    hyp_id = str(uuid.uuid4())
    hypothesis = {
        "id": hyp_id,
        "statement": "X causes Y",
        "confidence": 0.8,
        "evidence": [],
        "generation": 1,
    }
    graph = AsyncMock()
    graph.store_hypothesis = AsyncMock()
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=_mock_debate(),
        recursive_loop=_mock_recursive(hypothesis),
        knowledge_graph=graph,
        config=WorkflowConfig(
            max_sub_questions=1, run_debate=False, run_recursive_reasoning=False
        ),
    )
    await workflow.run("What causes Y?")
    graph.store_hypothesis.assert_called_once()


@pytest.mark.asyncio
async def test_workflow_selects_highest_quality_hypothesis():
    pipeline = AsyncMock()

    def _msg(q: float) -> list[AgentMessage]:
        return [
            _make_agent_message(
                {"statement": f"quality={q}", "confidence": q, "evidence": []}, q
            )
        ]

    call_count = 0

    async def _run(context):
        nonlocal call_count
        call_count += 1
        return _msg(0.3 if call_count == 1 else 0.9)

    pipeline.run = _run
    workflow = ResearchWorkflow(
        pipeline=pipeline,
        debate_runtime=_mock_debate(),
        recursive_loop=_mock_recursive(
            {"statement": "quality=0.9", "confidence": 0.9, "evidence": []}
        ),
        config=WorkflowConfig(
            max_sub_questions=2, run_debate=False, run_recursive_reasoning=False
        ),
    )
    result = await workflow.run("Which is best?")
    assert "0.9" in result.primary_hypothesis.get("statement", "")


@pytest.mark.asyncio
async def test_workflow_heuristic_plan_generates_sub_questions():
    hypothesis = {"statement": "X", "confidence": 0.5, "evidence": []}
    workflow = ResearchWorkflow(
        pipeline=_mock_pipeline(hypothesis),
        debate_runtime=_mock_debate(),
        recursive_loop=_mock_recursive(hypothesis),
        config=WorkflowConfig(
            max_sub_questions=3, run_debate=False, run_recursive_reasoning=False
        ),
    )
    result = await workflow.run("What is X?")
    assert len(result.sub_questions) == 3

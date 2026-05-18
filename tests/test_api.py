"""API integration tests using an in-memory SQLite DB and no external services."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.research_agent import ResearchAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.api.health import router as health_router
from src.api.routes.cognition import router as cognition_router
from src.api.routes.governance import router as governance_router
from src.api.routes.intelligence import router as intelligence_router
from src.api.routes.reasoning import router as reasoning_router
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router
from src.api.routes.streams import router as streams_router
from src.api.routes.workflows import router as workflows_router
from src.governance.audit_log import GovernanceAuditLog
from src.governance.policy_enforcer import PolicyEnforcer
from src.infrastructure.event_bus import RuntimeEventBus
from src.memory.research_memory import ResearchMemory
from src.memory.schema import Base
from src.reasoning.quality_tracker import QualityTracker
from src.runtime.stream_manager import StreamManager
from src.orchestration.agent_coordinator import AgentCoordinator, CoordinatorConfig
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.orchestration.debate_runtime import DebateRuntime
from src.orchestration.research_workflow import ResearchWorkflow, WorkflowConfig
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import RecursiveReasoningLoop
from src.runtime.scheduler import AsyncScheduler
from src.runtime.state_manager import RuntimeStateManager


@pytest.fixture
def test_app():
    """FastAPI app wired with in-memory SQLite — no external services needed."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        audit_log = GovernanceAuditLog()
        event_bus = RuntimeEventBus()
        research_memory = ResearchMemory()
        MemoryAgent(research_memory=research_memory).register(event_bus)
        pipeline = CognitivePipeline(
            agents=[ResearchAgent()],
            policy_enforcer=PolicyEnforcer(audit_log=audit_log),
        )
        state_manager = RuntimeStateManager()
        recursive_loop = RecursiveReasoningLoop()
        debate_runtime = DebateRuntime()
        research_workflow = ResearchWorkflow(
            pipeline=pipeline,
            debate_runtime=debate_runtime,
            recursive_loop=recursive_loop,
            config=WorkflowConfig(
                max_sub_questions=1,
                run_debate=False,
                run_recursive_reasoning=False,
            ),
        )
        coordinator = AgentCoordinator(
            event_bus=event_bus,
            hypothesis_agents=[HypothesisAgent(event_bus=event_bus)],
            critique_agents=[CritiqueAgent(event_bus=event_bus)],
            synthesis_agent=SynthesisAgent(event_bus=event_bus),
            config=CoordinatorConfig(max_sub_questions=1, run_critique=False),
        )

        app.state.pipeline = pipeline
        app.state.state_manager = state_manager
        app.state.db_session = session_factory
        app.state.reasoning_trace = ReasoningTrace()
        app.state.recursive_loop = recursive_loop
        app.state.debate_runtime = debate_runtime
        app.state.research_workflow = research_workflow
        app.state.scheduler = AsyncScheduler()
        app.state.audit_log = audit_log
        app.state.event_bus = event_bus
        app.state.coordinator = coordinator
        app.state.research_memory = research_memory
        app.state.quality_tracker = QualityTracker(ReasoningTrace())
        app.state.stream_manager = StreamManager()
        app.state.key_manager = None
        app.state.rate_limiter = None
        app.state.service_errors = {}
        yield

        await engine.dispose()

    application = FastAPI(lifespan=_lifespan)
    application.include_router(health_router)
    application.include_router(research_router)
    application.include_router(workflows_router)
    application.include_router(runtime_router)
    application.include_router(reasoning_router)
    application.include_router(governance_router)
    application.include_router(cognition_router)
    application.include_router(intelligence_router)
    application.include_router(streams_router)

    from fastapi import Request
    from src.api.routes.auth import get_current_user

    async def mock_get_current_user(request: Request):
        payload = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "role": "member",
        }
        request.state.tenant_id = payload["tenant_id"]
        request.state.user_id = payload["sub"]
        return payload

    application.dependency_overrides[get_current_user] = mock_get_current_user
    return application


def test_health_returns_healthy(test_app):
    with TestClient(test_app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["runtime"] == "healthy"
    assert response.json()["unavailable_services"] == []


def test_runtime_state_returns_empty_on_start(test_app):
    with TestClient(test_app) as client:
        response = client.get("/runtime/state")
    assert response.status_code == 200
    data = response.json()
    assert "active_agents" in data
    assert "cycles" in data


def test_create_research_task_returns_202(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/research/tasks",
            json={"question": "Does exercise improve cognitive function?"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "task_id" in body


def test_get_research_task_not_found(test_app):
    with TestClient(test_app) as client:
        response = client.get("/research/tasks/nonexistent-id")
    assert response.status_code == 404


def test_create_and_retrieve_research_task(test_app):
    with TestClient(test_app) as client:
        create_resp = client.post(
            "/research/tasks",
            json={
                "question": "What is the role of sleep in memory consolidation?",
                "constraints": ["use peer-reviewed sources"],
            },
        )
        assert create_resp.status_code == 202
        task_id = create_resp.json()["task_id"]

        get_resp = client.get(f"/research/tasks/{task_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["task_id"] == task_id
    assert data["question"] == "What is the role of sleep in memory consolidation?"


def test_recursive_reasoning_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/reasoning/recursive",
            json={
                "hypothesis_statement": "Sleep consolidates episodic memory",
                "question": "How does sleep affect memory?",
                "max_depth": 2,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "final_hypothesis" in data
    assert data["depth_reached"] >= 1
    assert "convergence_reason" in data


def test_debate_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/reasoning/debates",
            json={
                "hypothesis": "Exercise improves cognitive function",
                "max_rounds": 1,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "winner" in data
    assert data["winner"] in ("proponent", "opponent", "draw")
    assert data["total_rounds"] >= 0  # adaptive fast-track may produce 0 rounds


def test_reasoning_traces_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/reasoning/traces")
    assert response.status_code == 200
    data = response.json()
    assert "traces" in data
    assert "count" in data


def test_create_workflow_returns_202(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/research/workflows",
            json={"goal": "Understand mechanisms of neuroplasticity"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "workflow_id" in body


def test_get_workflow_not_found(test_app):
    with TestClient(test_app) as client:
        response = client.get("/research/workflows/nonexistent-id")
    assert response.status_code == 404


def test_create_and_retrieve_workflow(test_app):
    with TestClient(test_app) as client:
        create_resp = client.post(
            "/research/workflows",
            json={"goal": "What causes cognitive decline?"},
        )
        assert create_resp.status_code == 202
        workflow_id = create_resp.json()["workflow_id"]

        get_resp = client.get(f"/research/workflows/{workflow_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["workflow_id"] == workflow_id
    assert data["goal"] == "What causes cognitive decline?"


def test_list_workflows(test_app):
    with TestClient(test_app) as client:
        client.post("/research/workflows", json={"goal": "Goal A"})
        client.post("/research/workflows", json={"goal": "Goal B"})
        response = client.get("/research/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert "count" in data
    assert data["count"] >= 2


def test_governance_audit_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/governance/audit")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_coordinate_endpoint_returns_result(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/cognition/coordinate",
            json={"goal": "What causes cognitive decline?", "run_critique": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "hypotheses" in data
    assert "synthesis" in data
    assert data["goal"] == "What causes cognitive decline?"


def test_event_stats_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/cognition/events/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_events_published" in data
    assert "total_subscribers" in data


def test_intelligence_report_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/report")
    assert response.status_code == 200
    data = response.json()
    assert "knowledge_base" in data
    assert "recent_findings" in data
    assert "total_entries" in data["knowledge_base"]


def test_intelligence_recall_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/recall?topic=memory+consolidation")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert "entries" in data
    assert "count" in data


def test_intelligence_hypotheses_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/hypotheses")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_intelligence_quality_trends_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/quality-trends")
    assert response.status_code == 200
    data = response.json()
    assert "total_entries_analyzed" in data
    assert "recommendation" in data


def test_active_streams_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/streams/active")
    assert response.status_code == 200
    data = response.json()
    assert "active_streams" in data

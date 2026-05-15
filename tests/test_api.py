"""API integration tests using an in-memory SQLite DB and no external services."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.research_agent import ResearchAgent
from src.api.health import router as health_router
from src.api.routes.governance import router as governance_router
from src.api.routes.reasoning import router as reasoning_router
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router
from src.api.routes.workflows import router as workflows_router
from src.governance.audit_log import GovernanceAuditLog
from src.governance.policy_enforcer import PolicyEnforcer
from src.memory.schema import Base
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

        app.state.pipeline = pipeline
        app.state.state_manager = state_manager
        app.state.db_session = session_factory
        app.state.reasoning_trace = ReasoningTrace()
        app.state.recursive_loop = recursive_loop
        app.state.debate_runtime = debate_runtime
        app.state.research_workflow = research_workflow
        app.state.scheduler = AsyncScheduler()
        app.state.audit_log = audit_log
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
    assert data["total_rounds"] >= 1


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

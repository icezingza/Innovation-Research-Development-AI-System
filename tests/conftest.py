"""Shared pytest fixtures for all test modules."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.research_agent import ResearchAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.api.health import router as health_router
from src.api.routes.audit_sdk import router as audit_sdk_router
from src.api.routes.security import router as security_router
from src.api.routes.vertical_swarms import router as vertical_swarms_router
from src.api.routes.telemetry import router as telemetry_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.cognition import router as cognition_router
from src.api.routes.governance import router as governance_router
from src.api.routes.intelligence import router as intelligence_router
from src.api.routes.reasoning import router as reasoning_router
from src.api.routes.research import router as research_router
from src.api.routes.runtime import router as runtime_router
from src.api.routes.streams import router as streams_router
from src.api.routes.workflows import router as workflows_router
from src.api.routes.auth import get_current_user
from src.governance.audit_log import GovernanceAuditLog
from src.governance.policy_enforcer import PolicyEnforcer
from src.infrastructure.event_bus import RuntimeEventBus
from src.memory.research_memory import ResearchMemory
from src.memory.schema import Base
from src.orchestration.agent_coordinator import AgentCoordinator, CoordinatorConfig
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.orchestration.debate_runtime import DebateRuntime
from src.orchestration.research_workflow import ResearchWorkflow, WorkflowConfig
from src.reasoning.quality_tracker import QualityTracker
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import RecursiveReasoningLoop
from src.runtime.scheduler import AsyncScheduler
from src.runtime.state_manager import RuntimeStateManager
from src.runtime.stream_manager import StreamManager


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
    application.include_router(audit_sdk_router)
    application.include_router(security_router)
    application.include_router(vertical_swarms_router)
    application.include_router(telemetry_router)
    application.include_router(dashboard_router)

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

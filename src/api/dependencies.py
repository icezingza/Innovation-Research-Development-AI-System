from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.governance.audit_log import GovernanceAuditLog
from src.infrastructure.event_bus import RuntimeEventBus
from src.memory.research_memory import ResearchMemory
from src.orchestration.agent_coordinator import AgentCoordinator
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.orchestration.debate_runtime import DebateRuntime
from src.orchestration.research_workflow import ResearchWorkflow
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import RecursiveReasoningLoop
from src.runtime.scheduler import AsyncScheduler
from src.runtime.state_manager import RuntimeStateManager


def get_pipeline(request: Request) -> CognitivePipeline:
    return request.app.state.pipeline


def get_state_manager(request: Request) -> RuntimeStateManager:
    return request.app.state.state_manager


def get_db_session(request: Request) -> async_sessionmaker[AsyncSession]:
    factory = getattr(request.app.state, "db_session", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return factory


def get_reasoning_trace(request: Request) -> ReasoningTrace:
    return request.app.state.reasoning_trace


def get_recursive_loop(request: Request) -> RecursiveReasoningLoop:
    return request.app.state.recursive_loop


def get_debate_runtime(request: Request) -> DebateRuntime:
    return request.app.state.debate_runtime


def get_workflow(request: Request) -> ResearchWorkflow:
    workflow = getattr(request.app.state, "research_workflow", None)
    if workflow is None:
        raise HTTPException(status_code=503, detail="Research workflow unavailable")
    return workflow


def get_scheduler(request: Request) -> AsyncScheduler:
    return request.app.state.scheduler


def get_audit_log(request: Request) -> GovernanceAuditLog:
    return request.app.state.audit_log


def get_event_bus(request: Request) -> RuntimeEventBus:
    return request.app.state.event_bus


def get_coordinator(request: Request) -> AgentCoordinator:
    coordinator = getattr(request.app.state, "coordinator", None)
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Agent coordinator unavailable")
    return coordinator


def get_research_memory(request: Request) -> ResearchMemory:
    return request.app.state.research_memory

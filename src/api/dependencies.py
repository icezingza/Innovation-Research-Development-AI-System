from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.governance.audit_log import GovernanceAuditLog
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

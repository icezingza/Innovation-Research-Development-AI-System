import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.schema import ReasoningTraceRecord, HypothesisRecord, ResearchTask
from src.security.auth_utils import RequireRole
from src.api.dependencies import get_db, get_db_session, get_pipeline
from src.api.routes.auth import get_current_user
from src.security.rls import get_rls_db
from src.orchestration.cognitive_pipeline import CognitivePipeline
from src.tenants.context import SYSTEM_TENANT_ID
from src.security.regulatory_guard import get_regulatory_guard, RegulatoryViolation

router = APIRouter(prefix="/research", tags=["research"])


class ResearchTaskRequest(BaseModel):
    question: str
    constraints: list[str] = []
    prior_hypotheses: list[str] = []


class ResearchTaskCreated(BaseModel):
    task_id: str
    status: str


@router.post("/tasks", response_model=ResearchTaskCreated, status_code=202)
async def create_research_task(
    body: ResearchTaskRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    pipeline: CognitivePipeline = Depends(get_pipeline),
    session_factory=Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ResearchTaskCreated:

    # === Regulatory Guard Check ===
    guard = get_regulatory_guard()
    try:
        guard.check(
            body.question,
            context={"domain": "general", "tenant_id": current_user.get("tenant_id")},
        )
    except RegulatoryViolation as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "regulatory_violation",
                "rule_id": e.rule_id,
                "message": e.message,
                "severity": e.severity,
            },
        )
    # === End Guard Check ===

    task_id = str(uuid.uuid4())

    # Populate request.state from JWT so _resolve_tenant_id works
    request.state.tenant_id = current_user.get("tenant_id")
    request.state.user_id = current_user.get("sub")

    # Resolve tenant_id from request state (set by auth or tenant middleware)
    tenant_id: str = _resolve_tenant_id(request)

    from sqlalchemy import text

    async with session_factory() as session:
        # Set RLS context so tenant_isolation policy allows the INSERT
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": tenant_id},
        )

        # Swarm template lookup deferred to Phase 4B (requires tenant_swarms table migration)
        # For now, use default context — swarm activation will be a separate API call
        context: dict[str, Any] = {
            "question": body.question,
            "constraints": body.constraints,
            "prior_hypotheses": body.prior_hypotheses,
        }

        task = ResearchTask(
            id=task_id, tenant_id=tenant_id, question=body.question, status="pending"
        )
        session.add(task)
        await session.commit()

    context: dict[str, Any] = {
        "question": body.question,
        "constraints": body.constraints,
        "prior_hypotheses": body.prior_hypotheses,
    }
    background_tasks.add_task(
        _execute_task, task_id, context, pipeline, session_factory
    )
    return ResearchTaskCreated(task_id=task_id, status="pending")


@router.get("/tasks/{task_id}")
async def get_research_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_rls_db),
) -> dict[str, Any]:
    # Best-effort auth: set tenant_id on state when JWT is present
    from src.security.auth_utils import decode_token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            request.state.tenant_id = payload.get("tenant_id")
            request.state.user_id = payload.get("sub")
        except Exception:
            pass

    task = await db.get(ResearchTask, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.id,
        "question": task.question,
        "status": task.status,
        "results": task.results,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
    }


@router.get("/tasks/{task_id}/trace")
async def get_task_trace(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve the auditable trace of a research task.

    Shows the reasoning flow: Hypothesis -> Research -> Critique -> Synthesis
    Requires admin, auditor, or owner role.
    """
    from sqlalchemy import text

    await RequireRole(["admin", "auditor", "owner"])(current_user)

    # Set RLS context so the query returns this tenant's data only
    tenant_id = current_user.get("tenant_id", "")
    await db.execute(
        text("SELECT set_config('app.tenant_id', :tid, false)"),
        {"tid": tenant_id},
    )

    # Get the task to verify access and context
    task = await db.get(ResearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Query all reasoning traces for this task (using task_id as session proxy)
    traces_result = await db.execute(
        select(ReasoningTraceRecord)
        .where(ReasoningTraceRecord.tenant_id == task.tenant_id)
        .order_by(ReasoningTraceRecord.timestamp.asc())
    )
    traces = traces_result.scalars().all()

    # Query all hypotheses generated during this task
    hyps_result = await db.execute(
        select(HypothesisRecord)
        .where(HypothesisRecord.tenant_id == task.tenant_id)
        .where(HypothesisRecord.session_id == task_id)
        .order_by(HypothesisRecord.created_at.asc())
    )
    hyps = hyps_result.scalars().all()

    events = []

    # Add reasoning traces
    for trace in traces:
        events.append(
            {
                "timestamp": trace.timestamp.isoformat(),
                "agent": trace.agent_id or "ReasoningEngine",
                "action": trace.operation,
                "content": trace.output_summary,
            }
        )

    # Add hypothesis events
    for hyp in hyps:
        events.append(
            {
                "timestamp": hyp.created_at.isoformat(),
                "agent": "HypothesisAgent",
                "action": "propose" if hyp.generation == 0 else "refine",
                "content": {
                    "hypothesis": hyp.statement,
                    "confidence": hyp.confidence,
                    "evidence": hyp.evidence,
                },
            }
        )

    # Sort chronologically
    events.sort(key=lambda x: x["timestamp"])

    return {
        "task_id": task_id,
        "question": task.question,
        "status": task.status,
        "events": events,
    }


def _resolve_tenant_id(request: Request) -> str:
    """Extract tenant ID from request state, defaulting to SYSTEM_TENANT_ID."""
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        tenant_ctx = getattr(request.state, "tenant", None)
        raw = getattr(tenant_ctx, "tenant_id", None)
    return str(raw) if raw else SYSTEM_TENANT_ID


async def _execute_task(
    task_id: str,
    context: dict[str, Any],
    pipeline: CognitivePipeline,
    session_factory,
) -> None:
    try:
        messages = await pipeline.run(context)
        results = [m.model_dump(mode="json") for m in messages]
        status = "complete"
        error: str | None = None
    except Exception as exc:
        results = []
        status = "error"
        error = str(exc)

    async with session_factory() as session:
        task = await session.get(ResearchTask, task_id)
        if task is not None:
            task.status = status
            task.results = results
            task.error_message = error
            await session.commit()

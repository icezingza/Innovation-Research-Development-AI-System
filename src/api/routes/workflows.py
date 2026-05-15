import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import get_db_session, get_workflow
from src.memory.schema import WorkflowRecord
from src.orchestration.research_workflow import ResearchWorkflow

router = APIRouter(prefix="/research", tags=["workflows"])
logger = logging.getLogger(__name__)


class WorkflowRequest(BaseModel):
    goal: str
    max_sub_questions: int = 3
    run_debate: bool = True
    run_recursive_reasoning: bool = True


class WorkflowResponse(BaseModel):
    workflow_id: str
    goal: str
    status: str


async def _run_workflow(
    workflow_id: str,
    goal: str,
    workflow: ResearchWorkflow,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        record = await session.get(WorkflowRecord, workflow_id)
        if record is None:
            return
        record.status = "running"
        await session.commit()

    try:
        result = await workflow.run(goal)
        async with session_factory() as session:
            record = await session.get(WorkflowRecord, workflow_id)
            if record is None:
                return
            record.status = "completed"
            record.sub_questions = result.sub_questions
            record.results = result.model_dump()
            record.completed_at = datetime.now(UTC)
            await session.commit()
    except Exception as exc:
        logger.warning(
            "workflow_failed",
            extra={"workflow_id": workflow_id, "error": str(exc)},
        )
        async with session_factory() as session:
            record = await session.get(WorkflowRecord, workflow_id)
            if record is None:
                return
            record.status = "failed"
            record.error_message = str(exc)
            record.completed_at = datetime.now(UTC)
            await session.commit()


@router.post("/workflows", status_code=202, response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
    workflow: ResearchWorkflow = Depends(get_workflow),
) -> WorkflowResponse:
    workflow_id = str(uuid.uuid4())
    async with session_factory() as session:
        record = WorkflowRecord(
            id=workflow_id,
            goal=request.goal,
            status="pending",
        )
        session.add(record)
        await session.commit()

    background_tasks.add_task(
        _run_workflow, workflow_id, request.goal, workflow, session_factory
    )
    return WorkflowResponse(
        workflow_id=workflow_id,
        goal=request.goal,
        status="pending",
    )


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> dict:
    async with session_factory() as session:
        result = await session.execute(
            select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "workflow_id": record.id,
        "goal": record.goal,
        "status": record.status,
        "sub_questions": record.sub_questions,
        "results": record.results,
        "error_message": record.error_message,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "completed_at": (
            record.completed_at.isoformat() if record.completed_at else None
        ),
    }


@router.get("/workflows")
async def list_workflows(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
    limit: int = 20,
) -> dict:
    async with session_factory() as session:
        result = await session.execute(
            select(WorkflowRecord)
            .order_by(WorkflowRecord.created_at.desc())
            .limit(limit)
        )
        records = result.scalars().all()

    return {
        "workflows": [
            {
                "workflow_id": r.id,
                "goal": r.goal,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "count": len(records),
    }

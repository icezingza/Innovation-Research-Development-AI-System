import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import get_db_session, get_pipeline
from src.memory.schema import ResearchTask
from src.orchestration.cognitive_pipeline import CognitivePipeline

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
    background_tasks: BackgroundTasks,
    pipeline: CognitivePipeline = Depends(get_pipeline),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> ResearchTaskCreated:
    task_id = str(uuid.uuid4())

    async with session_factory() as session:
        task = ResearchTask(id=task_id, question=body.question, status="pending")
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
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> dict[str, Any]:
    from fastapi import HTTPException

    async with session_factory() as session:
        task = await session.get(ResearchTask, task_id)

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


async def _execute_task(
    task_id: str,
    context: dict[str, Any],
    pipeline: CognitivePipeline,
    session_factory: async_sessionmaker[AsyncSession],
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

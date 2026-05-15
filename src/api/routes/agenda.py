"""Autonomous research agenda endpoints.

GET  /intelligence/agenda        — current agenda analysis
POST /intelligence/agenda/run    — trigger an agenda analysis and submit
                                   high-priority items to the scheduler
"""
import logging

from fastapi import APIRouter, HTTPException, Request

from src.orchestration.research_agenda import ResearchAgenda
from src.runtime.scheduler import AsyncScheduler, TaskPriority

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intelligence"])


def _get_agenda(request: Request) -> ResearchAgenda:
    agenda = getattr(request.app.state, "research_agenda", None)
    if agenda is None:
        raise HTTPException(status_code=503, detail="Research agenda not initialised")
    return agenda


def _get_scheduler(request: Request) -> AsyncScheduler:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler


@router.get("/intelligence/agenda")
async def get_research_agenda(request: Request) -> dict:
    """Analyse ResearchMemory and return identified research gaps."""
    agenda = _get_agenda(request)
    report = await agenda.analyze()
    return report.model_dump()


@router.post("/intelligence/agenda/run")
async def run_agenda(request: Request) -> dict:
    """Generate agenda and submit high-priority items to the scheduler."""
    agenda = _get_agenda(request)
    scheduler = _get_scheduler(request)
    coordinator = getattr(request.app.state, "coordinator", None)

    report = await agenda.analyze()
    submitted: list[str] = []

    for item in report.items:
        if item.priority < 7:
            continue
        if coordinator is None:
            break

        _goal = item.goal
        _item_id = item.item_id

        async def _run_research(_g: str = _goal, _id: str = _item_id) -> None:
            try:
                agenda.mark_running(_id)
                await coordinator.coordinate(goal=_g)
                agenda.mark_completed(_id)
            except Exception as exc:
                logger.warning(
                    "agenda_item_failed",
                    extra={"item_id": _id, "error": str(exc)},
                )

        task_id = scheduler.submit(
            _run_research,
            name=f"agenda:{item.item_id}",
            priority=TaskPriority(min(10, item.priority)),
        )
        submitted.append(task_id)

    return {
        "total_items": len(report.items),
        "submitted": len(submitted),
        "task_ids": submitted,
        "low_confidence_topics": report.low_confidence_topics,
        "sparse_topics": report.sparse_topics,
    }

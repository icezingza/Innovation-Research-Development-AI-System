import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_coordinator, get_event_bus
from src.infrastructure.event_bus import RuntimeEventBus
from src.orchestration.agent_coordinator import AgentCoordinator, CoordinatedResult

router = APIRouter(prefix="/cognition", tags=["cognition"])
logger = logging.getLogger(__name__)


class CoordinateRequest(BaseModel):
    goal: str
    max_sub_questions: int = 3
    run_critique: bool = True


@router.post("/coordinate", response_model=CoordinatedResult)
async def coordinate(
    request: CoordinateRequest,
    coordinator: AgentCoordinator = Depends(get_coordinator),
) -> CoordinatedResult:
    return await coordinator.coordinate(goal=request.goal)


@router.get("/events/stats")
async def event_stats(
    bus: RuntimeEventBus = Depends(get_event_bus),
) -> dict:
    return {
        "total_events_published": bus.event_count,
        "total_subscribers": bus.subscriber_count(),
    }

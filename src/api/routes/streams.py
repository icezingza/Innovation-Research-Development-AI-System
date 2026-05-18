import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_stream_manager
from src.runtime.stream_manager import StreamManager
from src.agents.coordinator import AgentCoordinator

router = APIRouter(prefix="/streams", tags=["streams"])
logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 15.0  # seconds
_STREAM_TIMEOUT = 300.0  # 5 minutes max


@router.get("/workflows/{workflow_id}")
async def stream_workflow_progress(
    workflow_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
) -> StreamingResponse:
    """SSE stream of progress events for a running workflow.

    Connect before or immediately after submitting a workflow.
    Emits JSON-encoded event objects: {"type": "...", "data": {...}}.
    Stream closes when a {"type": "done"} event is received or after 5 min.
    """

    async def event_generator():
        queue = stream_manager.create_stream(workflow_id)
        deadline = asyncio.get_event_loop().time() + _STREAM_TIMEOUT
        try:
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=min(_KEEPALIVE_INTERVAL, remaining)
                    )
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        finally:
            stream_manager.cleanup(workflow_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/active")
async def list_active_streams(
    stream_manager: StreamManager = Depends(get_stream_manager),
) -> dict:
    return {"active_streams": stream_manager.active_streams()}


@router.get("/research")
async def stream_research(
    request: Request, query: str, tenant_id: str = "internal_001"
):
    """
    SSE Endpoint สำหรับพ่น 'ก้าวความคิด' (Thinking Loop) ออกสู่หน้าจอแบบ Real-time
    เชื่อมต่อ Coordinator เข้ากับ API เพื่อให้เห็นการทำงานของ AI แบบวินาทีต่อวินาที
    """
    memory = getattr(request.app.state, "memory", None)
    inference = getattr(request.app.state, "inference", None)
    embedding = getattr(request.app.state, "embedding", None)

    coordinator = AgentCoordinator(
        tenant_id=tenant_id,
        memory=memory,
        inference=inference,
        embedding=embedding,
    )

    async def event_generator():
        async for message in coordinator.coordinate_research(query):
            if await request.is_disconnected():
                break
            yield {"data": message}

    return EventSourceResponse(event_generator())

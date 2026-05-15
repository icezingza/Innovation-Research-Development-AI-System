from typing import Any

from fastapi import APIRouter, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

router = APIRouter(tags=["observability"])


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    errors: dict[str, str] = getattr(request.app.state, "service_errors", {})
    status = "degraded" if errors else "healthy"
    return {"runtime": status, "unavailable_services": list(errors.keys())}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

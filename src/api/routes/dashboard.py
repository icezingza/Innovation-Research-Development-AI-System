"""Dashboard HTML pages — served as static files (templates render client-side via JS)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"


@router.get("/trace/{task_id}", response_class=HTMLResponse)
async def trace_dashboard(task_id: str) -> FileResponse:
    """Audit trail timeline dashboard. task_id is passed via URL; JS reads it."""
    return FileResponse(TEMPLATES_DIR / "trace_dashboard.html", media_type="text/html")


@router.get("/roi", response_class=HTMLResponse)
async def roi_dashboard() -> FileResponse:
    """ROI savings dashboard — tenant_id passed as query param, read by JS."""
    return FileResponse(TEMPLATES_DIR / "roi_dashboard.html", media_type="text/html")


@router.get("/finops/{tenant_id}", response_class=HTMLResponse)
async def finops_dashboard(tenant_id: str) -> FileResponse:
    """FinOps quota + cost dashboard. tenant_id from URL; JS extracts via window.location."""
    return FileResponse(TEMPLATES_DIR / "finops_dashboard.html", media_type="text/html")

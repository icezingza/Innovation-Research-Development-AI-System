from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/trace/{task_id}", response_class=HTMLResponse)
async def trace_dashboard(request: Request, task_id: str):
    return templates.TemplateResponse("trace_dashboard.html", {"request": request, "task_id": task_id})

@router.get("/finops/{tenant_id}", response_class=HTMLResponse)
async def finops_dashboard(request: Request, tenant_id: str):
    return templates.TemplateResponse("finops_dashboard.html", {"request": request, "tenant_id": tenant_id})

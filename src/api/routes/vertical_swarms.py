import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from src.api.routes.auth import get_current_user
from src.swarms.fintech_swarm import FintechSwarm
from src.swarms.legal_swarm import LegalSwarm

router = APIRouter(prefix="/swarms", tags=["vertical-swarms"])
logger = logging.getLogger(__name__)


# ── Request models ────────────────────────────────────────────────────────────

class FintechAnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=10, description="Risk query or transaction description")
    transaction_data: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured transaction metadata (e.g. days_overdue, amount)",
    )


class LegalAuditRequest(BaseModel):
    contract_text: str = Field(..., min_length=20, description="Full contract text to audit")
    query: str = Field(
        default="",
        description="Optional specific legal question about the contract",
    )


class PDPACheckRequest(BaseModel):
    data_flows: list[str] = Field(
        ...,
        min_length=1,
        description="List of data flow descriptions to scan for PDPA obligations",
    )


# ── SSE helper ────────────────────────────────────────────────────────────────

def _sse_stream(generator):
    """Wrap an async generator into SSE-formatted StreamingResponse."""

    async def event_stream():
        async for event in generator:
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Fintech endpoints ─────────────────────────────────────────────────────────

@router.post("/fintech/analyze")
async def fintech_analyze(
    body: FintechAnalyzeRequest,
    request: Request,
    _: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a bank-grade risk analysis for the given query.

    Returns SSE events progressing through:
    Red Team Guard → FintechKnowledgeRetriever → Circuit Breaker →
    ConflictResolver → MetaLearner → risk_assessment_complete

    The final event's ``report.bundle_hash`` is SHA-256 tamper-evident.
    """
    memory = getattr(request.app.state, "research_memory", None)
    inference = getattr(request.app.state, "inference", None)
    embedding = getattr(request.app.state, "embedding", None)
    tenant_id = getattr(request.state, "tenant_id", "default")

    swarm = FintechSwarm(
        tenant_id=tenant_id,
        memory=memory,
        inference=inference,
        embedding=embedding,
    )
    return _sse_stream(swarm.analyze_risk(body.query, body.transaction_data))


@router.get("/fintech/template")
async def fintech_template(_: dict = Depends(get_current_user)) -> dict:
    """Return the Fintech Swarm product specification."""
    from src.swarms.catalog import get_swarm_catalog
    catalog = get_swarm_catalog()
    template = catalog.get("fintech")
    if template is None:
        return {"id": "fintech", "name": "Fintech Swarm", "domain": "finance"}
    return {
        "id": template.id,
        "name": template.name,
        "domain": template.domain,
        "description": template.description,
        "regulatory_tags": template.regulatory_tags,
        "system_prompt": template.system_prompt,
    }


# ── Legal endpoints ───────────────────────────────────────────────────────────

@router.post("/legal/audit")
async def legal_audit(
    body: LegalAuditRequest,
    request: Request,
    _: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a contract audit with PDPA compliance mapping.

    Returns SSE events progressing through:
    LegalGraphExplorer → ConflictResolver → MetaLearner → contract_audit_complete

    The final event's ``report.bundle_hash`` is SHA-256 tamper-evident.
    """
    memory = getattr(request.app.state, "research_memory", None)
    inference = getattr(request.app.state, "inference", None)
    tenant_id = getattr(request.state, "tenant_id", "default")

    swarm = LegalSwarm(tenant_id=tenant_id, memory=memory, inference=inference)
    return _sse_stream(swarm.audit_contract(body.contract_text, body.query))


@router.post("/legal/pdpa-check")
async def legal_pdpa_check(
    body: PDPACheckRequest,
    request: Request,
    _: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a focused PDPA compliance scan for a list of data flow descriptions."""
    memory = getattr(request.app.state, "research_memory", None)
    inference = getattr(request.app.state, "inference", None)
    tenant_id = getattr(request.state, "tenant_id", "default")

    swarm = LegalSwarm(tenant_id=tenant_id, memory=memory, inference=inference)
    return _sse_stream(swarm.check_pdpa(body.data_flows))


@router.get("/legal/template")
async def legal_template(_: dict = Depends(get_current_user)) -> dict:
    """Return the Legal Swarm product specification."""
    from src.swarms.catalog import get_swarm_catalog
    catalog = get_swarm_catalog()
    template = catalog.get("legal")
    if template is None:
        return {"id": "legal", "name": "Legal Research Swarm", "domain": "legal"}
    return {
        "id": template.id,
        "name": template.name,
        "domain": template.domain,
        "description": template.description,
        "regulatory_tags": template.regulatory_tags,
        "system_prompt": template.system_prompt,
    }

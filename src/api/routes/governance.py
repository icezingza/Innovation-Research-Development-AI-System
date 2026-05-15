from fastapi import APIRouter, Depends

from src.api.dependencies import get_audit_log
from src.governance.audit_log import GovernanceAuditLog

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/audit")
async def get_audit_log(
    limit: int = 100,
    audit_log: GovernanceAuditLog = Depends(get_audit_log),
) -> dict:
    entries = await audit_log.get_recent(limit=limit)
    return {
        "entries": [e.model_dump() for e in entries],
        "count": len(entries),
    }

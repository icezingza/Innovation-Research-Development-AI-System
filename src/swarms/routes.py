from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from src.api.routes.auth import get_current_user
from src.security.auth_utils import RequireRole
from src.security.rls import get_rls_db
from src.swarms.catalog import get_swarm_catalog
from src.swarms.models import TenantSwarm

router = APIRouter(prefix="/swarms", tags=["swarms"])

@router.get("")
async def list_swarms(
    current_user=Depends(get_current_user)
):
    catalog = get_swarm_catalog()
    return [
        {"id": t.id, "name": t.name, "domain": t.domain, "description": t.__dict__.get("description","")}
        for t in catalog.list()
    ]

@router.post("/tenants/{tenant_id}/activate")
async def activate_swarm(
    tenant_id: str,
    template_id: str,
    db=Depends(get_rls_db),
    current_user=Depends(get_current_user)
):
    RequireRole(["admin"])(current_user)

    catalog = get_swarm_catalog()
    if template_id not in catalog.templates:
        raise HTTPException(404, "Template not found")

    # Deactivate existing
    result = await db.execute(select(TenantSwarm).filter(
        TenantSwarm.tenant_id == tenant_id,
        TenantSwarm.is_active == True
    ))
    existing = result.scalars().all()
    for sw in existing:
        sw.is_active = False
        sw.deactivated_at = datetime.now(UTC)

    # Activate new
    new_swarm = TenantSwarm(
        tenant_id=tenant_id,
        template_id=template_id
    )
    db.add(new_swarm)
    await db.commit()
    return {"status": "activated", "template": template_id}

@router.get("/tenants/{tenant_id}/active")
async def get_active_swarm(
    tenant_id: str,
    db=Depends(get_rls_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(select(TenantSwarm).filter(
        TenantSwarm.tenant_id == tenant_id,
        TenantSwarm.is_active == True
    ))
    sw = result.scalars().first()
    if not sw:
        raise HTTPException(404, "No active swarm")
    return {"template_id": sw.template_id, "activated_at": sw.activated_at.isoformat()}

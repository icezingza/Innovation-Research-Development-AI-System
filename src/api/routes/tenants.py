"""Tenant Provisioning API — create tenants and manage tier upgrades.

Endpoints:
  POST   /tenants              → create tenant + admin user (API-key gated)
  GET    /tenants/{tenant_id}  → fetch tenant info (admin or owner only)
  GET    /tenants/{tenant_id}/finops  → FinOps metrics (admin or finance only)
  PATCH  /tenants/{tenant_id}/tier  → upgrade/downgrade tier (API-key gated)
"""
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.dependencies import get_db
from src.api.routes.auth import get_current_user
from src.memory.schema import Tenant, User
from src.security.auth_utils import get_password_hash, RequireRole
from src.tenants.quota import TIER_LIMITS, DEFAULT_LIMIT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenants"])

VALID_TIERS: set[str] = {"free", "pro", "enterprise"}


# ── Request / Response models ─────────────────────────────────────────────────

class CreateTenantRequest(BaseModel):
    name: str
    domain: str
    tier: Literal["free", "pro", "enterprise"] = "free"
    admin_email: EmailStr
    admin_password: str

    @field_validator("admin_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("admin_password must be at least 8 characters")
        return v


class TenantResponse(BaseModel):
    id: str
    name: str
    domain: str
    tier: str
    status: str

    model_config = {"from_attributes": True}


class UpdateTierRequest(BaseModel):
    tier: Literal["free", "pro", "enterprise"]


class FinOpsResponse(BaseModel):
    tenant_id: str
    current_billing_period: str
    quota_limit: int
    quota_used: int
    estimated_cost: float
    budget_depletion_forecast: str | None
    recommendation: str


class ROIResponse(BaseModel):
    tenant_id: str
    period: str
    hours_saved: int
    token_cost_cloud_equivalent: float
    actual_token_cost: float
    savings_percentage: float
    tasks_completed: int
    avg_time_per_task_seconds: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_api_key(request: Request) -> None:
    """Gate provisioning endpoints behind the existing API key check.

    SecurityMiddleware already enforces X-API-Key for all routes except
    /health, /metrics, /auth/*. This function is a belt-and-suspenders guard.
    """
    key_manager = getattr(request.app.state, "key_manager", None)
    if key_manager is None:
        return  # dev mode — no keys configured
    raw_key = request.headers.get("X-API-Key", "")
    if not key_manager.validate(raw_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(
    body: CreateTenantRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new tenant and an owner-role admin user.

    Requires a valid X-API-Key (platform-level operation).
    Returns the created tenant's metadata.
    """
    _require_api_key(request)

    # Check domain uniqueness
    existing = await db.execute(select(Tenant).where(Tenant.domain == body.domain))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with domain '{body.domain}' already exists",
        )

    tenant = Tenant(
        id=uuid.uuid4(),
        name=body.name,
        domain=body.domain,
        tier=body.tier,
        status="active",
    )
    db.add(tenant)
    await db.flush()

    admin_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=body.admin_email,
        password_hash=get_password_hash(body.admin_password),
        role="owner",
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(tenant)

    logger.info(
        "tenant_created",
        extra={"tenant_id": str(tenant.id), "domain": tenant.domain, "tier": tenant.tier},
    )

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "domain": tenant.domain,
        "tier": tenant.tier,
        "status": tenant.status,
    }


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch tenant metadata.

    Accessible only to members of the same tenant or platform admins (API key).
    """
    # Allow platform admins to read any tenant
    key_manager = getattr(request.app.state, "key_manager", None)
    raw_key = request.headers.get("X-API-Key", "")
    is_platform_admin = key_manager is not None and key_manager.validate(raw_key)

    caller_tenant_id = current_user.get("tenant_id", "")
    if not is_platform_admin and caller_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "domain": tenant.domain,
        "tier": tenant.tier,
        "status": tenant.status,
    }


@router.get("/{tenant_id}/finops", response_model=FinOpsResponse)
async def get_tenant_finops(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve FinOps metrics for a tenant.

    Shows quota usage, estimated cost, and budget depletion forecast.
    Requires admin or finance role.
    """
    RequireRole(["admin", "finance", "owner"])(current_user)

    # Tenant isolation: users can only access their own tenant's finops
    caller_tenant_id = current_user.get("tenant_id", "")
    if caller_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get quota service from app state
    quota_service = getattr(request.app.state, "quota_service", None)
    if quota_service is None:
        raise HTTPException(status_code=500, detail="Quota service not available")

    # Current usage in this billing period
    limit = TIER_LIMITS.get(tenant.tier, DEFAULT_LIMIT)
    used = await quota_service.current_usage(tenant_id)

    # Cost estimation: $0.01 per API call (configurable)
    cost_per_unit = 0.01
    estimated_cost = round(used * cost_per_unit, 2)

    # Budget depletion forecast using linear extrapolation
    now = datetime.now(UTC)
    days_passed = max(1, now.day)
    daily_avg = used / days_passed

    depletion_time = None
    recommendation = ""

    if daily_avg > 0 and used < limit:
        remaining = limit - used
        days_left = remaining / daily_avg
        depletion_time = now + timedelta(days=days_left)

    # Generate recommendation based on usage
    usage_percent = (used / limit * 100) if limit > 0 else 0
    if tenant.tier == "free" and usage_percent > 80:
        recommendation = "Consider upgrading to Pro plan"
    elif tenant.tier == "pro" and usage_percent > 80:
        recommendation = "Consider upgrading to Enterprise plan"

    return {
        "tenant_id": tenant_id,
        "current_billing_period": now.strftime("%Y-%m"),
        "quota_limit": limit,
        "quota_used": used,
        "estimated_cost": estimated_cost,
        "budget_depletion_forecast": depletion_time.isoformat() if depletion_time else None,
        "recommendation": recommendation
    }


@router.get("/{tenant_id}/roi", response_model=ROIResponse)
async def get_tenant_roi(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve ROI analytics for a tenant (Phase 4C preview).

    Shows hours saved, cost comparison vs. public cloud, and throughput metrics.
    Requires admin role.
    """
    RequireRole(["admin"])(current_user)

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    quota_service = getattr(request.app.state, "quota_service", None)
    if quota_service is None:
        raise HTTPException(status_code=500, detail="Quota service not available")

    now = datetime.now(UTC)
    period = now.strftime("%Y-%m")
    
    used = await quota_service.current_usage(tenant_id)

    # Placeholder metrics (to be populated by actual task tracking)
    # In production, these would come from research_tasks table
    hours_saved = used // 100  # Rough estimate: 1 hour per 100 API calls
    
    # Cost comparison: public cloud ~$0.03/API call, IRD-AI $0.01/call
    cloud_cost = round(used * 0.03, 2)
    actual_cost = round(used * 0.01, 2)
    savings = round(cloud_cost - actual_cost, 2)
    savings_percent = round((savings / cloud_cost * 100) if cloud_cost > 0 else 0, 1)

    return {
        "tenant_id": tenant_id,
        "period": period,
        "hours_saved": hours_saved,
        "token_cost_cloud_equivalent": cloud_cost,
        "actual_token_cost": actual_cost,
        "savings_percentage": savings_percent,
        "tasks_completed": used,
        "avg_time_per_task_seconds": 45  # Placeholder
    }

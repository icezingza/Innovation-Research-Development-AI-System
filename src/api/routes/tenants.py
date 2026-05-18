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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_db
from src.api.routes.auth import get_current_user
from src.memory.schema import ResearchTask, Tenant, User
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
    edge_hardware_depreciation: float | None = None


class ROIResponse(BaseModel):
    tenant_id: str
    period: str
    hours_saved: int
    token_cost_cloud_equivalent: float
    actual_token_cost: float
    edge_hardware_depreciation_cost: float
    total_on_premise_cost: float
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )


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
        extra={
            "tenant_id": str(tenant.id),
            "domain": tenant.domain,
            "tier": tenant.tier,
        },
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

    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format"
        )

    caller_tenant_id = current_user.get("tenant_id", "")
    if not is_platform_admin and caller_tenant_id != str(tenant_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

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
    await RequireRole(["admin", "finance", "owner"])(current_user)

    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format"
        )

    # Tenant isolation: users can only access their own tenant's finops
    caller_tenant_id = current_user.get("tenant_id", "")
    if caller_tenant_id != str(tenant_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
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
    edge_hardware_depreciation = 100.0  # Assumed flat rate monthly allocation

    # Budget depletion forecast using linear extrapolation
    now = datetime.now(UTC)
    days_passed = max(1, now.day)
    daily_avg = used / days_passed

    depletion_time = None
    recommendation = ""

    if daily_avg > 0 and used < limit:
        remaining = limit - used
        days_left = remaining / daily_avg
        # Cap days_left at 3650 days (10 years) to prevent python datetime OverflowError
        days_left = min(days_left, 3650.0)
        depletion_time = now + timedelta(days=days_left)

    # Generate recommendation based on usage
    usage_percent = (used / limit * 100) if limit > 0 else 0
    if tenant.tier == "free" and usage_percent > 80:
        recommendation = "Consider upgrading to Pro plan"
    elif tenant.tier == "pro" and usage_percent > 80:
        recommendation = "Consider upgrading to Enterprise plan"

    return {
        "tenant_id": str(tenant_uuid),
        "current_billing_period": now.strftime("%Y-%m"),
        "quota_limit": limit,
        "quota_used": used,
        "estimated_cost": estimated_cost,
        "budget_depletion_forecast": depletion_time.isoformat()
        if depletion_time
        else None,
        "recommendation": recommendation,
        "edge_hardware_depreciation": edge_hardware_depreciation,
    }


@router.get("/{tenant_id}/finops/forecast")
async def get_finops_forecast(
    tenant_id: str,
    periods_ahead: int = 1,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Predict future token usage and cost for a tenant.

    Uses linear regression over recent quota history.
    Requires admin or owner role.
    """
    await RequireRole(["admin", "owner"])(current_user)

    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format"
        )

    caller_tenant_id = current_user.get("tenant_id", "")
    if caller_tenant_id != str(tenant_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    from src.billing.finops_predictor import FinOpsPredictor

    placeholder_history = [10_000, 15_000, 13_000, 18_000, 20_000]
    predictor = FinOpsPredictor()
    forecast = predictor.forecast(placeholder_history, periods_ahead=periods_ahead)
    return {
        "tenant_id": str(tenant_uuid),
        "forecast": forecast.model_dump(),
        "note": "history is placeholder; integrate quota_service for production data",
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
    await RequireRole(["admin", "finance", "auditor"])(current_user)

    import uuid

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant_id format"
        )

    # Tenant isolation
    caller_tenant_id = current_user.get("tenant_id", "")
    if caller_tenant_id != str(tenant_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    # --- ดึงข้อมูลการใช้งานจาก DB (เดือนปัจจุบัน) ---
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0)

    # นับจำนวน task ที่สร้างในเดือนนี้
    task_count_query = (
        select(func.count())
        .select_from(ResearchTask)
        .where(
            ResearchTask.tenant_id == tenant_uuid,
            ResearchTask.created_at >= start_of_month,
        )
    )
    task_count = await db.scalar(task_count_query) or 0

    # ดึง usage จาก Redis
    quota_service = request.app.state.quota_service
    api_calls_used = await quota_service.current_usage(str(tenant_uuid))

    # Constants
    AVG_HUMAN_HOURS_PER_TASK = 2.0
    CLOUD_COST_PER_1K_TOKENS = 0.03
    AVG_TOKENS_PER_TASK = 4000
    COST_PER_API_CALL = 0.01
    EDGE_DEPRECIATION_COST = (
        100.0  # Fixed monthly edge hardware depreciation per tenant
    )

    # --- คำนวณ ROI ---
    hours_saved = task_count * AVG_HUMAN_HOURS_PER_TASK
    cloud_cost = (
        api_calls_used * AVG_TOKENS_PER_TASK / 1000
    ) * CLOUD_COST_PER_1K_TOKENS
    actual_cost = api_calls_used * COST_PER_API_CALL
    total_on_premise_cost = actual_cost + EDGE_DEPRECIATION_COST

    savings_percentage = (
        round(((cloud_cost - total_on_premise_cost) / cloud_cost) * 100, 2)
        if cloud_cost > 0
        else 0.0
    )

    return {
        "tenant_id": str(tenant_uuid),
        "period": now.strftime("%Y-%m"),
        "tasks_completed": task_count,
        "api_calls_used": api_calls_used,
        "hours_saved": hours_saved,
        "token_cost_cloud_equivalent": round(cloud_cost, 2),
        "actual_token_cost": round(actual_cost, 2),
        "edge_hardware_depreciation_cost": EDGE_DEPRECIATION_COST,
        "total_on_premise_cost": round(total_on_premise_cost, 2),
        "savings_percentage": savings_percentage,
        "avg_time_per_task_seconds": 45.0,
        "recommendation": (
            "Your AI is saving significant cost vs. public cloud. Consider upgrading tier for more capacity."
            if savings_percentage > 50
            else "Efficiency gains are being tracked."
        ),
    }

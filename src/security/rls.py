"""RLS (Row Level Security) session dependency.

Sets the PostgreSQL session variable `app.tenant_id` before each DB operation
so that RLS policies can filter rows by tenant automatically.

Falls back to SYSTEM_TENANT_ID when no tenant context is present (e.g. in
heuristic mode tests that don't run TenantMiddleware).
"""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.api.dependencies import get_db
from src.tenants.context import SYSTEM_TENANT_ID


async def get_rls_db(request: Request, db: AsyncSession = Depends(get_db)):
    """Inject an AsyncSession with app.tenant_id set for RLS enforcement.

    Resolution order:
      1. request.state.tenant_id (set by get_current_user / auth middleware)
      2. request.state.tenant.tenant_id (set by TenantMiddleware)
      3. SYSTEM_TENANT_ID (fallback — unauthenticated or test context)
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        tenant_ctx = getattr(request.state, "tenant", None)
        tenant_id = getattr(tenant_ctx, "tenant_id", None)
    if not tenant_id:
        tenant_id = SYSTEM_TENANT_ID

    try:
        # PostgreSQL: set_config supports parameterized values
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(tenant_id)},
        )
    except Exception:
        # SQLite (test env) doesn't support set_config — ignore silently
        pass

    try:
        yield db
    finally:
        try:
            await db.execute(
                text("SELECT set_config('app.tenant_id', '', false)")
            )
        except Exception:
            pass

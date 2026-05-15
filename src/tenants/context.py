from dataclasses import dataclass

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class TenantContext:
    """Runtime context: which tenant and user made this request, and what role."""

    tenant_id: str
    user_id: str
    role: str  # owner | admin | member

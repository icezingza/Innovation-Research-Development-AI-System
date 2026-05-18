"""Per-tenant resource policy — maps tier to CPU/memory budget constraints.

These limits are enforced at two levels:
  1. Application layer: ResourceIsolationMiddleware tracks in-flight request
     concurrency and memory budget per tenant, rejecting excess with HTTP 429.
  2. Infrastructure layer: K8s ResourceQuota (see k8s/resource-quotas/) and
     Docker Compose resource limits enforce hard physical constraints.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourcePolicy:
    """Immutable resource constraints for a tenant tier."""

    tier: str
    max_concurrent_requests: int   # soft limit enforced by middleware
    max_memory_mb: int             # per-request memory budget hint (MB)
    cpu_weight: int                # relative CPU scheduling weight (1-100)
    max_reasoning_depth: int       # RecursiveReasoningLoop max_depth cap
    max_debate_rounds: int         # DebateRuntime max_rounds cap
    priority_class: str            # k8s PriorityClass name


# Tier definitions — enterprise gets dedicated headroom, free shares pool
RESOURCE_POLICIES: dict[str, ResourcePolicy] = {
    "free": ResourcePolicy(
        tier="free",
        max_concurrent_requests=2,
        max_memory_mb=256,
        cpu_weight=10,
        max_reasoning_depth=3,
        max_debate_rounds=1,
        priority_class="low-priority",
    ),
    "pro": ResourcePolicy(
        tier="pro",
        max_concurrent_requests=10,
        max_memory_mb=1024,
        cpu_weight=40,
        max_reasoning_depth=5,
        max_debate_rounds=3,
        priority_class="normal-priority",
    ),
    "enterprise": ResourcePolicy(
        tier="enterprise",
        max_concurrent_requests=50,
        max_memory_mb=4096,
        cpu_weight=100,
        max_reasoning_depth=10,
        max_debate_rounds=5,
        priority_class="high-priority",
    ),
}

DEFAULT_POLICY = RESOURCE_POLICIES["free"]


def get_policy(tier: str) -> ResourcePolicy:
    return RESOURCE_POLICIES.get(tier, DEFAULT_POLICY)

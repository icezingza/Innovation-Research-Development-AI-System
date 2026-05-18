"""Security & Compliance API — red team evidence and resource isolation status."""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from src.api.routes.audit_sdk import _require_auditor
from src.tenants.resource_isolation import get_resource_snapshot
from src.tenants.resource_policy import RESOURCE_POLICIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/red-team/report")
async def get_red_team_report(
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Generate and return a signed red team compliance evidence report.

    Runs all adversarial prompts in the corpus through RegulatoryGuard
    and returns a tamper-evident bundle suitable for PwC/Deloitte audit submission.

    Requires X-Auditor-Key header.
    """
    from src.security.red_team_runner import RedTeamRunner

    runner = RedTeamRunner()
    report = runner.run()
    signed = runner.to_signed_dict(report)

    logger.info(
        "red_team_report_requested",
        extra={
            "report_id": report.report_id,
            "verdict": report.overall_verdict,
            "block_rate": report.attack_block_rate_pct,
        },
    )
    return signed


@router.get("/resource-isolation/status")
async def get_isolation_status(
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Return current per-tenant resource isolation status and policy configuration.

    Provides evidence of hardware isolation enforcement for enterprise compliance.
    Requires X-Auditor-Key header.
    """
    snapshot = await get_resource_snapshot()
    policies = {
        tier: {
            "max_concurrent_requests": p.max_concurrent_requests,
            "max_memory_mb": p.max_memory_mb,
            "cpu_weight": p.cpu_weight,
            "max_reasoning_depth": p.max_reasoning_depth,
            "max_debate_rounds": p.max_debate_rounds,
            "priority_class": p.priority_class,
        }
        for tier, p in RESOURCE_POLICIES.items()
    }
    return {
        "active_tenant_concurrency": snapshot,
        "resource_policies": policies,
        "isolation_layer": "application + k8s-resource-quota",
        "noisy_neighbor_protection": "per-tenant concurrent request cap enforced by ResourceIsolationMiddleware",
    }

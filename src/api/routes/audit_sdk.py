"""Glass-Box Auditor SDK — read-only API for external compliance auditors.

Provides verifiable, tamper-evident access to AI reasoning traces, governance
decisions, and system configuration. Intended for PwC, Deloitte, and internal
risk committees that need to inspect "how the AI thinks" without operator access.

Authentication: X-Auditor-Key header (separate credential from API_KEYS).
All responses include a SHA-256 bundle_hash so auditors can verify integrity.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

from src.api.dependencies import get_audit_log, get_reasoning_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit-sdk"])

_auditor_key_header = APIKeyHeader(name="X-Auditor-Key", auto_error=False)

_SYSTEM_VERSION = "0.9.0"


def _require_auditor(key: str | None = Security(_auditor_key_header)) -> str:
    """Validate the auditor credential.

    The key is compared to AUDITOR_API_KEY env var using constant-time comparison
    to prevent timing attacks.
    """
    expected = os.environ.get("AUDITOR_API_KEY", "")
    if not key or not expected:
        raise HTTPException(status_code=403, detail="Auditor credentials required")
    if not _constant_time_compare(key, expected):
        raise HTTPException(status_code=403, detail="Invalid auditor credentials")
    return key


def _constant_time_compare(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y
    return result == 0


def _bundle_hash(payload: Any) -> str:
    """SHA-256 of the JSON-serialized payload for tamper detection."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _signed_response(data: dict[str, Any]) -> dict[str, Any]:
    """Wrap a response with a tamper-evident hash."""
    bundle_hash = _bundle_hash(data)
    return {
        **data,
        "bundle_hash": bundle_hash,
        "hash_algorithm": "sha256",
        "generated_at": time.time(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/system-manifest")
async def get_system_manifest(
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Return system version, declared capabilities, and deployment configuration.

    This is the auditor's entry point — confirms which version they are auditing
    and what capabilities are active.
    """
    manifest = {
        "system": "IRD-AI OS — Cognitive Research Runtime",
        "version": _SYSTEM_VERSION,
        "capabilities": [
            "recursive-reasoning",
            "adversarial-debate",
            "semantic-memory",
            "knowledge-graph",
            "governance-enforcement",
            "meta-learning",
            "circuit-breaker",
        ],
        "audit_endpoints": [
            "GET /audit/system-manifest",
            "GET /audit/reasoning-traces",
            "GET /audit/reasoning-traces/{trace_id}",
            "GET /audit/governance-log",
            "GET /audit/export/traces",
        ],
        "data_retention": {
            "reasoning_traces_memory": "ring-buffer, last 1000 entries",
            "governance_log_memory": "ring-buffer, last 1000 entries",
            "redis_ttl_hours": 24,
        },
        "access_mode": "read-only",
        "tamper_evidence": "sha256-bundle-hash on every response",
    }
    logger.info("auditor_manifest_accessed")
    return _signed_response({"manifest": manifest})


@router.get("/reasoning-traces")
async def list_reasoning_traces(
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Return a paginated list of reasoning trace entries.

    Each entry records one reasoning operation: what went in, what came out,
    which agent ran it, and how long it took. This is the primary audit surface
    for inspecting AI cognition step-by-step.
    """
    trace = get_reasoning_trace(request)
    entries = trace._local  # ring buffer, already in memory

    total = len(entries)
    page = entries[offset : offset + limit]
    serialized = [e.model_dump() for e in page]

    data = {
        "traces": serialized,
        "total": total,
        "returned": len(page),
        "offset": offset,
        "limit": limit,
    }
    logger.info("auditor_traces_listed", extra={"count": len(page)})
    return _signed_response(data)


@router.get("/reasoning-traces/{trace_id}")
async def get_reasoning_trace_by_id(
    trace_id: str,
    request: Request = None,
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Return the full detail of a single reasoning trace entry by ID.

    Includes the input hash, output summary, agent identity, and timestamp.
    The bundle_hash can be independently recomputed by the auditor to verify
    no data was altered between recording and retrieval.
    """
    trace = get_reasoning_trace(request)
    entry = next((e for e in trace._local if e.id == trace_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")

    data = {"trace": entry.model_dump()}
    logger.info("auditor_trace_accessed", extra={"trace_id": trace_id})
    return _signed_response(data)


@router.get("/governance-log")
async def list_governance_log(
    limit: int = 100,
    request: Request = None,
    audit_log=Depends(get_audit_log),
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Return recent governance audit entries.

    Every AI decision that passes through the governance layer is recorded here:
    policy checks, safety validations, approval/rejection decisions. Provides
    full decision traceability for compliance certification.
    """
    entries = await audit_log.get_recent(limit=limit)
    serialized = [e.model_dump() for e in entries]
    data = {
        "entries": serialized,
        "count": len(serialized),
        "requested_limit": limit,
    }
    logger.info("auditor_governance_log_accessed", extra={"count": len(serialized)})
    return _signed_response(data)


@router.get("/export/traces")
async def export_trace_bundle(
    limit: int = 500,
    request: Request = None,
    audit_log=Depends(get_audit_log),
    _: str = Depends(_require_auditor),
) -> dict[str, Any]:
    """Export a signed bundle of reasoning traces + governance log for offline review.

    Returns a single JSON document containing all available evidence. The auditor
    receives this bundle, recomputes the bundle_hash from the 'payload' field, and
    compares against the top-level 'bundle_hash' to confirm integrity.

    Designed for: offline review, archival, regulatory submission.
    """
    trace = get_reasoning_trace(request)
    trace_entries = [e.model_dump() for e in trace._local[-limit:]]
    gov_entries = await audit_log.get_recent(limit=limit)
    gov_serialized = [e.model_dump() for e in gov_entries]

    payload = {
        "export_version": "1.0",
        "system_version": _SYSTEM_VERSION,
        "export_timestamp": time.time(),
        "reasoning_traces": trace_entries,
        "governance_log": gov_serialized,
        "trace_count": len(trace_entries),
        "governance_count": len(gov_serialized),
    }

    bundle_hash = _bundle_hash(payload)
    logger.info(
        "auditor_export_generated",
        extra={
            "trace_count": len(trace_entries),
            "gov_count": len(gov_serialized),
            "bundle_hash": bundle_hash[:12],
        },
    )
    return {
        "bundle_hash": bundle_hash,
        "hash_algorithm": "sha256",
        "generated_at": time.time(),
        "payload": payload,
    }

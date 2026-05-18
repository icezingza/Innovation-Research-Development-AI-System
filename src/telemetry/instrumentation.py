"""Cognitive span instrumentation — consistent attribute schema for all OTel spans.

Usage:
    async with cognitive_span("fintech.risk_analysis", tenant_id="t1", domain="fintech"):
        ...

    @trace_cognitive_phase("legal.pdpa_check", domain="legal")
    async def my_fn(...): ...
"""

import functools
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from opentelemetry.trace import Span, StatusCode

from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


# ── Standard attribute key names ─────────────────────────────────────────────

class CognitiveAttr:
    """Canonical OTel attribute keys for the cognitive runtime.

    Using a class of constants prevents typos and enables IDE completion.
    All attributes use the `cognitive.*` namespace to avoid collisions with
    standard OTel semantic conventions.
    """
    TENANT_ID = "cognitive.tenant_id"
    DOMAIN = "cognitive.domain"
    PHASE = "cognitive.phase"
    AGENT_ID = "cognitive.agent_id"
    RISK_LEVEL = "cognitive.risk_level"
    PDPA_STATUS = "cognitive.pdpa_status"
    RUN_ID = "cognitive.run_id"
    QUERY_LENGTH = "cognitive.query_length"
    RESULT_COUNT = "cognitive.result_count"
    ERROR_TYPE = "cognitive.error_type"
    SWARM = "cognitive.swarm"


# ── Context manager ───────────────────────────────────────────────────────────

@asynccontextmanager
async def cognitive_span(
    name: str,
    *,
    tenant_id: str = "",
    domain: str = "",
    phase: str = "",
    agent_id: str = "",
    run_id: str = "",
    swarm: str = "",
    **extra_attrs: Any,
) -> AsyncIterator[Span]:
    """Async context manager that opens an OTel span with cognitive runtime attributes.

    Sets standard ``cognitive.*`` attributes on entry. Records any exception as
    a span error and re-raises it so callers still see the original exception.

    Example::

        async with cognitive_span("fintech.phase_1", tenant_id=tenant, domain="fintech") as span:
            result = await retriever.execute(payload)
            span.set_attribute(CognitiveAttr.RISK_LEVEL, result["risk_level"])
    """
    with tracer.start_as_current_span(name) as span:
        _set_standard_attrs(span, tenant_id, domain, phase, agent_id, run_id, swarm)
        for key, value in extra_attrs.items():
            try:
                span.set_attribute(f"cognitive.{key}", str(value))
            except Exception:
                pass
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.set_attribute(CognitiveAttr.ERROR_TYPE, type(exc).__name__)
            span.record_exception(exc)
            raise


# ── Decorator ─────────────────────────────────────────────────────────────────

def trace_cognitive_phase(
    span_name: str,
    *,
    domain: str = "",
    phase: str = "",
    swarm: str = "",
) -> Any:
    """Decorator that wraps an async function in a cognitive OTel span.

    Reads ``tenant_id`` from kwargs if present; falls back to empty string.

    Example::

        @trace_cognitive_phase("fintech.credit_scoring", domain="fintech", phase="1")
        async def score_credit(query: str, tenant_id: str = "") -> dict:
            ...
    """
    def decorator(fn: Any) -> Any:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tenant_id = kwargs.get("tenant_id", "")
            run_id = kwargs.get("run_id", "")
            async with cognitive_span(
                span_name,
                tenant_id=str(tenant_id),
                domain=domain,
                phase=phase,
                swarm=swarm,
                run_id=str(run_id),
            ):
                return await fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Span attribute helpers ────────────────────────────────────────────────────

def _set_standard_attrs(
    span: Span,
    tenant_id: str,
    domain: str,
    phase: str,
    agent_id: str,
    run_id: str,
    swarm: str,
) -> None:
    attrs = {
        CognitiveAttr.TENANT_ID: tenant_id,
        CognitiveAttr.DOMAIN: domain,
        CognitiveAttr.PHASE: phase,
        CognitiveAttr.AGENT_ID: agent_id,
        CognitiveAttr.RUN_ID: run_id,
        CognitiveAttr.SWARM: swarm,
    }
    for key, value in attrs.items():
        if value:
            try:
                span.set_attribute(key, value)
            except Exception:
                pass


def record_risk_outcome(span: Span, risk_level: str, result_count: int = 0) -> None:
    """Set risk and result attributes on an already-open span."""
    try:
        span.set_attribute(CognitiveAttr.RISK_LEVEL, risk_level)
        span.set_attribute(CognitiveAttr.RESULT_COUNT, result_count)
    except Exception:
        pass


def record_pdpa_outcome(span: Span, pdpa_status: str) -> None:
    """Set PDPA compliance status on an already-open span."""
    try:
        span.set_attribute(CognitiveAttr.PDPA_STATUS, pdpa_status)
    except Exception:
        pass

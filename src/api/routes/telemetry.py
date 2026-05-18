"""Telemetry status API — exposes OTel configuration and runtime health for observability audits."""

import logging
import os
import time

from fastapi import APIRouter, Depends
from opentelemetry import trace

from src.api.routes.auth import get_current_user

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
logger = logging.getLogger(__name__)

_STARTED_AT = time.time()


def _tracer_info() -> dict:
    provider = trace.get_tracer_provider()
    provider_name = type(provider).__name__

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    exporter = "otlp-grpc" if otlp_endpoint else "console"

    return {
        "provider": provider_name,
        "exporter": exporter,
        "otlp_endpoint": otlp_endpoint or None,
        "service_name": os.getenv("OTEL_SERVICE_NAME", "ird-ai-cognitive-runtime"),
        "service_version": os.getenv("SERVICE_VERSION", "0.9.0"),
        "deployment_environment": os.getenv("DEPLOYMENT_ENV", "development"),
        "instrumented_operations": [
            "agent.*.cycle",
            "cognitive_pipeline_process",
            "orchestration.research_workflow",
            "orchestration.debate",
            "reasoning.recursive_loop",
            "reasoning.reflect",
            "reasoning.analyze_contradictions",
            "research.evolve_hypothesis",
            "fintech.analyze_risk",
            "fintech.phase_1.knowledge_retrieval",
            "legal.phase_1.contract_analysis",
        ],
        "cognitive_attributes": [
            "cognitive.tenant_id",
            "cognitive.domain",
            "cognitive.phase",
            "cognitive.agent_id",
            "cognitive.risk_level",
            "cognitive.pdpa_status",
            "cognitive.run_id",
            "cognitive.query_length",
            "cognitive.result_count",
            "cognitive.swarm",
        ],
    }


@router.get("/status")
async def telemetry_status(_: dict = Depends(get_current_user)) -> dict:
    """Return current OpenTelemetry configuration and instrumentation coverage.

    Use this endpoint to verify that distributed tracing is active and correctly
    configured before connecting a Jaeger / Grafana Tempo backend.
    """
    uptime = round(time.time() - _STARTED_AT, 1)
    tracer_info = _tracer_info()

    return {
        "status": "active",
        "uptime_seconds": uptime,
        "tracing": tracer_info,
        "sla_target": "99.99%",
        "jaeger_ui": os.getenv("JAEGER_UI_URL", "http://localhost:16686"),
        "documentation": (
            "Set OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317 to route "
            "spans to Jaeger. All spans carry cognitive.* attributes for "
            "tenant-aware filtering."
        ),
    }


@router.get("/health")
async def telemetry_health() -> dict:
    """Lightweight liveness probe for the telemetry subsystem.

    Returns 200 with uptime and active exporter — no auth required so
    monitoring systems can poll without credentials.
    """
    tracer_info = _tracer_info()
    return {
        "healthy": True,
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        "exporter": tracer_info["exporter"],
        "provider": tracer_info["provider"],
    }

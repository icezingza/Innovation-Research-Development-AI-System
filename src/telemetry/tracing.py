import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_SERVICE_NAME = "ird-ai-cognitive-runtime"
_SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.9.0")


def configure_tracing() -> None:
    """Bootstrap OpenTelemetry with resource attributes.

    Routes spans to Jaeger when OTEL_EXPORTER_OTLP_ENDPOINT is set,
    otherwise falls back to console output for local development.
    """
    resource = Resource.create(
        {
            SERVICE_NAME: _SERVICE_NAME,
            SERVICE_VERSION: _SERVICE_VERSION,
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
            "cognitive.runtime": "antigravity",
        }
    )
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


tracer = trace.get_tracer(_SERVICE_NAME, _SERVICE_VERSION)

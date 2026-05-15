from prometheus_client import Counter, Gauge, Histogram

runtime_events = Counter(
    "runtime_events_total",
    "Total runtime events processed",
    ["event_type"],
)

active_agents = Gauge(
    "active_agents",
    "Number of currently active cognitive agents",
)

reasoning_latency = Histogram(
    "reasoning_latency_seconds",
    "Latency of reasoning operations",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

memory_sync_operations = Counter(
    "memory_sync_operations_total",
    "Total memory synchronization operations",
    ["layer"],
)


class RuntimeMetrics:
    """Captures and exposes runtime telemetry metrics."""

    def capture(self) -> dict[str, float]:
        return {
            "latency": 0.0,
            "memory_usage": 0.0,
            "active_agents": active_agents._value.get(),
            "reasoning_depth": 0.0,
        }

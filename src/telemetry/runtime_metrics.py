class RuntimeMetrics:
    """Captures runtime telemetry metrics."""

    def capture(self):
        return {
            'latency': 0.0,
            'memory_usage': 0.0,
            'active_agents': 0,
            'reasoning_depth': 0.0
        }

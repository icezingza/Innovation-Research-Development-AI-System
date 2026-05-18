"""Shared fixtures for the full-system evaluation suite.

All evaluation tests require live Docker Compose services
(redis, postgres, qdrant, neo4j). The `require_services` fixture
probes each service and skips the test session if any are down.
"""

import os
import socket
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


_SERVICE_PORTS = {
    "redis": ("localhost", 6379),
    "postgres": ("localhost", 5432),
    "qdrant": ("localhost", 6333),
    "neo4j": ("localhost", 7687),
}


def _probe_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


@pytest.fixture(scope="session")
def require_services() -> dict[str, bool]:
    """Skip the test if any required Docker service is unreachable."""
    results = {
        name: _probe_port(host, port) for name, (host, port) in _SERVICE_PORTS.items()
    }
    missing = [name for name, ok in results.items() if not ok]
    if missing:
        pytest.skip(
            f"Required services unreachable: {missing}. "
            f"Run `docker compose up -d` first."
        )
    return results


@pytest_asyncio.fixture(scope="session")
async def live_app(require_services):
    """Construct the FastAPI app with its real lifespan against live services."""
    os.environ.setdefault(
        "POSTGRES_URL", "postgresql+asyncpg://cognitive:cognitive@localhost/cognition"
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("QDRANT_HOST", "localhost")
    os.environ.setdefault("QDRANT_PORT", "6333")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")

    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest_asyncio.fixture(scope="session")
async def api_client(live_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=live_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

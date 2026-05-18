"""Smoke test: verify evaluation fixtures wire up correctly."""

import pytest


@pytest.mark.integration
def test_require_services_fixture_runs(require_services):
    assert require_services["redis"] is True
    assert require_services["postgres"] is True
    assert require_services["qdrant"] is True
    assert require_services["neo4j"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_client_health(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    # Endpoint returns {"runtime": "healthy"|"degraded", "unavailable_services": [...]}
    assert response.json()["runtime"] == "healthy"

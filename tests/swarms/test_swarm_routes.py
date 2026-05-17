"""Tests for GET /swarms/{template_id} detail endpoint."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.routes.auth import get_current_user
from src.swarms.routes import router as swarms_router


@pytest.fixture
def swarm_app():
    """Minimal FastAPI app with swarms router and mocked auth — no external services."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield

    application = FastAPI(lifespan=_lifespan)
    application.include_router(swarms_router)

    async def mock_get_current_user(request: Request):
        payload = {
            "sub": "00000000-0000-0000-0000-000000000002",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "role": "member",
        }
        request.state.tenant_id = payload["tenant_id"]
        request.state.user_id = payload["sub"]
        return payload

    application.dependency_overrides[get_current_user] = mock_get_current_user
    return application


def test_get_swarm_detail_fintech(swarm_app):
    with TestClient(swarm_app) as client:
        resp = client.get("/swarms/fintech")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "fintech"
    assert "kg_seed" in data
    assert "regulatory_tags" in data
    assert len(data["kg_seed"]["nodes"]) >= 5


def test_get_swarm_detail_not_found(swarm_app):
    with TestClient(swarm_app) as client:
        resp = client.get("/swarms/nonexistent")
    assert resp.status_code == 404

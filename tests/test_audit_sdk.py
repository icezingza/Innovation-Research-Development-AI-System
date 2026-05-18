"""Tests for the Glass-Box Auditor SDK (/audit/*)."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

AUDITOR_KEY = "test-auditor-key-xyz"
HEADERS = {"X-Auditor-Key": AUDITOR_KEY}


@pytest.fixture(autouse=True)
def set_auditor_env(monkeypatch):
    monkeypatch.setenv("AUDITOR_API_KEY", AUDITOR_KEY)


def test_system_manifest_requires_auditor_key(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/system-manifest")
    assert resp.status_code == 403


def test_system_manifest_rejects_wrong_key(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/system-manifest", headers={"X-Auditor-Key": "wrong"})
    assert resp.status_code == 403


def test_system_manifest_returns_manifest(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/system-manifest", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "manifest" in data
    assert data["manifest"]["version"] == "0.9.0"
    assert "capabilities" in data["manifest"]
    assert "bundle_hash" in data


def test_system_manifest_bundle_hash_is_valid(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/system-manifest", headers=HEADERS)
    data = resp.json()
    bundle_hash = data.pop("bundle_hash")
    data.pop("hash_algorithm")
    data.pop("generated_at")
    # Recompute hash from remaining payload
    recomputed = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert bundle_hash == recomputed


def test_reasoning_traces_requires_auth(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/reasoning-traces")
    assert resp.status_code == 403


def test_reasoning_traces_returns_list(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/reasoning-traces", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data
    assert "total" in data
    assert "bundle_hash" in data
    assert isinstance(data["traces"], list)


def test_reasoning_traces_pagination_params(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/reasoning-traces?limit=10&offset=0", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_reasoning_trace_by_id_not_found(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/reasoning-traces/nonexistent-id", headers=HEADERS)
    assert resp.status_code == 404


def test_governance_log_requires_auth(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/governance-log")
    assert resp.status_code == 403


def test_governance_log_returns_entries(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/governance-log", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "count" in data
    assert "bundle_hash" in data


def test_export_traces_requires_auth(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/export/traces")
    assert resp.status_code == 403


def test_export_traces_returns_signed_bundle(test_app):
    with TestClient(test_app) as client:
        resp = client.get("/audit/export/traces", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "bundle_hash" in data
    assert "payload" in data
    payload = data["payload"]
    assert "reasoning_traces" in payload
    assert "governance_log" in payload
    assert payload["export_version"] == "1.0"
    assert payload["system_version"] == "0.9.0"


def test_export_traces_bundle_hash_verifiable(test_app):
    """Auditor can independently verify integrity by recomputing the hash."""
    with TestClient(test_app) as client:
        resp = client.get("/audit/export/traces", headers=HEADERS)
    data = resp.json()
    claimed_hash = data["bundle_hash"]
    payload = data["payload"]
    recomputed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert claimed_hash == recomputed


def test_audit_endpoints_are_read_only(test_app):
    """Verify no write endpoints exist under /audit/."""
    with TestClient(test_app) as client:
        for method in (client.post, client.put, client.delete, client.patch):
            resp = method("/audit/system-manifest", headers=HEADERS)
            assert resp.status_code in (405, 403, 404, 422)

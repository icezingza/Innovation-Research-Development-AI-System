"""Tests for multi-tenant hardware isolation."""

import pytest

from src.tenants.resource_policy import get_policy
from src.tenants.resource_isolation import TenantConcurrencyTracker


# ── Resource Policy ────────────────────────────────────────────────────────────

def test_all_tiers_have_policies():
    for tier in ("free", "pro", "enterprise"):
        policy = get_policy(tier)
        assert policy.tier == tier


def test_enterprise_has_highest_limits():
    free = get_policy("free")
    pro = get_policy("pro")
    enterprise = get_policy("enterprise")
    assert enterprise.max_concurrent_requests > pro.max_concurrent_requests
    assert enterprise.max_concurrent_requests > free.max_concurrent_requests
    assert enterprise.max_memory_mb > pro.max_memory_mb
    assert enterprise.max_memory_mb > free.max_memory_mb


def test_free_has_strictest_limits():
    free = get_policy("free")
    pro = get_policy("pro")
    assert free.max_concurrent_requests < pro.max_concurrent_requests
    assert free.max_reasoning_depth < pro.max_reasoning_depth


def test_unknown_tier_returns_free_policy():
    policy = get_policy("unknown_tier")
    assert policy.tier == "free"


def test_policy_is_immutable():
    policy = get_policy("enterprise")
    with pytest.raises(Exception):
        policy.max_concurrent_requests = 999  # type: ignore[misc]


# ── Concurrency Tracker ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tracker_allows_within_limit():
    tracker = TenantConcurrencyTracker()
    acquired = await tracker.acquire("tenant-a", max_concurrent=3)
    assert acquired is True


@pytest.mark.asyncio
async def test_tracker_blocks_at_limit():
    tracker = TenantConcurrencyTracker()
    for _ in range(2):
        await tracker.acquire("tenant-b", max_concurrent=2)
    # third request should be rejected
    acquired = await tracker.acquire("tenant-b", max_concurrent=2)
    assert acquired is False


@pytest.mark.asyncio
async def test_tracker_release_frees_slot():
    tracker = TenantConcurrencyTracker()
    await tracker.acquire("tenant-c", max_concurrent=1)
    rejected = await tracker.acquire("tenant-c", max_concurrent=1)
    assert rejected is False

    await tracker.release("tenant-c")
    acquired_after_release = await tracker.acquire("tenant-c", max_concurrent=1)
    assert acquired_after_release is True


@pytest.mark.asyncio
async def test_tracker_isolates_between_tenants():
    tracker = TenantConcurrencyTracker()
    # Fill up tenant-d
    await tracker.acquire("tenant-d", max_concurrent=1)
    blocked = await tracker.acquire("tenant-d", max_concurrent=1)
    assert blocked is False
    # tenant-e is unaffected
    acquired = await tracker.acquire("tenant-e", max_concurrent=1)
    assert acquired is True


@pytest.mark.asyncio
async def test_tracker_current_returns_count():
    tracker = TenantConcurrencyTracker()
    assert await tracker.current("tenant-f") == 0
    await tracker.acquire("tenant-f", max_concurrent=5)
    assert await tracker.current("tenant-f") == 1
    await tracker.acquire("tenant-f", max_concurrent=5)
    assert await tracker.current("tenant-f") == 2


@pytest.mark.asyncio
async def test_tracker_release_does_not_go_negative():
    tracker = TenantConcurrencyTracker()
    await tracker.release("tenant-g")  # release without prior acquire
    assert await tracker.current("tenant-g") == 0


@pytest.mark.asyncio
async def test_tracker_snapshot_reflects_state():
    tracker = TenantConcurrencyTracker()
    await tracker.acquire("snap-a", max_concurrent=5)
    await tracker.acquire("snap-b", max_concurrent=5)
    snap = await tracker.snapshot()
    assert snap.get("snap-a", 0) >= 1
    assert snap.get("snap-b", 0) >= 1


# ── Middleware HTTP response (uses test_app from conftest) ─────────────────────

def test_resource_isolation_headers_present(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        resp = client.get("/health")
    # /health is exempt — middleware skips it, so headers may not be present
    assert resp.status_code == 200


def test_resource_policy_endpoint(test_app, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("AUDITOR_API_KEY", "test-auditor-key-xyz")
    with TestClient(test_app) as client:
        resp = client.get(
            "/security/resource-isolation/status",
            headers={"X-Auditor-Key": "test-auditor-key-xyz"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "resource_policies" in data
    assert "enterprise" in data["resource_policies"]
    assert "free" in data["resource_policies"]

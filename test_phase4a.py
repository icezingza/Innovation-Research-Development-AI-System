#!/usr/bin/env python3
"""Test script for Phase 4A endpoints"""
import json
from fastapi.testclient import TestClient
from src.api.main import app
from src.security.auth_utils import create_access_token

client = TestClient(app)

# Create a test JWT token for Tenant A with admin role
test_token = create_access_token({
    "tenant_id": "tenant-a",
    "user_id": "user-123",
    "role": "admin",
    "username": "testuser"
})

print("=" * 60)
print("PHASE 4A ENDPOINT TESTING")
print("=" * 60)
print(f"\nTest Token: {test_token[:50]}...")
print(f"Tenant ID: tenant-a")

# Test 1: Health check
print("\n[Test 1] GET /health")
response = client.get("/health")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Response: OK")

# Test 2: Get research trace
print("\n[Test 2] GET /research/tasks/task-001/trace")
headers = {"Authorization": f"Bearer {test_token}"}
response = client.get("/research/tasks/task-001/trace", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:200]}...")
else:
    print(f"Response: {response.json() if response.text else 'No response'}")

# Test 3: Get tenant finops
print("\n[Test 3] GET /tenants/tenant-a/finops")
response = client.get("/tenants/tenant-a/finops", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:300]}...")
else:
    print(f"Response: {response.json() if response.text else 'No response'}")

# Test 4: Access without token (should fail)
print("\n[Test 4] GET /research/tasks/task-001/trace (without auth - should fail)")
response = client.get("/research/tasks/task-001/trace")
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Response (Expected 401): OK")

print("\n" + "=" * 60)
print("TESTING COMPLETE")
print("=" * 60)

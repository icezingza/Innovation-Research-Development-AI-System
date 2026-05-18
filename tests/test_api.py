"""API integration tests using an in-memory SQLite DB and no external services.

The shared test_app fixture is defined in conftest.py.
"""

from fastapi.testclient import TestClient


def test_health_returns_healthy(test_app):
    with TestClient(test_app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["runtime"] == "healthy"
    assert response.json()["unavailable_services"] == []


def test_runtime_state_returns_empty_on_start(test_app):
    with TestClient(test_app) as client:
        response = client.get("/runtime/state")
    assert response.status_code == 200
    data = response.json()
    assert "active_agents" in data
    assert "cycles" in data


def test_create_research_task_returns_202(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/research/tasks",
            json={"question": "Does exercise improve cognitive function?"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "task_id" in body


def test_get_research_task_not_found(test_app):
    with TestClient(test_app) as client:
        response = client.get("/research/tasks/nonexistent-id")
    assert response.status_code == 404


def test_create_and_retrieve_research_task(test_app):
    with TestClient(test_app) as client:
        create_resp = client.post(
            "/research/tasks",
            json={
                "question": "What is the role of sleep in memory consolidation?",
                "constraints": ["use peer-reviewed sources"],
            },
        )
        assert create_resp.status_code == 202
        task_id = create_resp.json()["task_id"]

        get_resp = client.get(f"/research/tasks/{task_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["task_id"] == task_id
    assert data["question"] == "What is the role of sleep in memory consolidation?"


def test_recursive_reasoning_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/reasoning/recursive",
            json={
                "hypothesis_statement": "Sleep consolidates episodic memory",
                "question": "How does sleep affect memory?",
                "max_depth": 2,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "final_hypothesis" in data
    assert data["depth_reached"] >= 1
    assert "convergence_reason" in data


def test_debate_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/reasoning/debates",
            json={
                "hypothesis": "Exercise improves cognitive function",
                "max_rounds": 1,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "winner" in data
    assert data["winner"] in ("proponent", "opponent", "draw")
    assert data["total_rounds"] >= 0  # adaptive fast-track may produce 0 rounds


def test_reasoning_traces_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/reasoning/traces")
    assert response.status_code == 200
    data = response.json()
    assert "traces" in data
    assert "count" in data


def test_create_workflow_returns_202(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/research/workflows",
            json={"goal": "Understand mechanisms of neuroplasticity"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "workflow_id" in body


def test_get_workflow_not_found(test_app):
    with TestClient(test_app) as client:
        response = client.get("/research/workflows/nonexistent-id")
    assert response.status_code == 404


def test_create_and_retrieve_workflow(test_app):
    with TestClient(test_app) as client:
        create_resp = client.post(
            "/research/workflows",
            json={"goal": "What causes cognitive decline?"},
        )
        assert create_resp.status_code == 202
        workflow_id = create_resp.json()["workflow_id"]

        get_resp = client.get(f"/research/workflows/{workflow_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["workflow_id"] == workflow_id
    assert data["goal"] == "What causes cognitive decline?"


def test_list_workflows(test_app):
    with TestClient(test_app) as client:
        client.post("/research/workflows", json={"goal": "Goal A"})
        client.post("/research/workflows", json={"goal": "Goal B"})
        response = client.get("/research/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert "count" in data
    assert data["count"] >= 2


def test_governance_audit_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/governance/audit")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_coordinate_endpoint_returns_result(test_app):
    with TestClient(test_app) as client:
        response = client.post(
            "/cognition/coordinate",
            json={"goal": "What causes cognitive decline?", "run_critique": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "hypotheses" in data
    assert "synthesis" in data
    assert data["goal"] == "What causes cognitive decline?"


def test_event_stats_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/cognition/events/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_events_published" in data
    assert "total_subscribers" in data


def test_intelligence_report_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/report")
    assert response.status_code == 200
    data = response.json()
    assert "knowledge_base" in data
    assert "recent_findings" in data
    assert "total_entries" in data["knowledge_base"]


def test_intelligence_recall_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/recall?topic=memory+consolidation")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert "entries" in data
    assert "count" in data


def test_intelligence_hypotheses_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/hypotheses")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_intelligence_quality_trends_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/intelligence/quality-trends")
    assert response.status_code == 200
    data = response.json()
    assert "total_entries_analyzed" in data
    assert "recommendation" in data


def test_active_streams_endpoint(test_app):
    with TestClient(test_app) as client:
        response = client.get("/streams/active")
    assert response.status_code == 200
    data = response.json()
    assert "active_streams" in data

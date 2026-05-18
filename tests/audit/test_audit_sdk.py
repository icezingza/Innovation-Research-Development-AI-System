from src.audit.audit_sdk import AuditTrailExporter


SAMPLE_EVENTS = [
    {
        "timestamp": "2026-05-18T10:00:00",
        "agent": "HypothesisAgent",
        "action": "propose",
        "content": {"hypothesis": "AI reduces costs", "confidence": 0.72},
    },
    {
        "timestamp": "2026-05-18T10:01:00",
        "agent": "CritiqueAgent",
        "action": "critique",
        "content": "Lacks empirical evidence for cost claim.",
    },
]


def test_export_json_structure():
    exporter = AuditTrailExporter()
    result = exporter.export_json(task_id="task-001", events=SAMPLE_EVENTS)
    assert result["task_id"] == "task-001"
    assert result["total_events"] == 2
    assert result["events"] == SAMPLE_EVENTS
    assert "exported_at" in result


def test_export_html_contains_events():
    exporter = AuditTrailExporter()
    html = exporter.export_html(task_id="task-001", events=SAMPLE_EVENTS)
    assert "task-001" in html
    assert "HypothesisAgent" in html
    assert "CritiqueAgent" in html
    assert "<html" in html


def test_export_json_empty_events():
    exporter = AuditTrailExporter()
    result = exporter.export_json(task_id="empty-task", events=[])
    assert result["total_events"] == 0
    assert result["events"] == []

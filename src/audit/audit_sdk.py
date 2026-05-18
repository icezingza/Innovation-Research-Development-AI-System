from datetime import datetime, UTC


class AuditTrailExporter:
    """Formats reasoning trace events as Glass-Box audit artifacts."""

    def export_json(self, task_id: str, events: list[dict]) -> dict:
        return {
            "task_id": task_id,
            "total_events": len(events),
            "events": events,
            "exported_at": datetime.now(UTC).isoformat(),
        }

    def export_html(self, task_id: str, events: list[dict]) -> str:
        rows = ""
        for ev in events:
            content = ev.get("content", "")
            if isinstance(content, dict):
                content = ", ".join(f"{k}: {v}" for k, v in content.items())
            rows += (
                f"<tr>"
                f"<td>{ev.get('timestamp', '')}</td>"
                f"<td>{ev.get('agent', '')}</td>"
                f"<td>{ev.get('action', '')}</td>"
                f"<td>{content}</td>"
                f"</tr>\n"
            )
        return (
            f"<html><head><title>Audit Trail — {task_id}</title>"
            f"<style>body{{font-family:sans-serif;padding:2rem}}"
            f"table{{border-collapse:collapse;width:100%}}"
            f"th,td{{border:1px solid #ccc;padding:8px;text-align:left}}"
            f"th{{background:#f0f0f0}}</style></head><body>"
            f"<h1>Audit Trail</h1>"
            f"<p><strong>Task ID:</strong> {task_id}</p>"
            f"<table><thead><tr>"
            f"<th>Timestamp</th><th>Agent</th><th>Action</th><th>Content</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"</body></html>"
        )

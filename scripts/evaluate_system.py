"""Full system evaluation orchestrator.

Runs the 4-dimension pytest evaluation suite and produces:
- evaluation_report.json (machine-readable)
- evaluation_report.html (human-readable)

Usage:
    python scripts/evaluate_system.py
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON = REPO_ROOT / "evaluation_report.json"
REPORT_HTML = REPO_ROOT / "evaluation_report.html"
PYTEST_JSON = REPO_ROOT / ".pytest_report.json"

SERVICES = {
    "redis": ("localhost", 6379),
    "postgres": ("localhost", 5432),
    "qdrant": ("localhost", 6333),
    "neo4j": ("localhost", 7687),
}


def probe_services() -> dict[str, bool]:
    results = {}
    for name, (host, port) in SERVICES.items():
        try:
            with socket.create_connection((host, port), timeout=1.0):
                results[name] = True
        except OSError:
            results[name] = False
    return results


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def run_pytest(target: str) -> dict:
    """Run a single evaluation file and return parsed pytest output."""
    cmd = [
        sys.executable, "-m", "pytest",
        target,
        "-v",
        "-s",
        "--json-report",
        f"--json-report-file={PYTEST_JSON}",
        "--benchmark-disable",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if PYTEST_JSON.exists():
        data = json.loads(PYTEST_JSON.read_text())
        PYTEST_JSON.unlink()
    else:
        data = {"summary": {}, "tests": []}
    return {
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "summary": data.get("summary", {}),
        "stdout_tail": proc.stdout[-2000:],
    }


def build_html(report: dict) -> str:
    rows = []
    for dim, result in report["dimensions"].items():
        status = "PASS" if result["passed"] else "FAIL"
        color = "#2ecc71" if result["passed"] else "#e74c3c"
        summary = result.get("summary", {})
        rows.append(
            f"<tr><td>{dim}</td>"
            f"<td style='color:{color};font-weight:bold'>{status}</td>"
            f"<td>{summary.get('passed', 0)}/{summary.get('total', 0)} tests</td></tr>"
        )
    services_html = ", ".join(
        f"<span style='color:{'#2ecc71' if ok else '#e74c3c'}'>{name}</span>"
        for name, ok in report["services"].items()
    )
    overall_bg = "#d4edda" if report["overall"] == "PASS" else "#f8d7da"
    return f"""<!doctype html>
<html><head><title>Evaluation Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
th {{ background: #f5f5f5; }}
.overall {{ font-size: 24px; padding: 16px; background: {overall_bg}; }}
</style></head>
<body>
<h1>Full System Evaluation Report</h1>
<p><strong>Timestamp:</strong> {report['timestamp']}</p>
<p><strong>Git SHA:</strong> {report['git_sha']}</p>
<p><strong>Services:</strong> {services_html}</p>
<div class='overall'>Overall: <strong>{report['overall']}</strong></div>
<table>
<thead><tr><th>Dimension</th><th>Status</th><th>Tests</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""


def main() -> int:
    services = probe_services()
    if not all(services.values()):
        missing = [n for n, ok in services.items() if not ok]
        print(f"ERROR: services unreachable: {missing}", file=sys.stderr)
        print("Run `docker compose up -d` and try again.", file=sys.stderr)
        return 2

    targets = {
        "reasoning_quality": "tests/evaluation/test_reasoning_quality.py",
        "memory_persistence": "tests/evaluation/test_memory_persistence.py",
        "api_correctness": "tests/evaluation/test_api_correctness.py",
        "performance": "tests/evaluation/test_performance.py",
    }

    dimensions = {}
    for name, target in targets.items():
        print(f"==> Running {name} ...")
        dimensions[name] = run_pytest(target)

    overall = "PASS" if all(d["passed"] for d in dimensions.values()) else "FAIL"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "services": services,
        "dimensions": dimensions,
        "overall": overall,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2))
    REPORT_HTML.write_text(build_html(report))
    print(f"\n==> Overall: {overall}")
    print(f"==> JSON: {REPORT_JSON}")
    print(f"==> HTML: {REPORT_HTML}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

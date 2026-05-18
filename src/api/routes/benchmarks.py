"""Business KPI Benchmark API — run domain benchmark tasks and return investor-ready metrics."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from src.benchmarks.domain_benchmark import (
    VALID_DOMAINS,
    BenchmarkResult,
    DomainBenchmarkRunner,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


def _result_to_dict(r: BenchmarkResult) -> dict[str, Any]:
    return {
        "task_id": r.task_id,
        "domain": r.domain,
        "description": r.description,
        "kpi_category": r.kpi_category,
        "baseline_hours": r.baseline_hours,
        "estimated_ai_minutes": r.estimated_ai_minutes,
        "measured_heuristic_ms": r.measured_heuristic_ms,
        "speedup_factor": r.speedup_factor,
        "time_reduction_pct": r.time_reduction_pct,
        "kpi_statement": r.kpi_statement,
        "baseline_source": r.baseline_source,
    }


@router.get("/results")
async def get_benchmark_results(
    domain: str | None = Query(
        default=None,
        description="Domain filter: fintech | health | legal (omit for all)",
    ),
) -> dict[str, Any]:
    """Run benchmark tasks and return business KPI metrics.

    Measures actual heuristic pipeline execution time alongside
    industry-baseline manual process hours to compute speedup factors.

    Query param: ?domain=fintech | health | legal
    """
    if domain and domain not in VALID_DOMAINS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{domain}'. Must be one of: {sorted(VALID_DOMAINS)}",
        )

    runner = DomainBenchmarkRunner(research_workflow=None)  # heuristic mode for speed

    if domain:
        results = await runner.run_domain(domain)
        grouped = {domain: [_result_to_dict(r) for r in results]}
    else:
        all_results = await runner.run_all()
        grouped = {
            d: [_result_to_dict(r) for r in rs] for d, rs in all_results.items()
        }

    total_tasks = sum(len(v) for v in grouped.values())
    avg_speedup = (
        sum(r["speedup_factor"] for rs in grouped.values() for r in rs) / total_tasks
        if total_tasks
        else 0
    )

    logger.info(
        "benchmark_run_complete",
        extra={"domain": domain or "all", "total_tasks": total_tasks},
    )

    return {
        "summary": {
            "total_tasks": total_tasks,
            "average_speedup_factor": round(avg_speedup, 1),
            "mode": "heuristic",
            "note": "speedup_factor uses estimated_ai_minutes (LLM inference); "
                    "measured_heuristic_ms shows actual heuristic pipeline timing",
        },
        "results": grouped,
    }

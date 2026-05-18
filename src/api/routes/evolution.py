"""
NamoNexus Phase 10: Recursive Self-Evolution API
Exposes endpoints for self-architecture reflection, performance auto-tuning,
and autonomous resource allocation.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evolution", tags=["evolution"])

class EvolutionSnapshot(BaseModel):
    meta_reflection: Dict[str, Any]
    parameter_tuning: Dict[str, Any]
    finops_allocation: Dict[str, Any]

@router.post("/optimize")
async def trigger_self_evolution(request: Request) -> EvolutionSnapshot:
    """Trigger a recursive self-evolution cycle."""
    meta_engine = request.app.state.meta_reasoning
    learning_engine = request.app.state.adaptive_learning
    trace_log = request.app.state.reasoning_trace
    
    # 1. Self-Architecture Reflection
    traces = await trace_log.get_recent(limit=20)
    reflection = await meta_engine.reflect_on_execution(traces)
    
    # 2. Performance Auto-Tuning
    tuning = await learning_engine.self_optimization()
    
    # 3. Autonomous Resource Allocation (Internal Demo Tenant)
    allocation = await learning_engine.autonomous_resource_allocation("internal_001")
    
    logger.info("🧬 Phase 10 Self-Evolution Cycle Complete.")
    
    return EvolutionSnapshot(
        meta_reflection=reflection.model_dump(),
        parameter_tuning=tuning,
        finops_allocation=allocation
    )

@router.get("/status")
async def get_evolution_status(request: Request) -> Dict[str, Any]:
    """Get current evolutionary state of the cognitive runtime."""
    return {
        "engine": "RecursiveSelfEvolution",
        "version": "v1.0.0 (Phase 10)",
        "living_entity": True,
        "autonomous_tuning": "ACTIVE"
    }

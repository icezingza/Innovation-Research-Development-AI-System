from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import (
    get_debate_runtime,
    get_reasoning_trace,
    get_recursive_loop,
)
from src.orchestration.debate_runtime import DebateResult, DebateRuntime
from src.reasoning.reasoning_trace import ReasoningTrace
from src.reasoning.recursive_loop import (
    RecursiveConfig,
    RecursiveReasoningLoop,
    RecursiveReasoningResult,
)
from src.research.hypothesis_evolution import Hypothesis

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class RecursiveRequest(BaseModel):
    hypothesis_statement: str
    evidence: list[str] = []
    confidence: float = 0.5
    question: str = ""
    max_depth: int = 5
    convergence_threshold: float = 0.85


class DebateRequest(BaseModel):
    hypothesis: str
    max_rounds: int = 3


@router.post("/recursive", response_model=RecursiveReasoningResult)
async def run_recursive_reasoning(
    body: RecursiveRequest,
    loop: RecursiveReasoningLoop = Depends(get_recursive_loop),
) -> RecursiveReasoningResult:
    import uuid

    initial = Hypothesis(
        id=str(uuid.uuid4()),
        statement=body.hypothesis_statement,
        confidence=body.confidence,
        evidence=body.evidence or [
            f"Derived from: {body.question or body.hypothesis_statement}"
        ],
        generation=0,
    )
    config = RecursiveConfig(
        max_depth=body.max_depth,
        convergence_threshold=body.convergence_threshold,
    )
    loop._config = config
    return await loop.run(initial, question=body.question)


@router.post("/debates", response_model=DebateResult)
async def run_debate(
    body: DebateRequest,
    runtime: DebateRuntime = Depends(get_debate_runtime),
) -> DebateResult:
    return await runtime.debate(
        hypothesis=body.hypothesis,
        max_rounds=body.max_rounds,
    )


@router.get("/traces")
async def get_traces(
    limit: int = 50,
    trace: ReasoningTrace = Depends(get_reasoning_trace),
) -> dict[str, Any]:
    entries = await trace.get_recent(limit=limit)
    return {
        "count": len(entries),
        "traces": [e.model_dump() for e in entries],
    }

"""
NRE v5.0.0 Sovereign Edition — FastAPI Router for Swarm A/B Testing & Feedback Loops
Clean, type-safe, asynchronous, and Pydantic v2 compatible
"""

from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

from src.infrastructure.feedback_loop import Experiment

router = APIRouter(prefix="/experiments", tags=["experiments-feedback"])


# --- Pydantic v2 Schemas ---


class CreateExperimentSchema(BaseModel):
    id: str = Field(..., description="Unique Experiment identifier")
    name: str = Field(..., description="Human-readable experiment name")
    description: str = Field(..., description="Detailed description of hypothesis")
    variants: Dict[str, float] = Field(
        ..., description="Variant assignments with traffic percentage summing to 1.0"
    )
    metrics: List[str] = Field(..., description="Key metrics to monitor")
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: datetime = Field(..., description="End boundary of experiment")
    min_sample_size: int = Field(
        1000, description="Minimum exposures required for significance"
    )


class AssignVariantResponse(BaseModel):
    user_id: str
    experiment_id: str
    variant: str


class TrackConversionSchema(BaseModel):
    user_id: str
    experiment_id: str
    metric_name: str
    value: float = 1.0


class TrackExplicitRatingSchema(BaseModel):
    user_id: str
    session_id: str
    message_id: str
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    comment: Optional[str] = None


class TrackImplicitSignalSchema(BaseModel):
    user_id: str
    session_id: str
    message_id: str
    signal_type: str = Field(
        ...,
        description="Behavioral action (e.g. copy, share, upvote, downvote, regenerate)",
    )
    value: float = 1.0


class TrackSystemMetricSchema(BaseModel):
    message_id: str
    metric_name: str
    value: float
    threshold: Optional[float] = None


class ReportIssueSchema(BaseModel):
    user_id: str
    message_id: str
    issue_type: str = Field(
        ..., description="Category (e.g. harmful, incorrect, dangerous)"
    )
    description: str


# --- A/B Testing Endpoints ---


@router.post("/create", response_model=Dict[str, bool])
async def create_experiment(payload: CreateExperimentSchema, request: Request):
    """Instantiate a new A/B testing experiment targeting Prompt or Model variants."""
    ab_testing = getattr(request.app.state, "ab_testing", None)
    if not ab_testing:
        raise HTTPException(status_code=503, detail="A/B Testing service unavailable")

    experiment = Experiment(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        variants=payload.variants,
        metrics=payload.metrics,
        start_date=payload.start_date,
        end_date=payload.end_date,
        min_sample_size=payload.min_sample_size,
    )

    success = await ab_testing.create_experiment(experiment)
    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to initialize experiment configuration"
        )
    return {"success": success}


@router.get("/assign", response_model=AssignVariantResponse)
async def assign_variant(
    request: Request,
    user_id: str = Query(..., description="Unique client user reference"),
    experiment_id: str = Query(..., description="Experiment UUID"),
):
    """Dynamically assign a consistent variant to the client (Consistent Hashing)."""
    ab_testing = getattr(request.app.state, "ab_testing", None)
    if not ab_testing:
        raise HTTPException(status_code=503, detail="A/B Testing service unavailable")

    variant = await ab_testing.assign_variant(user_id, experiment_id)
    return {"user_id": user_id, "experiment_id": experiment_id, "variant": variant}


@router.post("/conversion", response_model=Dict[str, str])
async def track_conversion(payload: TrackConversionSchema, request: Request):
    """Increment conversion counters when users succeed in designated variant flows."""
    ab_testing = getattr(request.app.state, "ab_testing", None)
    if not ab_testing:
        raise HTTPException(status_code=503, detail="A/B Testing service unavailable")

    await ab_testing.track_conversion(
        user_id=payload.user_id,
        experiment_id=payload.experiment_id,
        metric_name=payload.metric_name,
        value=payload.value,
    )
    return {"status": "conversion_registered"}


@router.get("/results/{experiment_id}")
async def get_results(experiment_id: str, request: Request):
    """Expose analytical outcomes of A/B test variants alongside calculated Confidence Intervals."""
    ab_testing = getattr(request.app.state, "ab_testing", None)
    if not ab_testing:
        raise HTTPException(status_code=503, detail="A/B Testing service unavailable")

    results = await ab_testing.get_results(experiment_id)
    winner = await ab_testing.get_winner(experiment_id)

    return {
        "experiment_id": experiment_id,
        "results": {v: asdict(r) for v, r in results.items()} if results else {},
        "winner": winner,
    }


# --- Feedback Endpoints ---


@router.post("/feedback/rating", response_model=Dict[str, str])
async def track_explicit_rating(payload: TrackExplicitRatingSchema, request: Request):
    """Save explicit user star ratings (1-5) on generated responses."""
    collector = getattr(request.app.state, "feedback_collector", None)
    if not collector:
        raise HTTPException(status_code=503, detail="Feedback collector unavailable")

    await collector.track_explicit_rating(
        user_id=payload.user_id,
        session_id=payload.session_id,
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return {"status": "explicit_feedback_stored"}


@router.post("/feedback/signal", response_model=Dict[str, str])
async def track_implicit_signal(payload: TrackImplicitSignalSchema, request: Request):
    """Register implicit user interactions (copying, sharing, stop, skip, regenerate)."""
    collector = getattr(request.app.state, "feedback_collector", None)
    if not collector:
        raise HTTPException(status_code=503, detail="Feedback collector unavailable")

    await collector.track_implicit_signal(
        user_id=payload.user_id,
        session_id=payload.session_id,
        message_id=payload.message_id,
        signal_type=payload.signal_type,
        value=payload.value,
    )
    return {"status": "implicit_signal_stored"}


@router.post("/feedback/metric", response_model=Dict[str, str])
async def track_system_metric(payload: TrackSystemMetricSchema, request: Request):
    """Record backend computational statistics (latency, token usage) under the feedback loop."""
    collector = getattr(request.app.state, "feedback_collector", None)
    if not collector:
        raise HTTPException(status_code=503, detail="Feedback collector unavailable")

    await collector.track_system_metric(
        message_id=payload.message_id,
        metric_name=payload.metric_name,
        value=payload.value,
        threshold=payload.threshold,
    )
    return {"status": "system_metric_stored"}


@router.post("/feedback/issue", response_model=Dict[str, str])
async def report_issue(payload: ReportIssueSchema, request: Request):
    """Capture critical safety, bias or factual errors reported by consumers."""
    collector = getattr(request.app.state, "feedback_collector", None)
    if not collector:
        raise HTTPException(status_code=503, detail="Feedback collector unavailable")

    await collector.report_issue(
        user_id=payload.user_id,
        message_id=payload.message_id,
        issue_type=payload.issue_type,
        description=payload.description,
    )
    return {"status": "safety_issue_reported"}


@router.get("/feedback/aggregate/{message_id}")
async def get_aggregated_feedback(message_id: str, request: Request):
    """Aggregate multi-source explicit/implicit feedback to score overall quality of generated outputs."""
    aggregator = getattr(request.app.state, "feedback_aggregator", None)
    if not aggregator:
        raise HTTPException(status_code=503, detail="Feedback aggregator unavailable")

    aggregated = await aggregator.aggregate_feedback(message_id)
    return asdict(aggregated)

"""
NRE v5.0.0 Sovereign Edition — Swarm A/B Testing & Feedback Loop Infrastructure
Fully typed, 100% Async/Await, Pure Python (No NumPy dependency), and Prometheus integrated
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import math

from prometheus_client import Counter, Histogram

# Prometheus Observability Metrics
ab_test_counter = Counter(
    "ab_test_exposures", "A/B Test Exposures", ["experiment", "variant"]
)
ab_test_conversion = Counter(
    "ab_test_conversions", "A/B Test Conversions", ["experiment", "variant"]
)
ab_test_latency = Histogram("ab_test_latency", "A/B Test Response Time", ["variant"])

logger = logging.getLogger(__name__)


class VariantType(str, Enum):
    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"
    VARIANT_C = "variant_c"


@dataclass
class Experiment:
    """A/B Test Experiment Configuration"""

    id: str
    name: str
    description: str
    variants: Dict[str, float]  # variant_name: traffic_percentage
    metrics: List[str]
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    min_sample_size: int = 1000


@dataclass
class ExperimentResult:
    """A/B Test Analytical Outcome"""

    variant: str
    exposures: int
    conversions: int
    conversion_rate: float
    avg_latency: float
    confidence_interval: tuple
    is_significant: bool


class ABTestingManager:
    """Manages A/B Testing Traffic Split & Gradual rollouts using Consistent Hashing."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client
        self.experiments: Dict[str, Experiment] = {}

    async def create_experiment(self, experiment: Experiment) -> bool:
        """Register a new experiment in memory and Redis storage."""
        try:
            # Validate traffic allocation
            total_traffic = sum(experiment.variants.values())
            if abs(total_traffic - 1.0) > 0.01:
                raise ValueError(
                    f"Traffic allocation must sum to 1.0, got {total_traffic}"
                )

            # Store in Redis
            key = f"experiment:{experiment.id}"
            duration = int(
                (experiment.end_date - experiment.start_date).total_seconds()
            )
            duration = max(1, duration)  # Ensure non-zero

            # Serialize dates dynamically
            data = asdict(experiment)
            data["start_date"] = experiment.start_date.isoformat()
            data["end_date"] = experiment.end_date.isoformat()

            await self.redis.setex(key, duration, json.dumps(data))
            self.experiments[experiment.id] = experiment
            logger.info(f"Created experiment: {experiment.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            return False

    async def assign_variant(self, user_id: str, experiment_id: str) -> str:
        """Consistently assign user to a variant using MD5 hashing (Consistent Hashing)."""
        try:
            experiment = self.experiments.get(experiment_id)
            if not experiment or not experiment.is_active:
                return VariantType.CONTROL.value

            # Check if user already assigned
            cache_key = f"user_variant:{user_id}:{experiment_id}"
            cached = await self.redis.get(cache_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else str(cached)

            # Consistent hashing for absolute assignment consistency
            hash_input = f"{user_id}:{experiment_id}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            normalized = (hash_value % 10000) / 10000.0

            # Determine variant based on traffic allocation
            cumulative = 0.0
            for variant, traffic in experiment.variants.items():
                cumulative += traffic
                if normalized < cumulative:
                    # Cache assignment for 24h
                    await self.redis.setex(cache_key, 86400, variant)

                    # Increment exposure metrics
                    ab_test_counter.labels(
                        experiment=experiment_id, variant=variant
                    ).inc()
                    await self._track_exposure(experiment_id, variant)
                    return variant

            fallback = list(experiment.variants.keys())[0]
            return fallback
        except Exception as e:
            logger.error(f"Failed to assign variant: {e}")
            return VariantType.CONTROL.value

    async def track_conversion(
        self, user_id: str, experiment_id: str, metric_name: str, value: float = 1.0
    ) -> None:
        """Register metric conversion event for statistical sign-offs."""
        try:
            variant = await self.assign_variant(user_id, experiment_id)
            if not variant:
                return

            # Update Prometheus
            ab_test_conversion.labels(experiment=experiment_id, variant=variant).inc()

            key = f"conversion:{experiment_id}:{variant}:{metric_name}"
            await self.redis.hincrby(key, "count", 1)
            await self.redis.hincrbyfloat(key, "total_value", value)
            logger.debug(f"Tracked conversion: {experiment_id}/{variant}/{metric_name}")
        except Exception as e:
            logger.error(f"Failed to track conversion: {e}")

    async def _track_exposure(self, experiment_id: str, variant: str) -> None:
        key = f"exposure:{experiment_id}:{variant}"
        await self.redis.hincrby(key, "count", 1)

    async def get_results(self, experiment_id: str) -> Dict[str, ExperimentResult]:
        """Fetch real-time exposures, conversions and compute confidence intervals."""
        try:
            experiment = self.experiments.get(experiment_id)
            if not experiment:
                return {}

            results = {}
            for variant in experiment.variants.keys():
                exposure_key = f"exposure:{experiment_id}:{variant}"
                conversion_key = f"conversion:{experiment_id}:{variant}:primary"

                exp_val = await self.redis.hget(exposure_key, "count")
                conv_val = await self.redis.hget(conversion_key, "count")

                exposures = int(exp_val) if exp_val else 0
                conversions = int(conv_val) if conv_val else 0

                if exposures > 0:
                    conv_rate = conversions / exposures
                    ci = self._calculate_ci(conversions, exposures)
                    results[variant] = ExperimentResult(
                        variant=variant,
                        exposures=exposures,
                        conversions=conversions,
                        conversion_rate=conv_rate,
                        avg_latency=0.0,
                        confidence_interval=ci,
                        is_significant=exposures >= experiment.min_sample_size,
                    )
            return results
        except Exception as e:
            logger.error(f"Failed to get results: {e}")
            return {}

    def _calculate_ci(
        self, conversions: int, exposures: int, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Compute Wilson Score confidence interval in pure Python to eliminate NumPy."""
        if exposures == 0:
            return (0.0, 0.0)

        p = conversions / exposures
        z = 1.96  # 95% confidence level

        denominator = 1 + z**2 / exposures
        center = (p + z**2 / (2 * exposures)) / denominator
        margin = (
            z
            * math.sqrt((p * (1 - p) / exposures + z**2 / (4 * exposures**2)))
            / denominator
        )

        return (max(0.0, center - margin), min(1.0, center + margin))

    async def get_winner(self, experiment_id: str) -> Optional[str]:
        """Determine winning variant based on highest conversion rate and statistical sample."""
        results = await self.get_results(experiment_id)
        if len(results) < 2:
            return None

        best_variant = None
        best_rate = -1.0

        for variant, result in results.items():
            if result.is_significant and result.conversion_rate > best_rate:
                best_rate = result.conversion_rate
                best_variant = variant

        return best_variant


class FeatureFlagManager:
    """Robust dynamic feature toggles with gradual rollouts and Whitelisting policies."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    async def set_flag(
        self,
        flag_name: str,
        enabled: bool,
        rollout_percentage: float = 100.0,
        user_whitelist: Optional[List[str]] = None,
    ) -> None:
        flag_data = {
            "enabled": enabled,
            "rollout_percentage": rollout_percentage,
            "whitelist": user_whitelist or [],
            "updated_at": datetime.utcnow().isoformat(),
        }
        key = f"feature_flag:{flag_name}"
        await self.redis.set(key, json.dumps(flag_data))

    async def is_enabled(self, flag_name: str, user_id: str) -> bool:
        """Decide if a feature is enabled for a specific user."""
        key = f"feature_flag:{flag_name}"
        data = await self.redis.get(key)
        if not data:
            return False

        # Handle bytes vs string
        flag_str = data.decode() if isinstance(data, bytes) else str(data)
        flag = json.loads(flag_str)

        # Check absolute override
        if not flag.get("enabled", False):
            return False

        # Whitelist exception
        if user_id in flag.get("whitelist", []):
            return True

        # Hashed rollout logic
        hash_input = f"{user_id}:{flag_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        percentage = hash_value % 100

        return percentage < flag.get("rollout_percentage", 100.0)


class FeedbackType(str, Enum):
    EXPLICIT_RATING = "explicit_rating"  # 1-5 Stars
    IMPLICIT_POSITIVE = "implicit_positive"  # Copy, share, upvote
    IMPLICIT_NEGATIVE = "implicit_negative"  # Regenerate, edit, downvote
    REPORT_ISSUE = "report_issue"  # Content flags
    SYSTEM_METRIC = "system_metric"  # Latency, resource consumption


@dataclass
class FeedbackEvent:
    id: str
    user_id: str
    session_id: str
    message_id: str
    feedback_type: FeedbackType
    score: float  # Normalized 0.0 - 1.0
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class AggregatedFeedback:
    message_id: str
    total_feedback_count: int
    avg_explicit_rating: float
    positive_signals: int
    negative_signals: int
    issues_reported: int
    overall_score: float
    confidence: float


class FeedbackCollector:
    """Collects Explicit and Implicit signals into Redis and alerts on critical items."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client
        self.event_handlers: Dict[
            FeedbackType, List[Callable[[FeedbackEvent], Any]]
        ] = {}

    async def track_explicit_rating(
        self,
        user_id: str,
        session_id: str,
        message_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> None:
        try:
            # Normalize 1-5 stars rating to 0.0 - 1.0 score
            normalized_score = (rating - 1) / 4.0
            event = FeedbackEvent(
                id=f"feedback_{datetime.utcnow().timestamp()}",
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                feedback_type=FeedbackType.EXPLICIT_RATING,
                score=normalized_score,
                metadata={"rating": rating, "comment": comment},
                timestamp=datetime.utcnow(),
            )
            await self._store_event(event)
            await self._trigger_handlers(event)
            logger.info(f"Explicit rating: {rating}/5 for message {message_id}")
        except Exception as e:
            logger.error(f"Failed to track explicit rating: {e}")

    async def track_implicit_signal(
        self,
        user_id: str,
        session_id: str,
        message_id: str,
        signal_type: str,
        value: float = 1.0,
    ) -> None:
        try:
            positive_signals = {"copy", "share", "continue", "bookmark", "upvote"}
            negative_signals = {"regenerate", "edit", "stop", "downvote", "skip"}

            if signal_type in positive_signals:
                feedback_type = FeedbackType.IMPLICIT_POSITIVE
                score = 0.7
            elif signal_type in negative_signals:
                feedback_type = FeedbackType.IMPLICIT_NEGATIVE
                score = 0.3
            else:
                return

            event = FeedbackEvent(
                id=f"feedback_{datetime.utcnow().timestamp()}",
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                feedback_type=feedback_type,
                score=score,
                metadata={"signal_type": signal_type, "value": value},
                timestamp=datetime.utcnow(),
            )
            await self._store_event(event)
            await self._trigger_handlers(event)
            logger.debug(f"Implicit signal: {signal_type} for message {message_id}")
        except Exception as e:
            logger.error(f"Failed to track implicit signal: {e}")

    async def track_system_metric(
        self,
        message_id: str,
        metric_name: str,
        value: float,
        threshold: Optional[float] = None,
    ) -> None:
        try:
            if threshold:
                score = (
                    1.0
                    if value <= threshold
                    else max(0.0, 1.0 - (value - threshold) / threshold)
                )
            else:
                score = 0.5

            event = FeedbackEvent(
                id=f"metric_{datetime.utcnow().timestamp()}",
                user_id="system",
                session_id="system",
                message_id=message_id,
                feedback_type=FeedbackType.SYSTEM_METRIC,
                score=score,
                metadata={
                    "metric_name": metric_name,
                    "value": value,
                    "threshold": threshold,
                },
                timestamp=datetime.utcnow(),
            )
            await self._store_event(event)
        except Exception as e:
            logger.error(f"Failed to track system metric: {e}")

    async def report_issue(
        self, user_id: str, message_id: str, issue_type: str, description: str
    ) -> None:
        try:
            event = FeedbackEvent(
                id=f"issue_{datetime.utcnow().timestamp()}",
                user_id=user_id,
                session_id="",
                message_id=message_id,
                feedback_type=FeedbackType.REPORT_ISSUE,
                score=0.0,  # Highly critical negative
                metadata={
                    "issue_type": issue_type,
                    "description": description,
                },
                timestamp=datetime.utcnow(),
            )
            await self._store_event(event)
            await self._trigger_handlers(event)

            if issue_type in ["harmful", "dangerous"]:
                logger.critical(f"CRITICAL ISSUE REPORTED: {issue_type} - {message_id}")
        except Exception as e:
            logger.error(f"Failed to report issue: {e}")

    async def _store_event(self, event: FeedbackEvent) -> None:
        key = f"feedback:{event.message_id}"
        data = asdict(event)
        data["feedback_type"] = event.feedback_type.value
        data["timestamp"] = event.timestamp.isoformat()
        await self.redis.rpush(key, json.dumps(data))
        await self.redis.expire(key, 2592000)  # TTL of 30 days

    async def _trigger_handlers(self, event: FeedbackEvent) -> None:
        handlers = self.event_handlers.get(event.feedback_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Feedback trigger handler error: {e}")

    def register_handler(
        self, feedback_type: FeedbackType, handler: Callable[[FeedbackEvent], Any]
    ) -> None:
        if feedback_type not in self.event_handlers:
            self.event_handlers[feedback_type] = []
        self.event_handlers[feedback_type].append(handler)


class FeedbackAggregator:
    """Aggregates multi-source feedback events into single metrics using pure Python."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    async def aggregate_feedback(self, message_id: str) -> AggregatedFeedback:
        try:
            key = f"feedback:{message_id}"
            raw_events = await self.redis.lrange(key, 0, -1)
            if not raw_events:
                return AggregatedFeedback(
                    message_id=message_id,
                    total_feedback_count=0,
                    avg_explicit_rating=0.0,
                    positive_signals=0,
                    negative_signals=0,
                    issues_reported=0,
                    overall_score=0.5,
                    confidence=0.0,
                )

            events: List[FeedbackEvent] = []
            for raw in raw_events:
                raw_str = raw.decode() if isinstance(raw, bytes) else str(raw)
                d = json.loads(raw_str)
                d["timestamp"] = datetime.fromisoformat(d["timestamp"])
                d["feedback_type"] = FeedbackType(d["feedback_type"])
                events.append(FeedbackEvent(**d))

            explicit_ratings = [
                e.score
                for e in events
                if e.feedback_type == FeedbackType.EXPLICIT_RATING
            ]
            positive_signals = sum(
                1 for e in events if e.feedback_type == FeedbackType.IMPLICIT_POSITIVE
            )
            negative_signals = sum(
                1 for e in events if e.feedback_type == FeedbackType.IMPLICIT_NEGATIVE
            )
            issues = sum(
                1 for e in events if e.feedback_type == FeedbackType.REPORT_ISSUE
            )

            # Pure Python Weighted Average
            scores = []
            weights = []

            if explicit_ratings:
                avg_explicit = sum(explicit_ratings) / len(explicit_ratings)
                scores.append(avg_explicit)
                weights.append(3.0)
            else:
                avg_explicit = 0.0

            if (positive_signals + negative_signals) > 0:
                implicit_score = positive_signals / (
                    positive_signals + negative_signals
                )
                scores.append(implicit_score)
                weights.append(1.0)

            if issues > 0:
                scores.append(0.0)
                weights.append(2.0)

            if scores:
                weighted_sum = sum(s * w for s, w in zip(scores, weights))
                total_weight = sum(weights)
                overall_score = weighted_sum / total_weight if total_weight > 0 else 0.5
            else:
                overall_score = 0.5

            confidence = min(1.0, len(events) / 10.0)

            return AggregatedFeedback(
                message_id=message_id,
                total_feedback_count=len(events),
                avg_explicit_rating=avg_explicit,
                positive_signals=positive_signals,
                negative_signals=negative_signals,
                issues_reported=issues,
                overall_score=overall_score,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"Failed to aggregate feedback: {e}")
            return AggregatedFeedback(
                message_id=message_id,
                total_feedback_count=0,
                avg_explicit_rating=0.0,
                positive_signals=0,
                negative_signals=0,
                issues_reported=0,
                overall_score=0.5,
                confidence=0.0,
            )

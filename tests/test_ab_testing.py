"""
NRE v5.0.0 Sovereign Edition — Unit Tests and Simulations for Swarm A/B Testing & Feedback Loops
"""

import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.infrastructure.feedback_loop import (
    ABTestingManager,
    Experiment,
    FeatureFlagManager,
    FeedbackCollector,
    FeedbackAggregator,
    VariantType,
)


class MockRedis:
    """Mock Redis Client supporting asynchronous dictionary storage for testing contexts."""

    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}
        self.expirations: Dict[str, int] = {}

    async def get(self, key: str) -> Optional[bytes]:
        val = self.store.get(key)
        if val is None:
            return None
        return val.encode() if isinstance(val, str) else val

    async def set(self, key: str, value: Any) -> None:
        self.store[key] = value

    async def setex(self, key: str, seconds: int, value: Any) -> None:
        self.store[key] = value
        self.expirations[key] = seconds

    async def hincrby(self, key: str, field: str, increment: int) -> int:
        if key not in self.store:
            self.store[key] = {}
        current = self.store[key].get(field, 0)
        self.store[key][field] = current + increment
        return self.store[key][field]

    async def hincrbyfloat(self, key: str, field: str, increment: float) -> float:
        if key not in self.store:
            self.store[key] = {}
        current = self.store[key].get(field, 0.0)
        self.store[key][field] = current + increment
        return self.store[key][field]

    async def hget(self, key: str, field: str) -> Optional[bytes]:
        if key not in self.store:
            return None
        val = self.store[key].get(field)
        if val is None:
            return None
        return str(val).encode()

    async def rpush(self, key: str, value: Any) -> int:
        if key not in self.store:
            self.store[key] = []
        self.store[key].append(value)
        return len(self.store[key])

    async def lrange(self, key: str, start: int, end: int) -> List[bytes]:
        if key not in self.store:
            return []
        items = self.store[key]
        if end == -1:
            slice_items = items[start:]
        else:
            slice_items = items[start : end + 1]

        return [x.encode() if isinstance(x, str) else x for x in slice_items]

    async def expire(self, key: str, seconds: int) -> int:
        self.expirations[key] = seconds
        return 1


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


class TestABTesting:
    @pytest.mark.asyncio
    async def test_experiment_creation(self, mock_redis: MockRedis) -> None:
        manager = ABTestingManager(mock_redis)
        exp = Experiment(
            id="exp-001",
            name="Model Debate Swarm",
            description="Testing 3-agent vs 5-agent debate performance",
            variants={VariantType.CONTROL.value: 0.5, VariantType.VARIANT_A.value: 0.5},
            metrics=["accuracy", "latency"],
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            min_sample_size=10,
        )

        success = await manager.create_experiment(exp)
        assert success is True
        assert "exp-001" in manager.experiments

    @pytest.mark.asyncio
    async def test_experiment_traffic_validation(self, mock_redis: MockRedis) -> None:
        manager = ABTestingManager(mock_redis)
        exp = Experiment(
            id="exp-bad",
            name="Bad traffic experiment",
            description="Testing bad traffic total sum",
            variants={
                VariantType.CONTROL.value: 0.4,
                VariantType.VARIANT_A.value: 0.4,
            },  # Sum = 0.8
            metrics=["accuracy"],
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        success = await manager.create_experiment(exp)
        assert success is False

    @pytest.mark.asyncio
    async def test_consistent_hash_variant_assignment(
        self, mock_redis: MockRedis
    ) -> None:
        manager = ABTestingManager(mock_redis)
        exp = Experiment(
            id="exp-hash",
            name="Consistent Hash Test",
            description="Ensuring user lands on the same variant repeatedly",
            variants={
                VariantType.CONTROL.value: 0.5,
                VariantType.VARIANT_A.value: 0.5,
            },
            metrics=["latency"],
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=1),
            is_active=True,
        )
        await manager.create_experiment(exp)

        # Same user should consistently get the same variant
        user_1 = "user-alice-12345"
        variant_first = await manager.assign_variant(user_1, "exp-hash")

        for _ in range(10):
            variant_repeat = await manager.assign_variant(user_1, "exp-hash")
            assert variant_first == variant_repeat

        # Different users should map across allocations
        user_2 = "user-bob-98765"
        variant_user_2 = await manager.assign_variant(user_2, "exp-hash")
        assert variant_user_2 in [
            VariantType.CONTROL.value,
            VariantType.VARIANT_A.value,
        ]


class TestFeatureFlag:
    @pytest.mark.asyncio
    async def test_feature_flag_gradual_rollout(self, mock_redis: MockRedis) -> None:
        ff = FeatureFlagManager(mock_redis)
        await ff.set_flag(
            flag_name="dynamic_memory_routing",
            enabled=True,
            rollout_percentage=50.0,
            user_whitelist=["p_ice_vip"],
        )

        # Whitelist override check
        assert await ff.is_enabled("dynamic_memory_routing", "p_ice_vip") is True

        # Non-whitelist hashed rollout check
        enabled_count = 0
        total_checks = 100
        for i in range(total_checks):
            user_id = f"user_{i}"
            if await ff.is_enabled("dynamic_memory_routing", user_id):
                enabled_count += 1

        # Statistically, 50% rollout should yield ~40-60% active assignments
        assert 35 <= enabled_count <= 65


class TestFeedbackLoop:
    @pytest.mark.asyncio
    async def test_explicit_implicit_feedback_aggregation(
        self, mock_redis: MockRedis
    ) -> None:
        collector = FeedbackCollector(mock_redis)
        aggregator = FeedbackAggregator(mock_redis)
        msg_id = "msg_debate_reconcile_001"

        # Simulate multiple user explicit star ratings
        await collector.track_explicit_rating(
            user_id="user_1", session_id="s_01", message_id=msg_id, rating=5
        )
        await collector.track_explicit_rating(
            user_id="user_2", session_id="s_01", message_id=msg_id, rating=4
        )

        # Simulate user copy and share positive implicit signals
        await collector.track_implicit_signal(
            user_id="user_1", session_id="s_01", message_id=msg_id, signal_type="copy"
        )
        await collector.track_implicit_signal(
            user_id="user_3", session_id="s_01", message_id=msg_id, signal_type="share"
        )

        # Simulate system metric latency tracking
        await collector.track_system_metric(
            message_id=msg_id, metric_name="response_latency", value=4.2, threshold=5.0
        )

        # Aggregate the scores
        result = await aggregator.aggregate_feedback(msg_id)

        assert result.message_id == msg_id
        assert (
            result.total_feedback_count == 5
        )  # 2 explicit + 2 implicit + 1 system metric
        # Explicit ratings: (5 + 4) -> normalized scores are 1.0 (5 stars) and 0.75 (4 stars)
        # Average rating should be 4.5
        assert (
            result.avg_explicit_rating == 0.875
        )  # ((5-1)/4 + (4-1)/4) / 2 = (1.0 + 0.75) / 2 = 0.875
        assert result.positive_signals == 2
        assert result.negative_signals == 0
        assert result.issues_reported == 0
        assert (
            result.overall_score > 0.8
        )  # Strong score due to high ratings and positive signals
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_safety_issue_reporting(self, mock_redis: MockRedis) -> None:
        collector = FeedbackCollector(mock_redis)
        aggregator = FeedbackAggregator(mock_redis)
        msg_id = "msg_toxic_output"

        # Report serious factual mismatch/bias
        await collector.report_issue(
            user_id="user_x",
            message_id=msg_id,
            issue_type="harmful",
            description="Swarm generated toxic reasoning trace",
        )

        result = await aggregator.aggregate_feedback(msg_id)
        assert result.issues_reported == 1
        # Factual issue drops score precipitously
        assert result.overall_score < 0.2

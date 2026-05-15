"""Tests for GoldenBayesian confidence updater."""
import math


from src.reasoning.math_engine.golden_bayesian import GoldenBayesian

PHI = (1 + math.sqrt(5)) / 2
INV_PHI = 1 / PHI


class TestGoldenBayesianConstants:
    def test_phi_value(self) -> None:
        assert abs(GoldenBayesian.PHI - 1.6180339887) < 1e-8

    def test_inv_phi_value(self) -> None:
        assert abs(GoldenBayesian.INV_PHI - 0.6180339887) < 1e-8

    def test_phi_times_inv_phi_equals_one(self) -> None:
        assert abs(GoldenBayesian.PHI * GoldenBayesian.INV_PHI - 1.0) < 1e-10


class TestUpdateConfidence:
    def test_supporting_evidence_increases_confidence(self) -> None:
        result = GoldenBayesian.update_confidence(0.5, 0.8, is_contradiction=False)
        assert result > 0.5

    def test_contradicting_evidence_decreases_confidence(self) -> None:
        result = GoldenBayesian.update_confidence(0.7, 0.6, is_contradiction=True)
        assert result < 0.7

    def test_result_clamped_above_zero(self) -> None:
        result = GoldenBayesian.update_confidence(0.1, 1.0, is_contradiction=True)
        assert result >= 0.0

    def test_result_clamped_below_one(self) -> None:
        result = GoldenBayesian.update_confidence(0.99, 1.0, is_contradiction=False)
        assert result <= 1.0

    def test_zero_evidence_does_not_explode(self) -> None:
        result = GoldenBayesian.update_confidence(0.5, 0.0, is_contradiction=False)
        assert 0.0 <= result <= 1.0

    def test_contradiction_uses_inv_phi_damping(self) -> None:
        prior = 0.8
        evidence = 0.5
        result = GoldenBayesian.update_confidence(prior, evidence, is_contradiction=True)
        expected = max(0.0, prior - evidence * INV_PHI)
        assert abs(result - expected) < 1e-9

    def test_prior_clamped_to_valid_range(self) -> None:
        # Inputs outside [0,1] should be clamped internally
        result = GoldenBayesian.update_confidence(1.5, 0.5)
        assert 0.0 <= result <= 1.0
        result2 = GoldenBayesian.update_confidence(-0.3, 0.5)
        assert 0.0 <= result2 <= 1.0

    def test_high_evidence_with_low_prior_still_stays_bounded(self) -> None:
        result = GoldenBayesian.update_confidence(0.05, 0.99)
        assert 0.0 <= result <= 1.0

    def test_supporting_evidence_grows_slower_than_full_evidence(self) -> None:
        # Should not jump from 0.5 to 1.0 in a single step
        result = GoldenBayesian.update_confidence(0.5, 1.0)
        assert result < 1.0
        assert result > 0.5


class TestBatchUpdate:
    def test_batch_returns_float(self) -> None:
        result = GoldenBayesian.batch_update(0.5, [0.6, 0.7, 0.8])
        assert isinstance(result, float)

    def test_batch_all_supporting_increases_confidence(self) -> None:
        result = GoldenBayesian.batch_update(0.4, [0.8, 0.8, 0.8])
        assert result > 0.4

    def test_batch_all_contradicting_decreases_confidence(self) -> None:
        result = GoldenBayesian.batch_update(0.8, [0.5, 0.5], [True, True])
        assert result < 0.8

    def test_batch_empty_returns_prior(self) -> None:
        result = GoldenBayesian.batch_update(0.6, [])
        assert result == 0.6

    def test_batch_result_clamped(self) -> None:
        result = GoldenBayesian.batch_update(0.99, [1.0, 1.0, 1.0])
        assert result <= 1.0

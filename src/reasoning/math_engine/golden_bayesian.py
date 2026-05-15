"""Golden Ratio weighted Bayesian confidence updater.

Uses the Golden Ratio (φ ≈ 1.618) as a natural scaling constant for
hypothesis confidence updates during recursive reasoning cycles.

Why φ?
- Supporting evidence pushes confidence toward the golden mean organically,
  avoiding over-confident jumps that linear ±delta methods produce.
- Contradicting evidence decays using 1/φ (≈ 0.618), the complementary
  ratio, so confidence falls faster than it rises — matching the asymmetric
  cost of false confidence in scientific reasoning.
"""
import math


class GoldenBayesian:
    """Golden Ratio weighted Bayesian inference for hypothesis confidence."""

    PHI: float = (1 + math.sqrt(5)) / 2   # 1.6180339887...
    INV_PHI: float = 1 / PHI               # 0.6180339887...  (= PHI - 1)

    @classmethod
    def update_confidence(
        cls,
        prior: float,
        evidence_strength: float,
        is_contradiction: bool = False,
    ) -> float:
        """Return an updated confidence in [0.0, 1.0].

        Args:
            prior: Current hypothesis confidence (0–1).
            evidence_strength: Quality signal from this iteration (0–1).
                               Typically the ReflectionEngine quality_score.
            is_contradiction: True when this evidence opposes the hypothesis
                               (e.g. quality decreased vs previous iteration).

        Returns:
            Updated confidence clamped to [0.0, 1.0].
        """
        prior = max(0.0, min(1.0, prior))
        evidence_strength = max(0.0, min(1.0, evidence_strength))

        if is_contradiction:
            # Graceful damping: shrink by INV_PHI-scaled evidence
            adjustment = evidence_strength * cls.INV_PHI
            return max(0.0, prior - adjustment)

        # Supporting evidence: Bayesian update scaled by INV_PHI to
        # prevent overconfidence and preserve the golden mean property.
        likelihood = evidence_strength * (cls.PHI - 1)  # = evidence * INV_PHI
        denominator = (
            prior * likelihood
            + (1 - prior) * (1 - likelihood)
            + 1e-9  # numerical stability
        )
        posterior = (prior * likelihood) / denominator
        return min(1.0, prior + posterior * cls.INV_PHI)

    @classmethod
    def batch_update(
        cls,
        prior: float,
        evidence_scores: list[float],
        contradiction_flags: list[bool] | None = None,
    ) -> float:
        """Sequential updates over multiple evidence signals.

        Args:
            prior: Starting confidence.
            evidence_scores: Ordered list of quality signals.
            contradiction_flags: Parallel list of contradiction booleans.
                                  Defaults to all False if omitted.

        Returns:
            Final confidence after all updates.
        """
        flags = contradiction_flags or [False] * len(evidence_scores)
        confidence = prior
        for score, is_contra in zip(evidence_scores, flags):
            confidence = cls.update_confidence(confidence, score, is_contra)
        return round(confidence, 6)

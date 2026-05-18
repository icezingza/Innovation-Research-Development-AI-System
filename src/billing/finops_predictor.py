"""FinOps Predictor — linear regression forecasting for token/compute usage.

Predicts future token usage based on historical data using simple linear regression,
then calculates estimated costs for the next billing period.
"""

from pydantic import BaseModel


class ForecastResult(BaseModel):
    """Result of a usage forecast."""

    predicted_usage: int
    predicted_cost_usd: float
    periods_ahead: int
    method: str


class FinOpsPredictor:
    """Linear regression predictor for tenant token/compute usage."""

    def __init__(self, cost_per_1k_tokens: float = 0.002) -> None:
        """Initialize predictor with cost per 1k tokens.

        Args:
            cost_per_1k_tokens: Cost in USD per 1000 tokens (default 0.002 = $0.002/1k tokens)
        """
        self._cost_per_1k = cost_per_1k_tokens

    def forecast(
        self, history: list[int], periods_ahead: int = 1
    ) -> ForecastResult:
        """Forecast future usage based on historical data.

        Args:
            history: List of past usage values (must have at least 1 point)
            periods_ahead: Number of periods to forecast ahead (default 1)

        Returns:
            ForecastResult containing predicted usage and cost

        Raises:
            ValueError: If history is empty
        """
        if not history:
            raise ValueError("history must contain at least one data point")

        # Single point: repeat it; multiple points: linear extrapolation
        if len(history) == 1:
            predicted = history[0]
            method = "repeat"
        else:
            predicted = self._linear_extrapolate(history, periods_ahead)
            method = "linear_regression"

        # Ensure non-negative prediction
        predicted = max(0, predicted)

        # Calculate cost: usage * (cost_per_1k / 1000)
        cost = predicted * self._cost_per_1k / 1000

        return ForecastResult(
            predicted_usage=predicted,
            predicted_cost_usd=round(cost, 6),
            periods_ahead=periods_ahead,
            method=method,
        )

    def _linear_extrapolate(self, history: list[int], periods_ahead: int) -> int:
        """Fit a line to history data and extrapolate forward.

        Uses least-squares linear regression: y = mx + b
        where x is the period index (0, 1, 2, ..., n-1) and y is the usage.

        Args:
            history: List of at least 2 usage values
            periods_ahead: Number of periods to extrapolate

        Returns:
            Predicted usage value as integer
        """
        n = len(history)
        x_mean = (n - 1) / 2
        y_mean = sum(history) / n

        # Calculate slope: Σ((x - x_mean) * (y - y_mean)) / Σ((x - x_mean)²)
        numerator = sum((i - x_mean) * (history[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean

        # Predict at x = n - 1 + periods_ahead (next period)
        x_predict = n - 1 + periods_ahead
        predicted_value = intercept + slope * x_predict

        return int(predicted_value)

"""Tests for FinOps Predictor — linear regression token/cost forecasting."""

import pytest

from src.billing.finops_predictor import FinOpsPredictor, ForecastResult


def test_forecast_linear_trend():
    """Linear increasing usage should forecast next value correctly."""
    predictor = FinOpsPredictor()
    # Linearly increasing usage: 100, 200, 300, 400, 500
    history = [100, 200, 300, 400, 500]
    result = predictor.forecast(history, periods_ahead=1)
    assert isinstance(result, ForecastResult)
    # Next value should be ~600 (linear trend)
    assert 550 <= result.predicted_usage <= 650


def test_forecast_flat_trend():
    """Flat usage should forecast near same value."""
    predictor = FinOpsPredictor()
    history = [1000, 1000, 1000, 1000]
    result = predictor.forecast(history, periods_ahead=1)
    assert 950 <= result.predicted_usage <= 1050


def test_forecast_cost_calculation():
    """Cost calculation should use cost_per_1k_tokens."""
    predictor = FinOpsPredictor(cost_per_1k_tokens=0.002)
    history = [500_000]
    result = predictor.forecast(history, periods_ahead=1)
    # 500_000 tokens * (0.002 / 1000) = $1.00
    assert result.predicted_cost_usd > 0


def test_forecast_minimum_history():
    """Single data point should repeat value."""
    predictor = FinOpsPredictor()
    result = predictor.forecast([100], periods_ahead=1)
    assert result.predicted_usage == 100  # single point → repeat


def test_forecast_empty_history_raises():
    """Empty history should raise ValueError."""
    predictor = FinOpsPredictor()
    with pytest.raises(ValueError, match="history"):
        predictor.forecast([], periods_ahead=1)

from datetime import date, timedelta

from cropnova.market.mandi_forecast import assess_forecast
from cropnova.market.mandi_page import market_guidance


def weekly_series(prices):
    start = date(2024, 1, 1)
    return [
        (start + timedelta(weeks=week, days=day), price)
        for week, price in enumerate(prices)
        for day in range(3, 6)
    ]


def test_regression_beats_persistence_and_stale_series_stops_current_forecast():
    observations = weekly_series([2300, 2500] * 36)
    current = observations[-1][0] + timedelta(days=2)
    forecast = assess_forecast(observations, current)
    assert forecast["state"] == "current"
    assert forecast["error"] < forecast["baseline_error"]
    assert forecast["price"] < forecast["previous"]
    assert "recorded field mismatch" in market_guidance({"status": "rejected"}, forecast)
    assert "open field checks" in market_guidance({"status": "unknown"}, forecast)
    assert "lower" in market_guidance({"status": "feasible"}, forecast)
    assert assess_forecast(observations, current + timedelta(weeks=3))["state"] == "historical"


def test_forecast_gates_sparse_and_constant_series():
    observations = weekly_series([2300] * 72)
    current = observations[-1][0] + timedelta(days=2)
    assert assess_forecast(observations[:30], current)["state"] == "sparse"
    assert assess_forecast(observations, current)["state"] == "baseline_better"


def test_incomplete_week_does_not_leak_into_the_forecast_or_backtest():
    observations = weekly_series([2300, 2500] * 36)
    current = observations[-1][0] + timedelta(days=2)
    expected = assess_forecast(observations, current)
    with_current_week = observations + [(current, 9999)]
    assert assess_forecast(with_current_week, current) == expected

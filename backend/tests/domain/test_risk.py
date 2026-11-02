"""Risk buffers and the explicit two-day outcome lag in the walk-forward back-test."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.domain.risk import (
    buffer_by_hour,
    buffer_overall,
    risk_adjusted,
    walk_forward_backtest,
)
from tests.helpers import joined_errors


def test_buffer_overall_matches_linear_quantiles() -> None:
    frame = pd.DataFrame({"error_mw": [-10.0, 0.0, 10.0, 20.0]})
    points = buffer_overall(frame, (0.5, 0.9, 0.95))
    assert [point.level for point in points] == [0.5, 0.9, 0.95]
    assert [point.buffer_mw for point in points] == pytest.approx([5.0, 17.0, 18.5])


def test_buffer_overall_drops_missing_errors_and_handles_empty_input() -> None:
    frame = pd.DataFrame({"error_mw": [float("nan"), 10.0, 20.0]})
    points = buffer_overall(frame, (0.5,))
    assert len(points) == 1
    assert points[0].buffer_mw == pytest.approx(15.0)
    assert buffer_overall(pd.DataFrame({"error_mw": []}), (0.5,)) == []


def test_buffer_by_hour_returns_twenty_four_buckets() -> None:
    frame = pd.DataFrame(
        {
            "start_time": pd.to_datetime(
                ["2026-01-15T00:00:00Z", "2026-01-15T01:00:00Z", "2026-01-15T01:30:00Z"],
                utc=True,
            ),
            "error_mw": [10.0, 20.0, 30.0],
        }
    )
    rows = buffer_by_hour(frame, (0.5,))
    assert len(rows) == 24
    assert rows[0]["hour"] == 0
    assert [point.buffer_mw for point in rows[0]["buffers"]] == pytest.approx([10.0])
    assert [point.buffer_mw for point in rows[1]["buffers"]] == pytest.approx([25.0])
    assert rows[2]["buffers"] == []


def test_risk_adjusted_forecast_is_clipped_at_zero() -> None:
    forecast = pd.Series([100.0, 500.0, 1000.0])
    adjusted = risk_adjusted(forecast, 300.0)
    assert adjusted.tolist() == pytest.approx([0.0, 200.0, 700.0])


def _walk_forward_frame() -> pd.DataFrame:
    # One period per day keeps the quantile arithmetic unambiguous.
    days = [date(2026, 1, day) for day in range(1, 7)]
    errors = [100.0, 200.0, 300.0, 400.0, 0.0, 0.0]
    return joined_errors([(day, 1000.0, error) for day, error in zip(days, errors, strict=True)])


def test_walk_forward_excludes_the_two_most_recent_delivery_days() -> None:
    result = walk_forward_backtest(
        _walk_forward_frame(), level=0.5, min_history_days=2, outcome_lag_days=2
    )

    # Days 1-3 have insufficient history; day 4 sees only days 1-2.
    assert result.evaluated_days == 3
    assert result.skipped_days == (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3))
    assert [day.delivery_date for day in result.daily] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    # Median of [100, 200] is 150. If day 3 leaked in, it would be 200.
    assert result.daily[0].buffer_mw == pytest.approx(150.0)
    assert result.daily[1].buffer_mw == pytest.approx(200.0)
    assert result.daily[2].buffer_mw == pytest.approx(250.0)
    assert result.mean_buffer_mw == pytest.approx(200.0)
    assert result.coverage == pytest.approx(2.0 / 3.0)
    assert result.days_with_breach_share == pytest.approx(1.0 / 3.0)
    assert result.target == 0.5
    assert result.outcome_lag_days == 2


def test_walk_forward_without_enough_history_returns_undefined_coverage() -> None:
    result = walk_forward_backtest(
        _walk_forward_frame(), level=0.9, min_history_days=31, outcome_lag_days=2
    )
    assert result.evaluated_days == 0
    assert result.daily == ()
    assert result.coverage is None
    assert result.mean_buffer_mw is None
    assert result.days_with_breach_share is None
    assert len(result.skipped_days) == 6


def test_walk_forward_ignores_rows_without_an_actual() -> None:
    frame = _walk_forward_frame()
    frame.loc[frame["delivery_date"] == date(2026, 1, 6), "actual_mw"] = float("nan")
    result = walk_forward_backtest(frame, level=0.5, min_history_days=2, outcome_lag_days=2)
    assert [day.delivery_date for day in result.daily] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]

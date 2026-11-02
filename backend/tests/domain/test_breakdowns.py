"""Breakdowns: London hours, equal-count wind bins, daily and worst rankings."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.domain.breakdowns import by_day, by_hour, by_level, worst_days, worst_periods


def _frame() -> pd.DataFrame:
    rows = [
        ("2026-01-15T00:00:00Z", date(2026, 1, 15), 1000.0, 100.0),
        ("2026-01-15T01:00:00Z", date(2026, 1, 15), 1100.0, -100.0),
        ("2026-01-16T00:00:00Z", date(2026, 1, 16), 1200.0, 300.0),
        ("2026-01-16T01:00:00Z", date(2026, 1, 16), 1300.0, -50.0),
    ]
    frame = pd.DataFrame(rows, columns=["start_time", "delivery_date", "forecast_mw", "error_mw"])
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["actual_mw"] = frame["forecast_mw"] - frame["error_mw"]
    frame["abs_error_mw"] = frame["error_mw"].abs()
    frame["shortfall_mw"] = frame["error_mw"].clip(lower=0.0)
    return frame


def test_by_hour_returns_all_24_london_hours_in_order() -> None:
    buckets = by_hour(_frame())
    assert len(buckets) == 24
    assert [bucket.label for bucket in buckets[:3]] == ["00:00", "01:00", "02:00"]
    assert buckets[0].metrics.n == 2
    assert buckets[1].metrics.n == 2
    assert buckets[2].metrics.n == 0


def test_by_hour_handles_an_empty_frame() -> None:
    empty = pd.DataFrame(
        {
            "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
            "forecast_mw": pd.Series(dtype=float),
            "actual_mw": pd.Series(dtype=float),
        }
    )
    buckets = by_hour(empty)
    assert len(buckets) == 24
    assert all(bucket.metrics.n == 0 for bucket in buckets)


def test_by_level_uses_equal_count_quantile_bins() -> None:
    buckets = by_level(_frame(), basis="actual", bins=2)
    assert [bucket.label for bucket in buckets] == ["Q1 (lowest)", "Q2"]
    assert [bucket.metrics.n for bucket in buckets] == [2, 2]
    # Actuals are [900, 1200, 900, 1350].
    assert buckets[0].from_value == pytest.approx(900.0)
    assert buckets[0].to_value == pytest.approx(900.0)
    assert buckets[1].from_value == pytest.approx(1200.0)
    assert buckets[1].to_value == pytest.approx(1350.0)


def test_by_level_supports_forecast_basis_and_clamps_bin_count_to_rows() -> None:
    buckets = by_level(_frame(), basis="forecast", bins=10)
    assert len(buckets) == 4
    assert [bucket.metrics.n for bucket in buckets] == [1, 1, 1, 1]
    assert buckets[-1].to_value == pytest.approx(1300.0)


def test_by_level_rejects_an_unknown_basis() -> None:
    with pytest.raises(ValueError, match="basis"):
        by_level(_frame(), basis="wind-speed")


def test_by_level_returns_empty_for_no_valid_rows() -> None:
    frame = _frame()
    assert by_level(frame.loc[frame["forecast_mw"].isna()], basis="forecast") == []


def test_by_day_computes_metrics_and_the_largest_miss() -> None:
    days = by_day(_frame())
    assert [row["delivery_date"] for row in days] == [date(2026, 1, 15), date(2026, 1, 16)]
    first = days[0]
    assert first["max_abs_mw"] == pytest.approx(100.0)
    assert first["mean_actual_mw"] == pytest.approx(1050.0)
    second = days[1]
    assert second["max_abs_mw"] == pytest.approx(300.0)
    assert second["max_abs_time"] == pd.Timestamp("2026-01-16T00:00:00Z")


def test_by_day_handles_rows_without_actuals() -> None:
    frame = _frame()
    frame["actual_mw"] = float("nan")
    frame["error_mw"] = float("nan")
    frame["abs_error_mw"] = float("nan")
    days = by_day(frame)
    assert len(days) == 2
    assert days[0]["max_abs_mw"] is None
    assert days[0]["mean_actual_mw"] is None


def test_worst_days_ranks_by_daily_mae() -> None:
    ranked = worst_days(_frame(), n=1)
    assert len(ranked) == 1
    assert ranked[0]["delivery_date"] == date(2026, 1, 16)


def test_worst_periods_ranks_individual_errors() -> None:
    ranked = worst_periods(_frame(), n=2)
    assert [row["error_mw"] for row in ranked] == pytest.approx([300.0, 100.0])
    assert ranked[0]["start_time"] == pd.Timestamp("2026-01-16T00:00:00Z")
    assert ranked[0]["abs_error_mw"] == pytest.approx(300.0)

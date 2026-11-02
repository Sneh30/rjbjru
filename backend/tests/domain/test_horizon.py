"""Horizon bucket boundaries and the open-ended final bucket."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.domain.horizon import decision_band_h, horizon_buckets


def _frame() -> pd.DataFrame:
    # Every row has a known actual, so each bucket's n is predictable.
    return pd.DataFrame(
        {
            "horizon_h": [-1.0, 0.0, 5.99, 6.0, 11.99, 12.0, 71.99, 72.0, 100.0],
            "forecast_mw": [100.0] * 9,
            "actual_mw": [90.0] * 9,
        }
    )


def test_buckets_are_left_inclusive_and_right_exclusive() -> None:
    buckets, negative = horizon_buckets(_frame(), (0.0, 6.0, 12.0, 72.0))
    assert negative == 1
    assert [bucket.label for bucket in buckets] == ["0-6 h", "6-12 h", "12-72 h", "72+ h"]
    assert [bucket.metrics.n for bucket in buckets] == [2, 2, 2, 2]
    assert [bucket.from_value for bucket in buckets] == [0.0, 6.0, 12.0, 72.0]
    assert np.isinf(buckets[-1].to_value)
    assert buckets[0].metrics.mae_mw == pytest.approx(10.0)


def test_empty_buckets_are_returned_for_a_stable_axis() -> None:
    frame = pd.DataFrame(
        {
            "horizon_h": [2.0],
            "forecast_mw": [100.0],
            "actual_mw": [90.0],
        }
    )
    buckets, negative = horizon_buckets(frame, (0.0, 6.0, 12.0))
    assert negative == 0
    assert [bucket.metrics.n for bucket in buckets] == [1, 0, 0]
    assert buckets[1].metrics.mae_mw is None


def test_negative_horizons_are_dropped_and_counted() -> None:
    frame = pd.DataFrame(
        {
            "horizon_h": [-0.01, -10.0, 1.0],
            "forecast_mw": [1.0, 2.0, 3.0],
            "actual_mw": [1.0, 2.0, 3.0],
        }
    )
    buckets, negative = horizon_buckets(frame, (0.0, 6.0))
    assert negative == 2
    assert buckets[0].metrics.n == 1


def test_decision_band_reports_selected_horizon_extent() -> None:
    selected = pd.DataFrame({"horizon_h": [16.5, 28.0, 39.5]})
    assert decision_band_h(selected) == (16.5, 39.5)


def test_decision_band_is_none_for_an_empty_selection() -> None:
    assert decision_band_h(pd.DataFrame({"horizon_h": []})) is None

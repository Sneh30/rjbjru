"""Hand-computed metric tests.

The reference vector is the one documented in ``docs/IMPLEMENTATION.md``:
errors ``[-10, 10, -30, 20]``. Every expected value here is derived by hand or from
the definition, not by calling the implementation.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.domain.metrics import compute_metrics, energy_mwh, max_ramp_mw, skill_score


def _reference_frame() -> pd.DataFrame:
    # actual = 2000 MW everywhere => errors are exactly the documented vector.
    errors = [-10.0, 10.0, -30.0, 20.0]
    return pd.DataFrame(
        {
            "forecast_mw": [2000.0 + error for error in errors],
            "actual_mw": [2000.0] * 4,
        }
    )


def test_metrics_match_hand_computed_reference_vector() -> None:
    metrics = compute_metrics(_reference_frame())

    assert metrics.n == 4
    assert metrics.n_missing_actual == 0
    assert metrics.mean_actual_mw == pytest.approx(2000.0)
    assert metrics.mae_mw == pytest.approx(17.5)
    assert metrics.rmse_mw == pytest.approx(math.sqrt(375.0))
    assert metrics.bias_mw == pytest.approx(-2.5)
    assert metrics.nmae_pct == pytest.approx(0.875)
    assert metrics.wape_pct == pytest.approx(0.875)
    # MAPE is guarded and all four actuals exceed the 500 MW floor.
    assert metrics.mape_n == 4
    assert metrics.mape_pct == pytest.approx(0.875)
    assert metrics.p50_abs_mw == pytest.approx(15.0)
    assert metrics.p90_abs_mw == pytest.approx(27.0)
    assert metrics.p95_abs_mw == pytest.approx(28.5)
    assert metrics.p5_err_mw == pytest.approx(-27.0)
    assert metrics.p50_err_mw == pytest.approx(0.0)
    assert metrics.p95_err_mw == pytest.approx(18.5)
    assert metrics.over_forecast_share == pytest.approx(0.5)
    assert metrics.shortfall_mean_mw == pytest.approx(7.5)
    assert metrics.shortfall_p90_mw == pytest.approx(17.0)
    assert metrics.shortfall_p95_mw == pytest.approx(18.5)
    assert metrics.shortfall_max_mw == pytest.approx(20.0)
    # A constant actual has zero variance, so correlation is undefined rather than 1.
    assert metrics.correlation is None


def test_error_sign_is_forecast_minus_actual_even_if_input_column_disagrees() -> None:
    frame = pd.DataFrame(
        {
            "forecast_mw": [110.0, 90.0],
            "actual_mw": [100.0, 100.0],
            "error_mw": [-999.0, -999.0],
        }
    )
    metrics = compute_metrics(frame)
    assert metrics.bias_mw == pytest.approx(0.0)
    assert metrics.mae_mw == pytest.approx(10.0)
    assert metrics.over_forecast_share == pytest.approx(0.5)


def test_missing_actual_is_counted_but_excluded_from_metrics() -> None:
    frame = _reference_frame()
    frame.loc[len(frame)] = {"forecast_mw": 1234.0, "actual_mw": float("nan")}
    metrics = compute_metrics(frame)
    assert metrics.n == 4
    assert metrics.n_missing_actual == 1
    assert metrics.mae_mw == pytest.approx(17.5)


def test_missing_forecast_is_excluded_even_without_a_missing_actual() -> None:
    frame = _reference_frame()
    frame.loc[len(frame)] = {"forecast_mw": float("nan"), "actual_mw": 2000.0}
    metrics = compute_metrics(frame)
    assert metrics.n == 4
    assert metrics.n_missing_actual == 0
    assert metrics.mae_mw == pytest.approx(17.5)


def test_empty_and_all_missing_frames_return_none_not_nan() -> None:
    empty = pd.DataFrame(
        {
            "forecast_mw": pd.Series(dtype=float),
            "actual_mw": pd.Series(dtype=float),
        }
    )
    metrics = compute_metrics(empty)
    assert metrics.n == 0
    assert metrics.mae_mw is None
    assert metrics.correlation is None
    assert metrics.over_forecast_share is None

    all_missing = pd.DataFrame(
        {"forecast_mw": [1.0, 2.0], "actual_mw": [float("nan"), float("nan")]}
    )
    metrics = compute_metrics(all_missing)
    assert metrics.n == 0
    assert metrics.n_missing_actual == 2
    assert metrics.mae_mw is None


def test_missing_required_columns_raises_value_error() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        compute_metrics(pd.DataFrame({"actual_mw": [1.0]}))


def test_guarded_mape_skips_low_and_non_positive_actuals() -> None:
    frame = pd.DataFrame(
        {
            "forecast_mw": [510.0, 1010.0, 1010.0],
            "actual_mw": [500.0, 1000.0, 0.0],
        }
    )
    metrics = compute_metrics(frame, mape_min_actual_mw=500.0)
    # Exactly 500 MW passes the guard; the zero actual cannot contribute.
    assert metrics.mape_n == 2
    assert metrics.mape_pct == pytest.approx(1.5)

    below = pd.DataFrame({"forecast_mw": [100.0], "actual_mw": [100.0]})
    metrics = compute_metrics(below, mape_min_actual_mw=500.0)
    assert metrics.mape_n == 0
    assert metrics.mape_pct is None


def test_ratio_metrics_are_undefined_when_aggregate_actual_is_not_positive() -> None:
    frame = pd.DataFrame(
        {
            "forecast_mw": [10.0, -10.0],
            "actual_mw": [-20.0, 20.0],
        }
    )
    metrics = compute_metrics(frame)
    assert metrics.mean_actual_mw == pytest.approx(0.0)
    assert metrics.nmae_pct is None
    assert metrics.wape_pct is None


def test_correlation_is_computed_when_both_series_vary() -> None:
    frame = pd.DataFrame(
        {
            "forecast_mw": [10.0, 20.0, 30.0],
            "actual_mw": [12.0, 18.0, 33.0],
        }
    )
    metrics = compute_metrics(frame)
    expected = float(np.corrcoef([10.0, 20.0, 30.0], [12.0, 18.0, 33.0])[0, 1])
    assert metrics.correlation == pytest.approx(expected)


def test_correlation_is_none_for_a_single_row() -> None:
    metrics = compute_metrics(pd.DataFrame({"forecast_mw": [1.0], "actual_mw": [1.0]}))
    assert metrics.correlation is None


@pytest.mark.parametrize(
    ("forecast_mae", "baseline_mae", "expected"),
    [
        (100.0, 200.0, 0.5),
        (200.0, 200.0, 0.0),
        (300.0, 200.0, -0.5),
        (None, 200.0, None),
        (100.0, None, None),
        (100.0, 0.0, None),
    ],
)
def test_skill_score(
    forecast_mae: float | None,
    baseline_mae: float | None,
    expected: float | None,
) -> None:
    assert skill_score(forecast_mae, baseline_mae) == expected


def test_energy_uses_one_hour_per_hourly_average() -> None:
    series = pd.Series([1000.0, 2000.0, 3000.0])
    assert energy_mwh(series) == pytest.approx(6000.0)


def test_max_ramp_uses_absolute_change_over_the_requested_lag() -> None:
    series = pd.Series([1000.0, 1300.0, 1200.0, 1800.0])
    assert max_ramp_mw(series, 1) == pytest.approx(600.0)
    assert max_ramp_mw(series, 2) == pytest.approx(500.0)
    assert max_ramp_mw(series, 3) == pytest.approx(800.0)
    assert max_ramp_mw(pd.Series([1000.0, 1200.0]), 2) is None

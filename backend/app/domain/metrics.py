"""Forecast-error metrics.

Definitions follow ``docs/METHODOLOGY.md`` and ``ENGINEERING_REFERENCE.md`` section 8.
Every function is pure and returns ``None`` rather than NaN for undefined values.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import DEFAULT_MAPE_MIN_ACTUAL_MW, MWH_PER_FORECAST_PERIOD
from .models import Metrics


def _valid_error_frame(joined: pd.DataFrame) -> pd.DataFrame:
    """Return rows with both a forecast and an actual, plus a clean error column."""
    required = {"forecast_mw", "actual_mw"}
    missing = required.difference(joined.columns)
    if missing:
        raise ValueError(f"joined frame is missing columns: {sorted(missing)}")
    valid = joined.loc[joined["forecast_mw"].notna() & joined["actual_mw"].notna()].copy()
    valid["error_mw"] = valid["forecast_mw"] - valid["actual_mw"]
    return valid


def compute_metrics(
    joined: pd.DataFrame,
    *,
    mape_min_actual_mw: float = DEFAULT_MAPE_MIN_ACTUAL_MW,
) -> Metrics:
    """Compute the buyer-relevant metric suite.

    Args:
        joined: Frame with ``forecast_mw`` and ``actual_mw`` (MW). ``error_mw`` is
            recomputed as ``forecast - actual`` to enforce the sign convention.
        mape_min_actual_mw: Minimum actual output for guarded MAPE (MW).

    Returns:
        A frozen :class:`Metrics` object. Undefined values are ``None``.

    Notes:
        Percentiles use NumPy's linear interpolation. Percent metrics are in
        percentage points (0-100), while ``over_forecast_share`` is a fraction.
    """
    n_missing_actual = int(joined["actual_mw"].isna().sum()) if "actual_mw" in joined else 0
    valid = _valid_error_frame(joined)
    n = int(len(valid))
    if n == 0:
        return Metrics(
            n=0,
            n_missing_actual=n_missing_actual,
            mean_actual_mw=None,
            mae_mw=None,
            rmse_mw=None,
            bias_mw=None,
            nmae_pct=None,
            wape_pct=None,
            mape_pct=None,
            mape_n=0,
            p50_abs_mw=None,
            p90_abs_mw=None,
            p95_abs_mw=None,
            p5_err_mw=None,
            p50_err_mw=None,
            p95_err_mw=None,
            over_forecast_share=None,
            shortfall_mean_mw=None,
            shortfall_p90_mw=None,
            shortfall_p95_mw=None,
            shortfall_max_mw=None,
            correlation=None,
        )

    error = valid["error_mw"].to_numpy(dtype=float)
    actual = valid["actual_mw"].to_numpy(dtype=float)
    forecast = valid["forecast_mw"].to_numpy(dtype=float)
    absolute = np.abs(error)
    shortfall = np.clip(error, 0.0, None)

    mean_actual = float(np.mean(actual))
    mae = float(np.mean(absolute))
    rmse = float(np.sqrt(np.mean(np.square(error))))
    bias = float(np.mean(error))

    nmae = mae / mean_actual * 100.0 if mean_actual > 0 else None
    actual_sum = float(np.sum(actual))
    wape = float(np.sum(absolute)) / actual_sum * 100.0 if actual_sum > 0 else None

    guarded = (actual >= mape_min_actual_mw) & (actual > 0)
    mape_n = int(np.count_nonzero(guarded))
    mape = float(np.mean(absolute[guarded] / actual[guarded]) * 100.0) if mape_n > 0 else None

    correlation: float | None
    if n >= 2 and float(np.std(forecast)) > 0 and float(np.std(actual)) > 0:
        correlation = float(np.corrcoef(forecast, actual)[0, 1])
    else:
        correlation = None

    return Metrics(
        n=n,
        n_missing_actual=n_missing_actual,
        mean_actual_mw=mean_actual,
        mae_mw=mae,
        rmse_mw=rmse,
        bias_mw=bias,
        nmae_pct=nmae,
        wape_pct=wape,
        mape_pct=mape,
        mape_n=mape_n,
        p50_abs_mw=float(np.percentile(absolute, 50, method="linear")),
        p90_abs_mw=float(np.percentile(absolute, 90, method="linear")),
        p95_abs_mw=float(np.percentile(absolute, 95, method="linear")),
        p5_err_mw=float(np.percentile(error, 5, method="linear")),
        p50_err_mw=float(np.percentile(error, 50, method="linear")),
        p95_err_mw=float(np.percentile(error, 95, method="linear")),
        over_forecast_share=float(np.mean(error > 0)),
        shortfall_mean_mw=float(np.mean(shortfall)),
        shortfall_p90_mw=float(np.percentile(shortfall, 90, method="linear")),
        shortfall_p95_mw=float(np.percentile(shortfall, 95, method="linear")),
        shortfall_max_mw=float(np.max(shortfall)),
        correlation=correlation,
    )


def skill_score(forecast_mae: float | None, baseline_mae: float | None) -> float | None:
    """Return ``1 - MAE_forecast / MAE_baseline`` or ``None`` when undefined."""
    if forecast_mae is None or baseline_mae is None or baseline_mae == 0:
        return None
    return 1.0 - forecast_mae / baseline_mae


def energy_mwh(forecast_mw: pd.Series[Any]) -> float:
    """Return energy in MWh from hourly average MW values."""
    return float(forecast_mw.sum() * MWH_PER_FORECAST_PERIOD)


def max_ramp_mw(values: pd.Series[Any], lag: int) -> float | None:
    """Return the largest absolute change over ``lag`` steps, in MW."""
    if len(values) <= lag:
        return None
    numeric = values.astype(float)
    return float(numeric.diff(periods=lag).abs().max(skipna=True))

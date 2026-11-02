"""Persistence baseline available at the decision cutoff.

The baseline is the latest complete hourly actual ending at or before the cutoff,
held flat across the delivery day. It uses only information a trader had at the
cutoff and only the two permitted Elexon datasets.
"""

from __future__ import annotations

from datetime import time

import pandas as pd

from .constants import FORECAST_PERIOD_HOURS
from .metrics import compute_metrics, skill_score
from .models import BaselineSummary
from .timeutils import cutoff_for_delivery_date

BASELINE_NAME = "persistence_last_actual_at_cutoff"


def _last_actual_before_cutoff(hourly_actuals: pd.DataFrame, cutoff: pd.Timestamp) -> float | None:
    """Return the latest complete hourly actual ending at or before ``cutoff``."""
    ends = hourly_actuals["start_time"] + pd.Timedelta(hours=FORECAST_PERIOD_HOURS)
    eligible = hourly_actuals.loc[(ends <= cutoff) & hourly_actuals["actual_mw"].notna()]
    if eligible.empty:
        return None
    row = eligible.loc[eligible["start_time"].idxmax()]
    return float(row["actual_mw"])


def persistence_for_selected(
    selected: pd.DataFrame,
    hourly_actuals: pd.DataFrame,
    cutoff_local: time,
) -> pd.DataFrame:
    """Attach a persistence baseline in MW to every selected forecast row.

    Args:
        selected: Decision-time selected rows with ``delivery_date``.
        hourly_actuals: Hourly actuals ``start_time``, ``actual_mw``.
        cutoff_local: Wall-clock cutoff on the previous London day.

    Returns:
        A copy of ``selected`` with ``baseline_mw`` (MW). Days without a complete
        prior hourly actual get ``NaN`` and are excluded from the baseline comparison.
    """
    frame = selected.copy()
    values: dict[object, float | None] = {}
    for delivery_date in sorted(frame["delivery_date"].unique()):
        cutoff = pd.Timestamp(cutoff_for_delivery_date(delivery_date, cutoff_local))
        values[delivery_date] = _last_actual_before_cutoff(hourly_actuals, cutoff)
    frame["baseline_mw"] = pd.Series(
        [values.get(day) for day in frame["delivery_date"]],
        index=frame.index,
        dtype="float64",
    )
    return frame


def baseline_summary(joined_with_baseline: pd.DataFrame) -> BaselineSummary:
    """Compute persistence MAE and forecast skill on the common row set."""
    common = joined_with_baseline.loc[
        joined_with_baseline["baseline_mw"].notna()
        & joined_with_baseline["actual_mw"].notna()
        & joined_with_baseline["forecast_mw"].notna()
    ].copy()
    if common.empty:
        return BaselineSummary(
            name=BASELINE_NAME,
            mae_mw=None,
            forecast_mae_mw=None,
            skill=None,
            n=0,
        )
    baseline_metrics = compute_metrics(
        pd.DataFrame(
            {
                "forecast_mw": common["baseline_mw"].astype(float),
                "actual_mw": common["actual_mw"].astype(float),
            }
        )
    )
    forecast_metrics = compute_metrics(common)
    return BaselineSummary(
        name=BASELINE_NAME,
        mae_mw=baseline_metrics.mae_mw,
        forecast_mae_mw=forecast_metrics.mae_mw,
        skill=skill_score(forecast_metrics.mae_mw, baseline_metrics.mae_mw),
        n=len(common),
    )

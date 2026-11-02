"""Breakdowns by London hour, wind level, delivery day, and worst periods."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

from .metrics import compute_metrics
from .models import BucketMetrics, Metrics
from .timeutils import london_hour


def by_hour(joined: pd.DataFrame, *, mape_min_actual_mw: float = 500.0) -> list[BucketMetrics]:
    """Compute metrics for each London-local hour (0-23).

    Args:
        joined: Decision-time rows with ``start_time``, ``forecast_mw`` and ``actual_mw``.
        mape_min_actual_mw: Guard threshold for MAPE.

    Returns:
        Twenty-four buckets in hour order, including empty hours with ``n=0``.
    """
    hours = london_hour(joined["start_time"])
    result: list[BucketMetrics] = []
    for hour in range(24):
        subset = joined.loc[hours == hour]
        result.append(
            BucketMetrics(
                label=f"{hour:02d}:00",
                from_value=float(hour),
                to_value=float(hour + 1),
                metrics=compute_metrics(subset, mape_min_actual_mw=mape_min_actual_mw),
            )
        )
    return result


def by_level(
    joined: pd.DataFrame,
    *,
    basis: str = "actual",
    bins: int = 5,
    mape_min_actual_mw: float = 500.0,
) -> list[BucketMetrics]:
    """Compute metrics for equal-count wind-output quantile bins.

    Ranks, rather than raw quantile edges, are used so duplicate values cannot create
    empty or overlapping bins. The reported ``from_value``/``to_value`` are the actual
    minimum and maximum of each bin in MW.

    Args:
        joined: Decision-time rows with ``forecast_mw`` and ``actual_mw``.
        basis: ``actual`` or ``forecast``.
        bins: Number of bins (3-10 enforced at the API boundary).
        mape_min_actual_mw: Guard threshold for MAPE.

    Returns:
        Non-empty bins in ascending output order, labelled Q1 (lowest) upward.
    """
    if basis not in {"actual", "forecast"}:
        raise ValueError("basis must be 'actual' or 'forecast'")
    column = "actual_mw" if basis == "actual" else "forecast_mw"
    valid = joined.loc[joined[column].notna()].sort_values(column, kind="mergesort").copy()
    n = len(valid)
    if n == 0:
        return []
    bin_count = max(1, min(bins, n))
    ranks = np.arange(n)
    valid["_bin"] = np.minimum((ranks * bin_count) // n, bin_count - 1)
    result: list[BucketMetrics] = []
    for index in range(bin_count):
        subset = valid.loc[valid["_bin"] == index]
        if subset.empty:
            continue
        low = float(subset[column].min())
        high = float(subset[column].max())
        result.append(
            BucketMetrics(
                label=f"Q{index + 1}" + (" (lowest)" if index == 0 else ""),
                from_value=low,
                to_value=high,
                metrics=compute_metrics(subset, mape_min_actual_mw=mape_min_actual_mw),
            )
        )
    return result


def by_day(joined: pd.DataFrame, *, mape_min_actual_mw: float = 500.0) -> list[dict[str, object]]:
    """Compute daily metrics and the single largest absolute miss of each day.

    Args:
        joined: Decision-time rows with ``delivery_date``, ``start_time`` and errors.
        mape_min_actual_mw: Guard threshold for MAPE.

    Returns:
        One dictionary per delivery date in ascending date order.
    """
    rows: list[dict[str, object]] = []
    for delivery_date, subset in joined.groupby("delivery_date", sort=True):
        metrics = compute_metrics(subset, mape_min_actual_mw=mape_min_actual_mw)
        valid = subset.loc[subset["abs_error_mw"].notna()]
        if valid.empty:
            max_abs = None
            max_time = None
            mean_actual = None
        else:
            worst = valid.loc[valid["abs_error_mw"].idxmax()]
            max_abs = float(worst["abs_error_mw"])
            max_time = worst["start_time"]
            mean_actual = float(valid["actual_mw"].mean())
        rows.append(
            {
                "delivery_date": delivery_date,
                "metrics": metrics,
                "max_abs_mw": max_abs,
                "max_abs_time": max_time,
                "mean_actual_mw": mean_actual,
            }
        )
    return rows


def worst_days(joined: pd.DataFrame, n: int = 5) -> list[dict[str, object]]:
    """Return the ``n`` delivery days with the highest daily MAE."""
    days: list[dict[str, object]] = []
    for row in by_day(joined):
        metrics = cast(Metrics, row["metrics"])
        if metrics.mae_mw is not None:
            days.append(row)
    days.sort(key=lambda row: float(cast(Metrics, row["metrics"]).mae_mw or 0.0), reverse=True)
    return days[:n]


def worst_periods(joined: pd.DataFrame, n: int = 10) -> list[dict[str, object]]:
    """Return the ``n`` half-hours/hours with the largest absolute error."""
    valid = joined.loc[joined["abs_error_mw"].notna()].nlargest(n, "abs_error_mw")
    rows: list[dict[str, object]] = []
    for _, row in valid.iterrows():
        rows.append(
            {
                "start_time": row["start_time"],
                "delivery_date": row["delivery_date"],
                "forecast_mw": float(row["forecast_mw"]),
                "actual_mw": float(row["actual_mw"]),
                "error_mw": float(row["error_mw"]),
                "abs_error_mw": float(row["abs_error_mw"]),
            }
        )
    return rows

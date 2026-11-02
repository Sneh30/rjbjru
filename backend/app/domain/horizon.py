"""Horizon bucketing and error-growth analysis across all forecast vintages."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pandas as pd

from .metrics import compute_metrics
from .models import BucketMetrics

DEFAULT_HORIZON_EDGES: tuple[float, ...] = (0.0, 6.0, 12.0, 18.0, 24.0, 36.0, 48.0, 72.0)
INFINITY = float("inf")


def _label(start: float, end: float) -> str:
    left = f"{start:g}"
    right = f"{end:g}"
    return f"{left}-{right} h" if np.isfinite(end) else f"{left}+ h"


def horizon_buckets(
    joined: pd.DataFrame,
    edges: tuple[float, ...] = DEFAULT_HORIZON_EDGES,
    *,
    mape_min_actual_mw: float = 500.0,
) -> tuple[list[BucketMetrics], int]:
    """Compute metrics by forecast horizon across all vintages.

    Args:
        joined: Every forecast vintage joined to hourly actuals, including
            ``horizon_h``.
        edges: Bucket boundaries in hours. The final bucket extends to infinity.
        mape_min_actual_mw: Guard threshold passed to :func:`compute_metrics`.

    Returns:
        A tuple of (buckets, dropped_negative_horizon_count). Buckets are returned
        even when empty so the chart has a stable axis.
    """
    negative = int((joined["horizon_h"] < 0).sum())
    valid = joined.loc[joined["horizon_h"] >= 0].copy()
    cutoff_edges = (*edges, INFINITY)
    buckets: list[BucketMetrics] = []
    for start, end in pairwise(cutoff_edges):
        subset = valid.loc[(valid["horizon_h"] >= start) & (valid["horizon_h"] < end)]
        buckets.append(
            BucketMetrics(
                label=_label(start, end),
                from_value=float(start),
                to_value=float(end),
                metrics=compute_metrics(subset, mape_min_actual_mw=mape_min_actual_mw),
            )
        )
    return buckets, negative


def decision_band_h(selected: pd.DataFrame) -> tuple[float, float] | None:
    """Return the min/max horizon (hours) of the selected decision-time rows."""
    if selected.empty:
        return None
    return (
        float(selected["horizon_h"].min()),
        float(selected["horizon_h"].max()),
    )

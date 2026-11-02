"""Accuracy Lab services: scorecards, breakdowns and cutoff sensitivity."""

from __future__ import annotations

from datetime import date, time
from typing import cast

import numpy as np
import pandas as pd

from app.domain.baseline import baseline_summary
from app.domain.breakdowns import by_day, by_hour, by_level, worst_days, worst_periods
from app.domain.horizon import decision_band_h, horizon_buckets
from app.domain.metrics import compute_metrics
from app.domain.models import BucketMetrics, Metrics
from app.domain.timeutils import format_cutoff_label, parse_cutoff

from .analysis_service import AnalysisService
from .formatting import (
    horizon_stats,
    metrics_payload,
    mw,
    pct,
    utc_iso,
)

MAX_SCATTER_POINTS = 1500


def _bucket_payload(bucket: BucketMetrics) -> dict[str, object]:
    metrics = bucket.metrics
    return {
        "label": bucket.label,
        "n": metrics.n,
        "nmae_pct": pct(metrics.nmae_pct),
        "mae_mw": mw(metrics.mae_mw),
        "bias_mw": mw(metrics.bias_mw),
        "rmse_mw": mw(metrics.rmse_mw),
    }


def summary(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
) -> dict[str, object]:
    """Return the pooled scorecard for an inclusive delivery-date window."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    metrics = compute_metrics(joined, mape_min_actual_mw=service.settings.mape_min_actual_mw)
    baseline = baseline_summary(joined)
    coverage = service.window_coverage(cutoff, start, end)
    metrics_out = metrics_payload(metrics)
    metrics_out["n_missing_forecast"] = cast(int, coverage["expected_periods"]) - cast(
        int, coverage["with_forecast"]
    )
    baseline_out = {
        "name": baseline.name,
        "mae_mw": mw(baseline.mae_mw),
        "forecast_mae_mw": mw(baseline.forecast_mae_mw),
        "skill": pct(baseline.skill),
        "n": baseline.n,
    }
    return {
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "delivery_days": (end - start).days + 1,
            "expected_periods": coverage["expected_periods"],
        },
        "cutoff": format_cutoff_label(cutoff),
        "metrics": metrics_out,
        "baseline": baseline_out,
        "horizon_h": horizon_stats(joined["horizon_h"]),
        "coverage": coverage,
    }


def daily(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
) -> dict[str, object]:
    """Return one row of daily accuracy metrics per delivery day."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    rows: list[dict[str, object]] = []
    for row in by_day(joined, mape_min_actual_mw=service.settings.mape_min_actual_mw):
        metrics = row["metrics"]
        if not isinstance(metrics, Metrics):
            continue
        rows.append(
            {
                "delivery_date": str(row["delivery_date"]),
                "n": metrics.n,
                "mae_mw": mw(metrics.mae_mw),
                "bias_mw": mw(metrics.bias_mw),
                "rmse_mw": mw(metrics.rmse_mw),
                "nmae_pct": pct(metrics.nmae_pct),
                "max_abs_mw": mw(cast(float | None, row["max_abs_mw"])),
                "max_abs_time": utc_iso(row["max_abs_time"]),
                "shortfall_p90_mw": mw(metrics.shortfall_p90_mw),
                "mean_actual_mw": mw(cast(float | None, row["mean_actual_mw"])),
            }
        )
    return {"start": start.isoformat(), "end": end.isoformat(), "days": rows}


def by_horizon(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
) -> dict[str, object]:
    """Return error metrics by horizon across every available vintage."""
    start, end = service.ensure_window(start, end)
    joined = service.vintage_window(start, end)
    buckets, negative = horizon_buckets(
        joined,
        tuple(service.settings.horizon_buckets_h),
        mape_min_actual_mw=service.settings.mape_min_actual_mw,
    )
    band = decision_band_h(service.window(cutoff, start, end))
    bucket_rows = [
        {
            "from_h": round(float(bucket.from_value), 1),
            "to_h": (round(float(bucket.to_value), 1) if np.isfinite(bucket.to_value) else None),
            **_bucket_payload(bucket),
        }
        for bucket in buckets
    ]
    return {
        "buckets": bucket_rows,
        "decision_band_h": ({"min": round(band[0], 1), "max": round(band[1], 1)} if band else None),
        "dropped_negative_horizon": negative,
        "n_vintage_rows": int(len(joined)),
    }


def by_hour_breakdown(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
) -> dict[str, object]:
    """Return decision-time metrics by London hour of day."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    hours = by_hour(joined, mape_min_actual_mw=service.settings.mape_min_actual_mw)
    rows = []
    for hour, bucket in enumerate(hours):
        rows.append(
            {
                "hour": hour,
                "label": bucket.label,
                "n": bucket.metrics.n,
                "mae_mw": mw(bucket.metrics.mae_mw),
                "bias_mw": mw(bucket.metrics.bias_mw),
                "rmse_mw": mw(bucket.metrics.rmse_mw),
                "shortfall_p90_mw": mw(bucket.metrics.shortfall_p90_mw),
                "mean_actual_mw": mw(bucket.metrics.mean_actual_mw),
            }
        )
    return {"hours": rows}


def by_level_breakdown(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
    *,
    basis: str,
    bins: int,
) -> dict[str, object]:
    """Return decision-time metrics by equal-count wind-output bins."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    buckets = by_level(
        joined,
        basis=basis,
        bins=bins,
        mape_min_actual_mw=service.settings.mape_min_actual_mw,
    )
    rows = [
        {
            "label": bucket.label,
            "from_mw": mw(bucket.from_value),
            "to_mw": mw(bucket.to_value),
            "n": bucket.metrics.n,
            "mae_mw": mw(bucket.metrics.mae_mw),
            "bias_mw": mw(bucket.metrics.bias_mw),
            "nmae_pct": pct(bucket.metrics.nmae_pct),
        }
        for bucket in buckets
    ]
    return {"basis": basis, "bins": rows}


def _downsample(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Select at most ``limit`` rows deterministically and evenly across the window."""
    if len(frame) <= limit:
        return frame
    indices = np.linspace(0, len(frame) - 1, num=limit).round().astype(int)
    return cast(pd.DataFrame, frame.iloc[np.unique(indices)])


def distribution(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
    *,
    bins: int,
) -> dict[str, object]:
    """Return a signed-error histogram, quantiles and a deterministic scatter sample."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    valid = joined.loc[joined["error_mw"].notna()].sort_values("start_time").reset_index(drop=True)
    errors = valid["error_mw"].to_numpy(dtype=float)
    histogram: list[dict[str, object]] = []
    if len(errors):
        low, high = float(np.min(errors)), float(np.max(errors))
        if high == low:
            high = low + 1.0
        edges = np.linspace(low, high, num=bins + 1)
        counts, _ = np.histogram(errors, bins=edges)
        histogram = [
            {
                "from_mw": mw(float(edges[index])),
                "to_mw": mw(float(edges[index + 1])),
                "count": int(counts[index]),
            }
            for index in range(bins)
        ]
        quantiles = {
            "p5": mw(float(np.percentile(errors, 5, method="linear"))),
            "p50": mw(float(np.percentile(errors, 50, method="linear"))),
            "p95": mw(float(np.percentile(errors, 95, method="linear"))),
            "shortfall_p90": mw(
                float(np.percentile(np.clip(errors, 0, None), 90, method="linear"))
            ),
        }
    else:
        quantiles = {"p5": None, "p50": None, "p95": None, "shortfall_p90": None}
    scatter_frame = _downsample(valid, MAX_SCATTER_POINTS)
    scatter = [
        {
            "forecast_mw": mw(float(row["forecast_mw"])),
            "actual_mw": mw(float(row["actual_mw"])),
            "start_time": utc_iso(row["start_time"]),
        }
        for _, row in scatter_frame.iterrows()
    ]
    return {
        "histogram": histogram,
        "quantiles": quantiles,
        "scatter": scatter,
        "scatter_total": int(len(valid)),
        "scatter_limit": MAX_SCATTER_POINTS,
    }


def worst(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
    *,
    n: int,
    metric: str,
) -> dict[str, object]:
    """Return the worst delivery days and the worst individual periods."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    day_rows = worst_days(joined, n=max(n, 10))
    allowed = {"mae", "rmse", "bias", "shortfall_p90"}
    if metric == "bias":
        day_rows.sort(
            key=lambda row: abs(float(cast(Metrics, row["metrics"]).bias_mw or 0.0)),
            reverse=True,
        )
    elif metric in {"rmse", "shortfall_p90"}:
        attr = "rmse_mw" if metric == "rmse" else "shortfall_p90_mw"
        day_rows.sort(
            key=lambda row: float(getattr(cast(Metrics, row["metrics"]), attr) or 0.0),
            reverse=True,
        )
    elif metric not in allowed:
        raise ValueError("unsupported worst-day metric")
    day_rows = day_rows[:n]

    days_out: list[dict[str, object]] = []
    for row in day_rows:
        metrics = row["metrics"]
        if not isinstance(metrics, Metrics):
            continue
        days_out.append(
            {
                "delivery_date": str(row["delivery_date"]),
                "n": metrics.n,
                "mae_mw": mw(metrics.mae_mw),
                "bias_mw": mw(metrics.bias_mw),
                "rmse_mw": mw(metrics.rmse_mw),
                "max_abs_mw": mw(cast(float | None, row["max_abs_mw"])),
                "max_abs_time": utc_iso(row["max_abs_time"]),
            }
        )
    periods_out = [
        {
            "start_time": utc_iso(row["start_time"]),
            "delivery_date": str(row["delivery_date"]),
            "forecast_mw": mw(cast(float, row["forecast_mw"])),
            "actual_mw": mw(cast(float, row["actual_mw"])),
            "error_mw": mw(cast(float, row["error_mw"])),
        }
        for row in worst_periods(joined, n=n)
    ]
    return {"metric": metric, "days": days_out, "periods": periods_out}


def cutoff_sensitivity(
    service: AnalysisService,
    start: date,
    end: date,
) -> dict[str, object]:
    """Return metrics and coverage for every configured decision cutoff."""
    start, end = service.ensure_window(start, end)
    rows: list[dict[str, object]] = []
    for value in service.settings.cutoff_grid:
        cutoff = parse_cutoff(format_cutoff_label(value))
        joined = service.window(cutoff, start, end)
        metrics = compute_metrics(joined, mape_min_actual_mw=service.settings.mape_min_actual_mw)
        coverage = service.window_coverage(cutoff, start, end)
        rows.append(
            {
                "cutoff": format_cutoff_label(cutoff),
                "n": metrics.n,
                "mae_mw": mw(metrics.mae_mw),
                "bias_mw": mw(metrics.bias_mw),
                "shortfall_p90_mw": mw(metrics.shortfall_p90_mw),
                "mean_horizon_h": (
                    round(float(joined["horizon_h"].dropna().mean()), 1)
                    if joined["horizon_h"].notna().any()
                    else None
                ),
                "coverage_pct": coverage["coverage_pct"],
            }
        )
    return {"rows": rows}

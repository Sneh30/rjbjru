"""Serialisation helpers shared by the service layer.

The domain never rounds. Rounding happens once, here, at the API boundary:
MW to one decimal place and percentages to two decimal places.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

import pandas as pd

from app.domain.constants import LONDON
from app.domain.models import Metrics
from app.domain.timeutils import cutoff_for_delivery_date, format_cutoff_label


def utc_iso(value: Any) -> str | None:
    """Return an ISO-8601 UTC string with a trailing ``Z``.

    Args:
        value: A timestamp-like value, or ``None``/``NaT``.

    Returns:
        ``YYYY-MM-DDTHH:MM:SSZ`` or ``None``.
    """
    if value is None:
        return None
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").isoformat(timespec="seconds").replace("+00:00", "Z")


def london_iso(value: Any) -> str | None:
    """Return an ISO-8601 Europe/London string with its UTC offset."""
    if value is None:
        return None
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert(LONDON).isoformat(timespec="seconds")


def local_date(value: Any) -> date | None:
    """Return the Europe/London calendar date of a UTC instant."""
    if value is None:
        return None
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert(LONDON).date()


def mw(value: float | None) -> float | None:
    """Round a MW value to one decimal place."""
    return None if value is None else round(float(value), 1)


def pct(value: float | None) -> float | None:
    """Round a percentage or fraction to two decimal places.

    Fractions such as ``over_forecast_share`` are intentionally not multiplied by
    100 here; the field name and API documentation identify it as a fraction.
    """
    return None if value is None else round(float(value), 2)


def cutoff_payload(delivery_date: date, cutoff_local: time) -> dict[str, object]:
    """Build the common cutoff object for a delivery date."""
    cutoff = cutoff_for_delivery_date(delivery_date, cutoff_local)
    return {
        "local": london_iso(cutoff),
        "utc": utc_iso(cutoff),
        "time": format_cutoff_label(cutoff_local),
        "timezone": "Europe/London",
    }


def metrics_payload(metrics: Metrics) -> dict[str, object]:
    """Convert a domain :class:`Metrics` object to API-ready values."""
    return {
        "n": metrics.n,
        "n_missing_actual": metrics.n_missing_actual,
        "mean_actual_mw": mw(metrics.mean_actual_mw),
        "mae_mw": mw(metrics.mae_mw),
        "rmse_mw": mw(metrics.rmse_mw),
        "bias_mw": mw(metrics.bias_mw),
        "nmae_pct": pct(metrics.nmae_pct),
        "wape_pct": pct(metrics.wape_pct),
        "mape_pct": pct(metrics.mape_pct),
        "mape_n": metrics.mape_n,
        "p50_abs_mw": mw(metrics.p50_abs_mw),
        "p90_abs_mw": mw(metrics.p90_abs_mw),
        "p95_abs_mw": mw(metrics.p95_abs_mw),
        "p5_err_mw": mw(metrics.p5_err_mw),
        "p50_err_mw": mw(metrics.p50_err_mw),
        "p95_err_mw": mw(metrics.p95_err_mw),
        "over_forecast_share": pct(metrics.over_forecast_share),
        "shortfall_mean_mw": mw(metrics.shortfall_mean_mw),
        "shortfall_p90_mw": mw(metrics.shortfall_p90_mw),
        "shortfall_p95_mw": mw(metrics.shortfall_p95_mw),
        "shortfall_max_mw": mw(metrics.shortfall_max_mw),
        "correlation": pct(metrics.correlation),
    }


def horizon_stats(values: pd.Series[Any]) -> dict[str, float | None]:
    """Return min/mean/max horizon in hours."""
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {"min": None, "mean": None, "max": None}
    return {
        "min": round(float(numeric.min()), 1),
        "mean": round(float(numeric.mean()), 1),
        "max": round(float(numeric.max()), 1),
    }

"""Frame builders shared by the test suites.

These helpers deliberately build minimal frames rather than copying production
normalisation logic, so a broken normaliser cannot make its own test pass.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


def utc(values: list[str]) -> pd.Series[Any]:
    """Parse strings into a UTC-aware pandas series."""
    return pd.to_datetime(pd.Series(values), utc=True)


def forecast_frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """Build a forecast frame from ``(target, publish, MW)`` tuples."""
    frame = pd.DataFrame(rows, columns=["start_time", "publish_time", "generation_mw"])
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["publish_time"] = pd.to_datetime(frame["publish_time"], utc=True)
    frame["generation_mw"] = frame["generation_mw"].astype(float)
    return frame


def hourly_actuals(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Build an hourly actuals frame from ``(start, MW)`` tuples."""
    frame = pd.DataFrame(rows, columns=["start_time", "actual_mw"])
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["actual_mw"] = frame["actual_mw"].astype(float)
    return frame


def half_hourly_actuals(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Build a half-hourly raw actuals frame from ``(start, MW)`` tuples."""
    frame = pd.DataFrame(rows, columns=["start_time", "generation_mw"])
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["generation_mw"] = frame["generation_mw"].astype(float)
    return frame


def joined_errors(
    rows: list[tuple[date, float, float]],
    *,
    start_time: str = "2026-01-15T12:00:00Z",
) -> pd.DataFrame:
    """Build a joined frame from ``(delivery_date, actual_mw, error_mw)`` tuples.

    ``forecast_mw`` is derived as ``actual + error`` so the sign convention is
    unambiguous. Each row uses the same target instant unless callers overwrite it.
    """
    records = []
    for delivery_date, actual, error in rows:
        records.append(
            {
                "delivery_date": delivery_date,
                "start_time": pd.Timestamp(start_time),
                "forecast_mw": actual + error,
                "actual_mw": actual,
                "error_mw": error,
                "abs_error_mw": abs(error),
                "shortfall_mw": max(0.0, error),
            }
        )
    frame = pd.DataFrame.from_records(records)
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    return frame

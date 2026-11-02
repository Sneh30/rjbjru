"""Decision-time vintage selection.

The product rule is: for each target time T, use the WINDFOR row with the greatest
``publish_time`` that is less than or equal to the decision cutoff for T's London
delivery day. The boundary is inclusive. Post-conditions are asserted on every call.
"""

from __future__ import annotations

from datetime import time
from typing import Literal

import pandas as pd

from .errors import DataIntegrityError
from .timeutils import decision_cutoff_utc, london_delivery_date

REQUIRED_FORECAST_COLUMNS = ("start_time", "publish_time", "generation_mw")
SELECTED_COLUMNS = (
    "start_time",
    "publish_time",
    "forecast_mw",
    "horizon_h",
    "cutoff_utc",
    "delivery_date",
)


def _empty_selected() -> pd.DataFrame:
    """Return an empty selected frame with stable dtypes."""
    return pd.DataFrame(
        {
            "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
            "publish_time": pd.Series(dtype="datetime64[ns, UTC]"),
            "forecast_mw": pd.Series(dtype="float64"),
            "horizon_h": pd.Series(dtype="float64"),
            "cutoff_utc": pd.Series(dtype="datetime64[ns, UTC]"),
            "delivery_date": pd.Series(dtype="object"),
        },
        columns=list(SELECTED_COLUMNS),
    )


def _validate_forecast_frame(forecasts: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_FORECAST_COLUMNS if col not in forecasts.columns]
    if missing:
        raise DataIntegrityError(f"forecast frame is missing columns: {missing}")
    for col in ("start_time", "publish_time"):
        if not isinstance(forecasts[col].dtype, pd.DatetimeTZDtype):
            raise DataIntegrityError(f"{col} must be timezone-aware UTC")
    if str(forecasts["publish_time"].dt.tz) != "UTC":
        raise DataIntegrityError("publish_time must be in UTC")


def _assert_no_leakage(selected: pd.DataFrame) -> None:
    """Assert one row per target and no publish after the cutoff."""
    if selected.empty:
        return
    if bool(selected["start_time"].duplicated().any()):
        raise DataIntegrityError("selection returned more than one row per target")
    if not bool((selected["publish_time"] <= selected["cutoff_utc"]).all()):
        raise DataIntegrityError("selection contains a forecast published after the cutoff")
    if bool(selected["start_time"].isna().any()):
        raise DataIntegrityError("selection contains a null target time")


def _select(
    forecasts: pd.DataFrame,
    cutoff_local: time,
    *,
    mode: Literal["latest", "earliest"],
) -> pd.DataFrame:
    """Shared selector for the latest or earliest eligible vintage per target."""
    _validate_forecast_frame(forecasts)
    if forecasts.empty:
        return _empty_selected()

    frame = forecasts.copy()
    frame["cutoff_utc"] = decision_cutoff_utc(frame["start_time"], cutoff_local)
    eligible = frame.loc[frame["publish_time"] <= frame["cutoff_utc"]]
    if eligible.empty:
        return _empty_selected()

    grouped = eligible.groupby("start_time", sort=True)["publish_time"]
    idx = grouped.idxmax() if mode == "latest" else grouped.idxmin()
    selected = eligible.loc[idx].copy()
    selected["horizon_h"] = (
        selected["start_time"] - selected["publish_time"]
    ).dt.total_seconds() / 3600.0
    selected["delivery_date"] = london_delivery_date(selected["start_time"]).dt.date
    selected = selected.rename(columns={"generation_mw": "forecast_mw"})
    selected = selected.loc[:, list(SELECTED_COLUMNS)].sort_values("start_time")
    _assert_no_leakage(selected)
    return selected.reset_index(drop=True)


def select_decision_forecasts(forecasts: pd.DataFrame, cutoff_local: time) -> pd.DataFrame:
    """Return the latest forecast available at the decision cutoff for each target.

    Args:
        forecasts: Columns ``start_time`` and ``publish_time`` (tz-aware UTC) and
            ``generation_mw`` (MW, hourly WINDFOR resolution).
        cutoff_local: Wall-clock cutoff on the previous London day.

    Returns:
        One row per target with an eligible vintage. Columns: ``start_time``,
        ``publish_time``, ``forecast_mw`` (MW), ``horizon_h`` (hours),
        ``cutoff_utc``, ``delivery_date``.

    Raises:
        DataIntegrityError: if the frame shape or a no-leakage post-condition fails.
    """
    return _select(forecasts, cutoff_local, mode="latest")


def select_earliest_forecasts(forecasts: pd.DataFrame, cutoff_local: time) -> pd.DataFrame:
    """Return the earliest eligible vintage per target, for vintage-value comparison.

    Args:
        forecasts: As for :func:`select_decision_forecasts`.
        cutoff_local: Wall-clock cutoff on the previous London day.

    Returns:
        The same schema as :func:`select_decision_forecasts`.
    """
    return _select(forecasts, cutoff_local, mode="earliest")

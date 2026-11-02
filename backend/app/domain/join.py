"""Joining forecasts to actuals and computing the buyer-centric error series."""

from __future__ import annotations

import pandas as pd


def join_selected_actuals(selected: pd.DataFrame, hourly_actuals: pd.DataFrame) -> pd.DataFrame:
    """Join selected forecasts to hourly actuals and derive error columns.

    Args:
        selected: Output of :func:`app.domain.selection.select_decision_forecasts`.
        hourly_actuals: Columns ``start_time`` (hourly UTC) and ``actual_mw`` (MW).

    Returns:
        ``selected`` plus ``actual_mw``, ``error_mw`` (= forecast - actual),
        ``abs_error_mw`` and ``shortfall_mw`` (= max(0, error)). Rows with a missing
        actual are kept with null error columns.
    """
    actuals = hourly_actuals.loc[:, ["start_time", "actual_mw"]]
    joined = selected.merge(actuals, on="start_time", how="left", validate="one_to_one")
    joined["error_mw"] = joined["forecast_mw"] - joined["actual_mw"]
    joined["abs_error_mw"] = joined["error_mw"].abs()
    joined["shortfall_mw"] = joined["error_mw"].clip(lower=0.0)
    return joined


def join_all_vintages(
    forecasts: pd.DataFrame,
    hourly_actuals: pd.DataFrame,
) -> pd.DataFrame:
    """Join every forecast vintage to actuals for horizon analysis.

    Only targets present in ``hourly_actuals`` survive. Rows with a negative horizon
    (target already in the past at publication) are retained here and counted by the
    caller; they are never eligible for a decision view.
    """
    actuals = hourly_actuals.loc[:, ["start_time", "actual_mw"]]
    joined = forecasts.merge(actuals, on="start_time", how="inner")
    joined = joined.rename(columns={"generation_mw": "forecast_mw"})
    joined["horizon_h"] = (
        joined["start_time"] - joined["publish_time"]
    ).dt.total_seconds() / 3600.0
    joined["error_mw"] = joined["forecast_mw"] - joined["actual_mw"]
    joined["abs_error_mw"] = joined["error_mw"].abs()
    joined["shortfall_mw"] = joined["error_mw"].clip(lower=0.0)
    return joined

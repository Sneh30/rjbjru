"""Decision-view service: the forecast a buyer could actually have seen."""

from __future__ import annotations

from datetime import date, time
from typing import Any, cast

import pandas as pd

from app.domain.metrics import compute_metrics, energy_mwh, max_ramp_mw

from .analysis_service import AnalysisService, london_day_hours
from .formatting import (
    cutoff_payload,
    horizon_stats,
    local_date,
    london_iso,
    metrics_payload,
    mw,
    utc_iso,
)


def _point(row: pd.Series[Any], *, include_actuals: bool) -> dict[str, object]:
    """Build one decision-view point."""
    payload: dict[str, object] = {
        "start_time": utc_iso(row["start_time"]),
        "local_time": london_iso(row["start_time"]),
        "forecast_mw": mw(row["forecast_mw"]),
        "publish_time": utc_iso(row["publish_time"]),
        "horizon_h": round(float(row["horizon_h"]), 1),
    }
    if include_actuals:
        actual = cast(float | None, row["actual_mw"])
        has_actual = actual is not None and bool(pd.notna(actual))
        payload["actual_mw"] = mw(actual)
        payload["error_mw"] = (
            mw(float(row["error_mw"])) if has_actual and pd.notna(row["error_mw"]) else None
        )
        payload["shortfall_mw"] = (
            mw(float(row["shortfall_mw"])) if has_actual and pd.notna(row["shortfall_mw"]) else None
        )
    return payload


def decision_view(
    service: AnalysisService,
    delivery_date: date,
    cutoff: time,
    *,
    include_actuals: bool = False,
) -> dict[str, object]:
    """Build the Decision desk payload for one London delivery day.

    Args:
        service: Snapshot-backed analysis service.
        delivery_date: In-scope London delivery date.
        cutoff: Wall-clock decision cutoff on the previous London day.
        include_actuals: Attach hindsight actuals, errors and day metrics.

    Returns:
        A JSON-ready mapping matching the API response model.

    Raises:
        OutOfScopeError: if the delivery date is outside the configured scope.
    """
    service.ensure_delivery_date(delivery_date)
    expected = london_day_hours(delivery_date)
    selected = service.selected(cutoff)
    day = selected.loc[selected["delivery_date"] == delivery_date].sort_values("start_time")
    actuals = service.repository.hourly_actuals()
    actual_map = (
        actuals.loc[actuals["actual_mw"].notna()].set_index("start_time")["actual_mw"].astype(float)
    )

    forecast_times = set(day["start_time"])
    missing_forecasts = [utc_iso(stamp) for stamp in expected if stamp not in forecast_times]
    missing_actuals = [
        utc_iso(stamp) for stamp in expected if not bool(pd.notna(actual_map.get(stamp)))
    ]

    joined = service.window(cutoff, delivery_date, delivery_date)
    points = [_point(row, include_actuals=include_actuals) for _, row in joined.iterrows()]

    forecast_series = joined.loc[joined["forecast_mw"].notna(), "forecast_mw"].astype(float)
    summary: dict[str, object] = {
        "mean_mw": mw(float(forecast_series.mean())) if not forecast_series.empty else None,
        "peak_mw": mw(float(forecast_series.max())) if not forecast_series.empty else None,
        "peak_time": (
            utc_iso(joined.loc[forecast_series.idxmax(), "start_time"])
            if not forecast_series.empty
            else None
        ),
        "min_mw": mw(float(forecast_series.min())) if not forecast_series.empty else None,
        "min_time": (
            utc_iso(joined.loc[forecast_series.idxmin(), "start_time"])
            if not forecast_series.empty
            else None
        ),
        "energy_mwh": mw(energy_mwh(forecast_series)) if not forecast_series.empty else None,
        "max_ramp_1h_mw": max_ramp_mw(forecast_series, 1) if len(forecast_series) > 1 else None,
        "max_ramp_3h_mw": max_ramp_mw(forecast_series, 3) if len(forecast_series) > 3 else None,
        "latest_publish_time": utc_iso(day["publish_time"].max()) if not day.empty else None,
        "earliest_publish_time": utc_iso(day["publish_time"].min()) if not day.empty else None,
        "horizon_h": horizon_stats(joined["horizon_h"]),
    }

    payload: dict[str, object] = {
        "delivery_date": delivery_date.isoformat(),
        "delivery_date_local": delivery_date.strftime("%d %b %Y"),
        "cutoff": cutoff_payload(delivery_date, cutoff),
        "resolution_minutes": 60,
        "points": points,
        "summary": summary,
        "coverage": {
            "expected_periods": len(expected),
            "with_forecast": int(len(day)),
            "with_actual": len(expected) - len(missing_actuals),
            "missing_forecast_periods": missing_forecasts,
            "missing_actual_periods": missing_actuals,
        },
    }
    if include_actuals:
        metrics = compute_metrics(
            joined,
            mape_min_actual_mw=service.settings.mape_min_actual_mw,
        )
        day_metrics = metrics_payload(metrics)
        day_metrics["n_missing_forecast"] = len(missing_forecasts)
        payload["day_metrics"] = day_metrics
    return payload


def decision_target_local_time(start_time: object) -> str | None:
    """Return the London date label for a target instant (helper for tests/UI)."""
    day = local_date(start_time)
    return day.isoformat() if day is not None else None

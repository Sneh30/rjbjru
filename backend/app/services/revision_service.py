"""Revision explorer service: every vintage around a target and the cutoff."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import cast

import pandas as pd

from app.domain.errors import NoDataError, OutOfScopeError

from .analysis_service import AnalysisService, london_midnight_utc
from .formatting import cutoff_payload, local_date, mw, utc_iso

REVISION_LOOKAHEAD_HOURS = 6


def resolve_target(
    *,
    target_time: datetime | None,
    delivery_date: date | None,
    period: int | None,
) -> tuple[pd.Timestamp, date]:
    """Resolve either a target instant or a delivery date plus hourly period.

    Args:
        target_time: UTC target instant, if supplied.
        delivery_date: London delivery date, if supplied.
        period: One-based London hour (1-24) when a date is supplied.

    Returns:
        A tuple of the UTC target timestamp and its London delivery date.

    Raises:
        ValueError: if the combination is ambiguous or incomplete.
        OutOfScopeError: if the target instant is not on an hourly boundary.
    """
    if target_time is not None:
        if delivery_date is not None or period is not None:
            raise ValueError("provide either target_time or delivery_date+period, not both")
        if target_time.tzinfo is None:
            raise ValueError("target_time must include a UTC offset")
        target = pd.Timestamp(target_time).tz_convert("UTC")
        day = local_date(target)
        assert day is not None
    else:
        if delivery_date is None or period is None:
            raise ValueError("provide target_time or both delivery_date and period")
        if not 1 <= period <= 24:
            raise ValueError("period must be between 1 and 24 for hourly WINDFOR data")
        target = london_midnight_utc(delivery_date) + pd.Timedelta(hours=period - 1)
        day = delivery_date
    if target.minute != 0 or target.second != 0 or target.microsecond != 0:
        raise OutOfScopeError(
            "WINDFOR targets are hourly; target_time must be on the hour",
            extra={"resolution_minutes": 60},
        )
    return target, day


def revisions(
    service: AnalysisService,
    *,
    target_time: datetime | None = None,
    delivery_date: date | None = None,
    period: int | None = None,
    cutoff: time,
) -> dict[str, object]:
    """Build the vintage history for one target.

    Vintages are shown up to six hours after the cutoff so the UI can illustrate
    what would have been leakage; only rows with ``publish_time <= cutoff`` are
    marked eligible.
    """
    target, target_day = resolve_target(
        target_time=target_time, delivery_date=delivery_date, period=period
    )
    service.ensure_delivery_date(target_day)
    cutoff_info = cutoff_payload(target_day, cutoff)
    cutoff_ts = pd.Timestamp(str(cutoff_info["utc"]).replace("Z", "+00:00"))

    forecasts = service.repository.forecasts()
    rows = forecasts.loc[forecasts["start_time"] == target].sort_values("publish_time")
    if rows.empty:
        raise NoDataError(
            f"no WINDFOR vintages exist for {utc_iso(target)}",
            extra={"target_time": utc_iso(target)},
        )
    horizon_limit = cutoff_ts + pd.Timedelta(hours=REVISION_LOOKAHEAD_HOURS)
    shown = rows.loc[rows["publish_time"] <= horizon_limit]
    if shown.empty:
        shown = rows.iloc[[0]]

    eligible_rows = shown.loc[shown["publish_time"] <= cutoff_ts]
    selected_publish: pd.Timestamp | None = None
    if not eligible_rows.empty:
        selected_publish = cast(pd.Timestamp, eligible_rows["publish_time"].max())

    actuals = service.repository.hourly_actuals()
    actual_rows = actuals.loc[actuals["start_time"] == target]
    actual = (
        float(actual_rows.iloc[0]["actual_mw"])
        if not actual_rows.empty and pd.notna(actual_rows.iloc[0]["actual_mw"])
        else None
    )

    vintages: list[dict[str, object]] = []
    eligible_values: list[float] = []
    for _, row in shown.iterrows():
        publish = pd.Timestamp(row["publish_time"])
        eligible = bool(publish <= cutoff_ts)
        forecast_value = float(row["generation_mw"])
        if eligible:
            eligible_values.append(forecast_value)
        vintages.append(
            {
                "publish_time": utc_iso(publish),
                "publish_time_local": pd.Timestamp(publish).tz_convert("Europe/London").isoformat(),
                "horizon_h": round((target - publish).total_seconds() / 3600.0, 1),
                "forecast_mw": mw(forecast_value),
                "eligible": eligible,
                "selected": bool(selected_publish is not None and publish == selected_publish),
            }
        )

    selected_forecast: float | None = None
    if selected_publish is not None:
        selected_forecast = float(
            eligible_rows.loc[
                eligible_rows["publish_time"] == selected_publish, "generation_mw"
            ].iloc[0]
        )
    revision_range: dict[str, float | None]
    if eligible_values:
        revision_range = {
            "min": mw(min(eligible_values)),
            "max": mw(max(eligible_values)),
            "spread": mw(max(eligible_values) - min(eligible_values)),
        }
    else:
        revision_range = {"min": None, "max": None, "spread": None}

    return {
        "target_time": utc_iso(target),
        "target_time_local": pd.Timestamp(target).tz_convert("Europe/London").isoformat(),
        "delivery_date": target_day.isoformat(),
        "cutoff": cutoff_info,
        "vintages": vintages,
        "selected_publish_time": utc_iso(selected_publish),
        "selected_forecast_mw": mw(selected_forecast),
        "actual_mw": mw(actual),
        "error_mw": (
            mw(selected_forecast - actual)
            if actual is not None and selected_forecast is not None
            else None
        ),
        "revision_range_mw": revision_range,
        "shown_until": utc_iso(horizon_limit),
        "lookahead_hours": REVISION_LOOKAHEAD_HOURS,
        "eligibility_note": (
            "eligible means publish_time <= cutoff (inclusive); later vintages are shown "
            "only to illustrate information that was not available at decision time"
        ),
        "resolution_minutes": 60,
    }


def revision_targets_for_day(
    service: AnalysisService, day: date, cutoff: time
) -> list[dict[str, object]]:
    """Return selectable target options for a delivery day, for the UI selector."""
    service.ensure_delivery_date(day)
    selected = service.selected(cutoff)
    rows = selected.loc[selected["delivery_date"] == day].sort_values("start_time")
    return [
        {
            "target_time": utc_iso(row["start_time"]),
            "local_time": pd.Timestamp(row["start_time"]).tz_convert("Europe/London").isoformat(),
            "forecast_mw": mw(float(row["forecast_mw"])),
        }
        for _, row in rows.iterrows()
    ]


def default_target_for_day(
    service: AnalysisService, day: date, cutoff: time
) -> dict[str, object] | None:
    """Return the peak-forecast target of a day, matching the PRD default."""
    options = revision_targets_for_day(service, day, cutoff)
    if not options:
        return None
    return max(options, key=lambda item: float(cast(float, item["forecast_mw"]) or 0.0))


def target_from_delivery_period(delivery_date: date, period: int) -> pd.Timestamp:
    """Return the UTC hourly target for a one-based London delivery period."""
    return london_midnight_utc(delivery_date) + pd.Timedelta(hours=period - 1)


def next_day(day: date) -> date:
    """Return the following calendar day."""
    return day + timedelta(days=1)

"""Snapshot validation and the committed quality report."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import Settings
from app.domain.errors import DataIntegrityError
from app.domain.selection import select_decision_forecasts
from app.domain.timeutils import format_cutoff_label, london_delivery_date

from .normalise import NormaliseStats

MAX_NAN_SHARE = 0.01
EXPECTED_FORECAST_HOURS_PER_DAY = 24
EXPECTED_ACTUAL_HALF_HOURS_PER_DAY = 48


def _hard_check_actuals(actuals: pd.DataFrame) -> None:
    if actuals.empty:
        raise DataIntegrityError("no WIND actuals were normalised")
    if actuals["start_time"].dt.tz is None:
        raise DataIntegrityError("actuals are not timezone-aware")
    minutes = set(actuals["start_time"].dt.minute.unique())
    seconds = set(actuals["start_time"].dt.second.unique())
    if not minutes.issubset({0, 30}) or seconds != {0}:
        raise DataIntegrityError("actuals are not aligned to half-hour settlement periods")
    if bool(actuals["start_time"].duplicated().any()):
        raise DataIntegrityError("actuals contain duplicate start_time rows")
    if bool(actuals["generation_mw"].isna().any()):
        raise DataIntegrityError("actuals contain null generation after normalisation")
    if bool((actuals["generation_mw"] < 0).any()):
        raise DataIntegrityError("actuals contain negative WIND generation")


def _hard_check_forecasts(forecasts: pd.DataFrame) -> None:
    if forecasts.empty:
        raise DataIntegrityError("no WINDFOR rows were normalised")
    if forecasts["start_time"].dt.tz is None or forecasts["publish_time"].dt.tz is None:
        raise DataIntegrityError("forecast timestamps are not timezone-aware")
    if set(forecasts["start_time"].dt.minute.unique()) != {0}:
        raise DataIntegrityError("WINDFOR targets are not hourly as verified")
    if bool(forecasts.duplicated(["start_time", "publish_time"]).any()):
        raise DataIntegrityError("forecasts contain duplicate (start_time, publish_time) rows")
    if bool(forecasts["generation_mw"].isna().any()):
        raise DataIntegrityError("forecasts contain null generation after normalisation")
    if bool((forecasts["generation_mw"] < 0).any()):
        raise DataIntegrityError("forecasts contain negative WIND generation")


def _actual_window(settings: Settings) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(settings.ingest_actuals_start)
    end = pd.Timestamp(settings.ingest_actuals_end)
    return start, end


def _missing_actual_periods(actuals: pd.DataFrame, settings: Settings) -> list[str]:
    start, end = _actual_window(settings)
    expected = pd.date_range(start, end - pd.Timedelta(minutes=30), freq="30min", tz="UTC")
    present = pd.DatetimeIndex(actuals["start_time"])
    missing = expected.difference(present)
    return [stamp.isoformat() for stamp in missing]


def _decision_coverage(
    forecasts: pd.DataFrame,
    settings: Settings,
) -> dict[str, object]:
    selected = select_decision_forecasts(forecasts, settings.default_cutoff)
    delivery_dates = settings.delivery_dates()
    missing: list[str] = []
    with_forecast = 0
    expected = 0
    for day in delivery_dates:
        subset = selected.loc[selected["delivery_date"] == day]
        expected += EXPECTED_FORECAST_HOURS_PER_DAY
        with_forecast += len(subset)
        if len(subset) != EXPECTED_FORECAST_HOURS_PER_DAY:
            expected_times = pd.date_range(
                f"{day}T00:00:00Z",
                f"{day}T23:00:00Z",
                freq="1h",
                tz="UTC",
            )
            present = set(subset["start_time"])
            missing.extend(stamp.isoformat() for stamp in expected_times if stamp not in present)
    coverage_pct = (with_forecast / expected * 100.0) if expected else 0.0
    return {
        "cutoff": format_cutoff_label(settings.default_cutoff),
        "delivery_days": len(delivery_dates),
        "hourly_periods_expected": expected,
        "hourly_periods_with_forecast": with_forecast,
        "hourly_periods_missing": missing,
        "coverage_pct": round(coverage_pct, 2),
        "resolution_note": (
            "WINDFOR is hourly (24 targets/day); FUELHH is half-hourly (48 actuals/day). "
            "Actuals are averaged in pairs for like-for-like evaluation."
        ),
    }


def build_quality_report(
    settings: Settings,
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    actual_stats: NormaliseStats,
    forecast_stats: NormaliseStats,
) -> dict[str, object]:
    """Validate the snapshot and return a JSON-serialisable quality report.

    Raises:
        DataIntegrityError: on any hard data failure.
    """
    _hard_check_actuals(actuals)
    _hard_check_forecasts(forecasts)

    missing_actuals = _missing_actual_periods(actuals, settings)
    coverage = _decision_coverage(forecasts, settings)
    horizons = (forecasts["start_time"] - forecasts["publish_time"]).dt.total_seconds() / 3600.0
    delivery_days = london_delivery_date(actuals["start_time"]).dt.date.nunique()
    warnings: list[str] = []
    if missing_actuals:
        warnings.append(
            f"{len(missing_actuals)} FUELHH half-hour actual periods are missing in the window"
        )
    missing_forecasts = int(coverage["hourly_periods_expected"]) - int(
        coverage["hourly_periods_with_forecast"]
    )
    if missing_forecasts:
        warnings.append(
            f"{missing_forecasts} hourly decision-time forecast periods are missing at "
            f"{coverage['cutoff']} on D-1"
        )
    if forecast_stats.duplicate_rows:
        warnings.append(f"{forecast_stats.duplicate_rows} duplicate forecast vintages were removed")
    if actual_stats.nan_rows or forecast_stats.nan_rows:
        warnings.append("Rows with non-numeric generation were dropped and counted")

    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "actuals": {
            "rows": int(len(actuals)),
            "expected_rows": int(
                (
                    pd.Timestamp(settings.ingest_actuals_end)
                    - pd.Timestamp(settings.ingest_actuals_start)
                )
                / pd.Timedelta(minutes=30)
            ),
            "delivery_days": int(delivery_days),
            "missing_periods": missing_actuals,
            "duplicates_dropped": actual_stats.duplicate_rows,
            "nan_dropped": actual_stats.nan_rows,
            "non_wind_dropped": actual_stats.non_wind_rows,
            "min_mw": float(actuals["generation_mw"].min()),
            "max_mw": float(actuals["generation_mw"].max()),
            "mean_mw": float(actuals["generation_mw"].mean()),
            "resolution_minutes": 30,
        },
        "forecasts": {
            "rows": int(len(forecasts)),
            "vintages": int(forecasts["publish_time"].nunique()),
            "targets": int(forecasts["start_time"].nunique()),
            "first_publish": forecasts["publish_time"].min().isoformat(),
            "last_publish": forecasts["publish_time"].max().isoformat(),
            "duplicates_dropped": forecast_stats.duplicate_rows,
            "nan_dropped": forecast_stats.nan_rows,
            "resolution_minutes": 60,
            "horizon_h": {
                "min": float(np.nanmin(horizons)),
                "p50": float(np.nanpercentile(horizons, 50, method="linear")),
                "max": float(np.nanmax(horizons)),
                "negative_rows": int((horizons < 0).sum()),
            },
            "generation_mw": {
                "min": float(forecasts["generation_mw"].min()),
                "max": float(forecasts["generation_mw"].max()),
                "mean": float(forecasts["generation_mw"].mean()),
            },
        },
        "decision_coverage": coverage,
        "warnings": warnings,
        "errors": [],
    }
    return report


def write_quality_report(path: Path, report: dict[str, object]) -> None:
    """Write the quality report as pretty, deterministic JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")

"""Snapshot loading, invariant checks and the hourly evaluation frame."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from app.domain.constants import HALF_HOURS_PER_FORECAST_HOUR
from app.domain.errors import DataIntegrityError

ACTUAL_COLUMNS = ("start_time", "generation_mw")
FORECAST_COLUMNS = ("start_time", "publish_time", "generation_mw")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_tz(frame: pd.DataFrame, column: str) -> None:
    if not isinstance(frame[column].dtype, pd.DatetimeTZDtype):
        raise DataIntegrityError(f"{column} must be timezone-aware")
    if str(frame[column].dt.tz) != "UTC":
        raise DataIntegrityError(f"{column} must be UTC")


def load_actuals(path: Path) -> pd.DataFrame:
    """Load and validate half-hourly FUELHH WIND outturn.

    Args:
        path: Gzipped CSV with ``start_time`` and ``generation_mw``.

    Returns:
        A sorted frame with UTC timestamps and float MW.

    Raises:
        DataIntegrityError: if required columns, timezone or uniqueness fail.
    """
    frame = pd.read_csv(path, compression="gzip")
    missing = [column for column in ACTUAL_COLUMNS if column not in frame.columns]
    if missing:
        raise DataIntegrityError(f"actuals snapshot is missing columns: {missing}")
    frame = frame.loc[:, list(ACTUAL_COLUMNS)].copy()
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["generation_mw"] = pd.to_numeric(frame["generation_mw"], errors="coerce").astype(
        "float64"
    )
    _require_tz(frame, "start_time")
    if bool(frame["start_time"].duplicated().any()):
        raise DataIntegrityError("actuals snapshot has duplicate start_time rows")
    if bool(frame["start_time"].isna().any()):
        raise DataIntegrityError("actuals snapshot has null start_time rows")
    return frame.sort_values("start_time").reset_index(drop=True)


def load_forecasts(path: Path) -> pd.DataFrame:
    """Load and validate hourly WINDFOR vintages.

    Args:
        path: Gzipped CSV with ``start_time``, ``publish_time`` and ``generation_mw``.

    Returns:
        A sorted frame with UTC timestamps and float MW.
    """
    frame = pd.read_csv(path, compression="gzip")
    missing = [column for column in FORECAST_COLUMNS if column not in frame.columns]
    if missing:
        raise DataIntegrityError(f"forecast snapshot is missing columns: {missing}")
    frame = frame.loc[:, list(FORECAST_COLUMNS)].copy()
    for column in ("start_time", "publish_time"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
        _require_tz(frame, column)
    frame["generation_mw"] = pd.to_numeric(frame["generation_mw"], errors="coerce").astype(
        "float64"
    )
    if bool(frame.duplicated(["start_time", "publish_time"]).any()):
        raise DataIntegrityError("forecast snapshot has duplicate (start_time, publish_time) rows")
    return frame.sort_values(["start_time", "publish_time"]).reset_index(drop=True)


def hourly_actuals_from_half_hourly(actuals: pd.DataFrame) -> pd.DataFrame:
    """Aggregate half-hourly outturn to the hourly WINDFOR comparison grid.

    Each hourly value is the mean of the two half-hour settlement periods. If either
    half-hour is missing, the hourly value is null and is excluded from metrics; no
    interpolation or forward fill is performed.

    Args:
        actuals: Columns ``start_time`` (UTC) and ``generation_mw`` (MW, half-hourly).

    Returns:
        Columns ``start_time`` (hour, UTC), ``actual_mw`` and ``half_hours``.
    """
    frame = actuals.copy()
    frame["start_time"] = frame["start_time"].dt.floor("1h")
    grouped = frame.groupby("start_time", sort=True).agg(
        total_mw=("generation_mw", "sum"),
        half_hours=("generation_mw", "count"),
    )
    grouped["actual_mw"] = grouped["total_mw"] / HALF_HOURS_PER_FORECAST_HOUR
    grouped.loc[grouped["half_hours"] != HALF_HOURS_PER_FORECAST_HOUR, "actual_mw"] = float("nan")
    return grouped.reset_index().loc[:, ["start_time", "actual_mw", "half_hours"]]


def load_manifest(path: Path) -> dict[str, object]:
    """Load the snapshot manifest as a dictionary."""
    if not path.exists():
        raise DataIntegrityError(f"manifest not found at {path}")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DataIntegrityError("manifest must be a JSON object")
    return payload

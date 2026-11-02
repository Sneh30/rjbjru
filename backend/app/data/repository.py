"""Read-only data repository protocol and snapshot implementation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Protocol, cast

import pandas as pd

from app.domain.constants import HALF_HOURS_PER_FORECAST_HOUR
from app.domain.errors import DataIntegrityError
from app.domain.timeutils import london_delivery_date

from .loader import (
    hourly_actuals_from_half_hourly,
    load_actuals,
    load_forecasts,
    load_manifest,
    sha256_file,
)


class Repository(Protocol):
    """Read-only access to the committed snapshot."""

    fingerprint: str
    manifest: Mapping[str, object]

    def actuals(self) -> pd.DataFrame:
        """Return half-hourly FUELHH WIND actuals."""

    def forecasts(self) -> pd.DataFrame:
        """Return all hourly WINDFOR vintages."""

    def hourly_actuals(self) -> pd.DataFrame:
        """Return hourly actuals aligned to WINDFOR targets."""

    def data_quality(self) -> Mapping[str, object]:
        """Return snapshot coverage and integrity statistics."""


def _expected_half_hours(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(first, last, freq="30min", tz="UTC")


class SnapshotRepository:
    """Load the processed CSV snapshot once and expose typed, validated frames."""

    def __init__(self, data_dir: Path) -> None:
        processed = data_dir / "processed"
        manifest = load_manifest(processed / "manifest.json")
        self.manifest = manifest
        self.fingerprint = str(manifest.get("fingerprint", ""))
        if not self.fingerprint:
            raise DataIntegrityError("manifest has no fingerprint")
        actuals_path = processed / "actuals.csv.gz"
        forecasts_path = processed / "forecasts.csv.gz"
        for path in (actuals_path, forecasts_path):
            if not path.exists():
                raise DataIntegrityError(f"snapshot file missing: {path}")
        self._verify_hashes(actuals_path, forecasts_path, manifest)
        self._actuals = load_actuals(actuals_path)
        self._forecasts = load_forecasts(forecasts_path)
        self._hourly = hourly_actuals_from_half_hourly(self._actuals)
        self._quality = self._build_quality()

    @staticmethod
    def _verify_hashes(
        actuals_path: Path,
        forecasts_path: Path,
        manifest: Mapping[str, object],
    ) -> None:
        processed = manifest.get("processed")
        if not isinstance(processed, dict):
            raise DataIntegrityError("manifest.processed is missing")
        expected_actuals = str(processed.get("actuals", {}).get("sha256", ""))
        expected_forecasts = str(processed.get("forecasts", {}).get("sha256", ""))
        if not expected_actuals or not expected_forecasts:
            raise DataIntegrityError("manifest.processed hashes are missing")
        if sha256_file(actuals_path) != expected_actuals:
            raise DataIntegrityError("actuals.csv.gz does not match the manifest hash")
        if sha256_file(forecasts_path) != expected_forecasts:
            raise DataIntegrityError("forecasts.csv.gz does not match the manifest hash")

    def actuals(self) -> pd.DataFrame:
        """Return half-hourly FUELHH WIND actuals."""
        return self._actuals

    def forecasts(self) -> pd.DataFrame:
        """Return all hourly WINDFOR vintages."""
        return self._forecasts

    def hourly_actuals(self) -> pd.DataFrame:
        """Return hourly actuals aligned to WINDFOR targets."""
        return self._hourly

    def data_quality(self) -> Mapping[str, object]:
        """Return snapshot coverage and integrity statistics."""
        return self._quality

    def _build_quality(self) -> Mapping[str, object]:
        actuals = self._actuals
        hourly = self._hourly
        first = actuals["start_time"].min()
        last = actuals["start_time"].max()
        expected = _expected_half_hours(first, last)
        missing = expected.difference(pd.DatetimeIndex(actuals["start_time"]))
        incomplete_hours = int((hourly["half_hours"] != HALF_HOURS_PER_FORECAST_HOUR).sum())
        publish = self._forecasts["publish_time"]
        vintages_per_day = (
            self._forecasts.assign(publish_date=publish.dt.date)
            .groupby("publish_date")["publish_time"]
            .nunique()
        )
        return {
            "actual_rows": int(len(actuals)),
            "actual_start": first,
            "actual_end": last,
            "actual_expected_rows": int(len(expected)),
            "actual_missing_rows": int(len(missing)),
            "actual_missing_periods": [stamp.isoformat() for stamp in missing[:48]],
            "hourly_rows": int(len(hourly)),
            "hourly_incomplete": incomplete_hours,
            "forecast_rows": int(len(self._forecasts)),
            "forecast_vintages": int(publish.nunique()),
            "forecast_first_publish": publish.min(),
            "forecast_last_publish": publish.max(),
            "vintages_per_publish_date": {
                str(day): int(count) for day, count in vintages_per_day.items()
            },
            "forecast_target_start": self._forecasts["start_time"].min(),
            "forecast_target_end": self._forecasts["start_time"].max(),
        }


class InMemoryRepository:
    """Small repository used by API tests and component fixtures."""

    def __init__(
        self,
        actuals: pd.DataFrame,
        forecasts: pd.DataFrame,
        *,
        fingerprint: str = "testfingerprint01",
        manifest: Mapping[str, object] | None = None,
    ) -> None:
        self._actuals = actuals.sort_values("start_time").reset_index(drop=True)
        self._forecasts = forecasts.sort_values(["start_time", "publish_time"]).reset_index(
            drop=True
        )
        self._hourly = hourly_actuals_from_half_hourly(self._actuals)
        self.fingerprint = fingerprint
        self.manifest = manifest or {
            "fingerprint": fingerprint,
            "generated_at": "2026-01-01T00:00:00Z",
            "source": {"datasets": ["FUELHH", "WINDFOR"]},
        }
        self._quality = {
            "actual_rows": int(len(self._actuals)),
            "actual_expected_rows": int(len(self._actuals)),
            "actual_missing_rows": 0,
            "hourly_rows": int(len(self._hourly)),
            "hourly_incomplete": int(
                (self._hourly["half_hours"] != HALF_HOURS_PER_FORECAST_HOUR).sum()
            ),
            "forecast_rows": int(len(self._forecasts)),
            "forecast_vintages": int(self._forecasts["publish_time"].nunique()),
        }

    def actuals(self) -> pd.DataFrame:
        """Return half-hourly actuals."""
        return self._actuals

    def forecasts(self) -> pd.DataFrame:
        """Return all forecast vintages."""
        return self._forecasts

    def hourly_actuals(self) -> pd.DataFrame:
        """Return hourly actuals."""
        return self._hourly

    def data_quality(self) -> Mapping[str, object]:
        """Return coverage statistics."""
        return self._quality


def delivery_dates_in_frame(hourly: pd.DataFrame) -> list[date]:
    """Return sorted London delivery dates present in an hourly frame."""
    dates = london_delivery_date(hourly["start_time"]).dt.date.unique().tolist()
    return sorted(cast(list[date], dates))

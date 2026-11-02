"""Application configuration.

All tunables are environment-overridable. Defaults are the committed, documented
configuration used by the demo and by the analysis scripts.
"""

from __future__ import annotations

import json
from datetime import date, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.domain.timeutils import parse_cutoff

DEFAULT_CUTOFF_GRID = (
    "06:00",
    "08:00",
    "09:00",
    "09:20",
    "09:50",
    "10:00",
    "12:00",
)
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://localhost:8080")
DEFAULT_HORIZON_BUCKETS = (0.0, 6.0, 12.0, 18.0, 24.0, 36.0, 48.0, 72.0)


def _split_csv(value: object) -> list[str]:
    """Split an env string on commas, or pass a JSON/list value through."""
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part) for part in value]
    raise ValueError("expected a comma-separated string or list")


class Settings(BaseSettings):
    """Runtime settings for the API, ingestion CLI and analysis scripts."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    timezone: str = "Europe/London"
    default_cutoff: time = time(9, 0)
    cutoff_grid: Annotated[list[time], NoDecode] = Field(
        default_factory=lambda: [parse_cutoff(value) for value in DEFAULT_CUTOFF_GRID]
    )
    scope_mode: Literal["decision_date", "delivery_date"] = "decision_date"
    scope_start: date = date(2026, 1, 1)
    scope_end: date = date(2026, 1, 31)
    ingest_forecast_publish_start: str = "2025-12-30T00:00:00Z"
    ingest_forecast_publish_end: str = "2026-02-02T00:00:00Z"
    ingest_actuals_start: str = "2026-01-01T00:00:00Z"
    ingest_actuals_end: str = "2026-02-02T00:00:00Z"
    mape_min_actual_mw: float = 500.0
    min_history_days: int = 7
    outcome_lag_days: int = 2
    horizon_buckets_h: Annotated[list[float], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_HORIZON_BUCKETS)
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_CORS_ORIGINS)
    )
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    log_level: str = "INFO"

    @field_validator("cutoff_grid", mode="before")
    @classmethod
    def _parse_cutoff_grid(cls, value: object) -> list[time]:
        if value == "":
            return [parse_cutoff(item) for item in DEFAULT_CUTOFF_GRID]
        if isinstance(value, str) and value.lstrip().startswith("["):
            value = json.loads(value)
        items = value if isinstance(value, list) else _split_csv(value)
        return [item if isinstance(item, time) else parse_cutoff(str(item)) for item in items]

    @field_validator("horizon_buckets_h", mode="before")
    @classmethod
    def _parse_horizon_buckets(cls, value: object) -> list[float]:
        if isinstance(value, list):
            return [float(item) for item in value]
        if isinstance(value, str):
            if value.lstrip().startswith("["):
                return [float(item) for item in json.loads(value)]
            return [float(item) for item in _split_csv(value)]
        raise ValueError("horizon_buckets_h must be a list or comma-separated string")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> list[str]:
        if isinstance(value, str) and value.lstrip().startswith("["):
            return [str(item) for item in json.loads(value)]
        return _split_csv(value)

    @field_validator("default_cutoff", mode="before")
    @classmethod
    def _parse_default_cutoff(cls, value: object) -> object:
        return parse_cutoff(value) if isinstance(value, str) else value

    @field_validator("cutoff_grid")
    @classmethod
    def _ensure_default_in_grid(cls, value: list[time], info: object) -> list[time]:
        default = getattr(info, "data", {}).get("default_cutoff")
        if default is not None and default not in value:
            return sorted([*value, default])
        return sorted(value)

    @property
    def processed_dir(self) -> Path:
        """Directory holding the committed snapshot."""
        return self.data_dir / "processed"

    @property
    def raw_dir(self) -> Path:
        """Directory holding cached raw responses."""
        return self.data_dir / "raw"

    def delivery_dates(self) -> list[date]:
        """Return in-scope delivery dates under the configured scope reading.

        ``decision_date`` (default): decisions 1-31 Jan 2026 deliver 2 Jan-1 Feb.
        ``delivery_date``: delivery days 1-31 Jan 2026.
        """
        if self.scope_mode == "decision_date":
            start = self.scope_start + timedelta(days=1)
            end = self.scope_end + timedelta(days=1)
        else:
            start = self.scope_start
            end = self.scope_end
        days: list[date] = []
        cursor = start
        while cursor <= end:
            days.append(cursor)
            cursor += timedelta(days=1)
        return days

    def decision_dates(self) -> list[date]:
        """Return in-scope decision dates (the day before each delivery date)."""
        return [day - timedelta(days=1) for day in self.delivery_dates()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide immutable settings."""
    return Settings()

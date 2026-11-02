"""Domain result types.

These are plain dataclasses so that the domain layer has no dependency on Pydantic
or the HTTP layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Cutoff:
    """A decision cutoff for one London delivery day."""

    delivery_date: date
    local_time: str
    instant_utc: datetime


@dataclass(frozen=True, slots=True)
class Metrics:
    """Forecast-error metrics for one row set.

    Units: MW for errors, percent for rates, dimensionless for correlation and skill.
    Sign convention: ``error = forecast - actual``; positive is over-forecast.
    """

    n: int
    n_missing_actual: int
    mean_actual_mw: float | None
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    nmae_pct: float | None
    wape_pct: float | None
    mape_pct: float | None
    mape_n: int
    p50_abs_mw: float | None
    p90_abs_mw: float | None
    p95_abs_mw: float | None
    p5_err_mw: float | None
    p50_err_mw: float | None
    p95_err_mw: float | None
    over_forecast_share: float | None
    shortfall_mean_mw: float | None
    shortfall_p90_mw: float | None
    shortfall_p95_mw: float | None
    shortfall_max_mw: float | None
    correlation: float | None


@dataclass(frozen=True, slots=True)
class BucketMetrics:
    """Metrics for a labelled subset of rows (horizon, hour, level or day)."""

    label: str
    from_value: float
    to_value: float
    metrics: Metrics


@dataclass(frozen=True, slots=True)
class BaselineSummary:
    """Persistence baseline evaluated on the same rows as the forecast."""

    name: str
    mae_mw: float | None
    forecast_mae_mw: float | None
    skill: float | None
    n: int


@dataclass(frozen=True, slots=True)
class BufferPoint:
    """An empirical signed-error quantile in MW."""

    level: float
    buffer_mw: float


@dataclass(frozen=True, slots=True)
class BacktestDay:
    """One walk-forward back-test day."""

    delivery_date: date
    buffer_mw: float
    coverage: float
    n: int
    breaches: int


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Walk-forward risk-buffer result."""

    level: float
    outcome_lag_days: int
    min_history_days: int
    evaluated_days: int
    skipped_days: tuple[date, ...]
    coverage: float | None
    target: float
    mean_buffer_mw: float | None
    days_with_breach_share: float | None
    daily: tuple[BacktestDay, ...]

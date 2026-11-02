"""Empirical risk buffers and a leakage-safe walk-forward back-test.

The buffer at level p is the p-th quantile of signed error (forecast - actual),
so the over-forecast margin is exceeded only about (1 - p) of the time. The
risk-adjusted forecast is ``max(0, forecast - buffer)``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

from .models import BacktestDay, BacktestResult, BufferPoint
from .timeutils import london_hour


def _quantile(errors: npt.NDArray[np.float64], level: float) -> float:
    """Return a linear-interpolated empirical quantile."""
    return float(np.percentile(errors, level * 100.0, method="linear"))


def buffer_overall(joined: pd.DataFrame, levels: tuple[float, ...]) -> list[BufferPoint]:
    """Return empirical signed-error quantiles overall.

    Args:
        joined: Rows with ``error_mw`` (MW).
        levels: Probabilities in (0, 1), e.g. ``(0.5, 0.75, 0.9, 0.95)``.

    Returns:
        One buffer point per requested level, in the order supplied.
    """
    errors = joined["error_mw"].dropna().to_numpy(dtype=float)
    if len(errors) == 0:
        return []
    return [BufferPoint(level=level, buffer_mw=_quantile(errors, level)) for level in levels]


def buffer_by_hour(
    joined: pd.DataFrame,
    levels: tuple[float, ...],
) -> list[dict[str, object]]:
    """Return empirical signed-error quantiles for each London hour.

    Args:
        joined: Rows with ``start_time`` and ``error_mw``.
        levels: Probabilities in (0, 1).

    Returns:
        Twenty-four dictionaries with ``hour`` and ``buffers`` (MW), including hours
        with no errors (empty buffer list).
    """
    hours = london_hour(joined["start_time"])
    result: list[dict[str, object]] = []
    for hour in range(24):
        subset = joined.loc[(hours == hour) & joined["error_mw"].notna()]
        result.append(
            {
                "hour": hour,
                "buffers": buffer_overall(subset, levels),
            }
        )
    return result


def risk_adjusted(forecast_mw: pd.Series[Any], buffer_mw: float) -> pd.Series[Any]:
    """Return ``max(0, forecast - buffer)`` in MW."""
    return (forecast_mw - buffer_mw).clip(lower=0.0)


def walk_forward_backtest(
    joined: pd.DataFrame,
    *,
    level: float,
    min_history_days: int = 7,
    outcome_lag_days: int = 2,
) -> BacktestResult:
    """Back-test a buffer using only outcomes observable before each delivery day.

    For delivery day ``d``, the buffer is estimated from delivery days on or before
    ``d - outcome_lag_days``. The two-day lag ensures the previous day's actuals are
    known at 09:00 on ``d - 1``. Days with fewer than ``min_history_days`` usable
    history days are skipped and reported.

    Args:
        joined: Decision-time rows with ``delivery_date``, ``forecast_mw``,
            ``actual_mw`` and ``error_mw``.
        level: Buffer probability in (0, 1).
        min_history_days: Minimum number of prior delivery days required.
        outcome_lag_days: Outcome publication lag in days.

    Returns:
        A :class:`BacktestResult` with pooled coverage, mean buffer and daily detail.
    """
    valid = joined.loc[joined["error_mw"].notna() & joined["actual_mw"].notna()].copy()
    days = sorted(valid["delivery_date"].dropna().unique())
    evaluated: list[BacktestDay] = []
    skipped: list[date] = []
    for day in days:
        history_cutoff = day - timedelta(days=outcome_lag_days)
        history = valid.loc[valid["delivery_date"] <= history_cutoff]
        history_days = history["delivery_date"].unique()
        if len(history_days) < min_history_days:
            skipped.append(day)
            continue
        buffer = _quantile(history["error_mw"].to_numpy(dtype=float), level)
        today = valid.loc[valid["delivery_date"] == day]
        adjusted = risk_adjusted(today["forecast_mw"], buffer)
        covered = today["actual_mw"].to_numpy(dtype=float) >= adjusted.to_numpy(dtype=float)
        evaluated.append(
            BacktestDay(
                delivery_date=day,
                buffer_mw=buffer,
                coverage=float(np.mean(covered)),
                n=int(len(today)),
                breaches=int(np.count_nonzero(~covered)),
            )
        )

    if not evaluated:
        return BacktestResult(
            level=level,
            outcome_lag_days=outcome_lag_days,
            min_history_days=min_history_days,
            evaluated_days=0,
            skipped_days=tuple(skipped),
            coverage=None,
            target=level,
            mean_buffer_mw=None,
            days_with_breach_share=None,
            daily=(),
        )

    daily = tuple(evaluated)
    total_n = sum(day.n for day in daily)
    total_covered = sum(day.coverage * day.n for day in daily)
    coverage = total_covered / total_n if total_n else None
    mean_buffer = float(np.mean([day.buffer_mw for day in daily]))
    breach_share = float(np.mean([day.breaches > 0 for day in daily]))
    return BacktestResult(
        level=level,
        outcome_lag_days=outcome_lag_days,
        min_history_days=min_history_days,
        evaluated_days=len(daily),
        skipped_days=tuple(skipped),
        coverage=coverage,
        target=level,
        mean_buffer_mw=mean_buffer,
        days_with_breach_share=breach_share,
        daily=daily,
    )

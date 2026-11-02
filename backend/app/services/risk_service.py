"""Risk buffer and leakage-safe walk-forward back-test services."""

from __future__ import annotations

from datetime import date, time
from typing import cast

from app.domain.models import BufferPoint
from app.domain.risk import buffer_by_hour, buffer_overall, walk_forward_backtest

from .analysis_service import AnalysisService
from .formatting import mw, pct


def buffer(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
    levels: tuple[float, ...],
) -> dict[str, object]:
    """Return in-sample empirical signed-error buffers overall and by London hour."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    overall = buffer_overall(joined, levels)
    by_hour_rows = buffer_by_hour(joined, levels)
    return {
        "basis": "in_sample",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "overall": [{"level": point.level, "buffer_mw": mw(point.buffer_mw)} for point in overall],
        "by_hour": [
            {
                "hour": cast(int, row["hour"]),
                "buffers": [
                    {"level": point.level, "buffer_mw": mw(point.buffer_mw)}
                    for point in cast(list[BufferPoint], row["buffers"])
                ],
            }
            for row in by_hour_rows
        ],
        "n": int(joined["error_mw"].notna().sum()),
        "caveat": (
            "In-sample buffers use outcomes from the same window. Use the walk-forward "
            "back-test to judge calibration; periods within a day are autocorrelated, so "
            "tail estimates rest on roughly the number of delivery days, not periods."
        ),
    }


def backtest(
    service: AnalysisService,
    start: date,
    end: date,
    cutoff: time,
    *,
    level: float,
    min_history_days: int,
) -> dict[str, object]:
    """Return a walk-forward coverage test for one buffer level."""
    start, end = service.ensure_window(start, end)
    joined = service.window(cutoff, start, end)
    result = walk_forward_backtest(
        joined,
        level=level,
        min_history_days=min_history_days,
        outcome_lag_days=service.settings.outcome_lag_days,
    )
    return {
        "basis": "walk_forward",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "level": result.level,
        "outcome_lag_days": result.outcome_lag_days,
        "min_history_days": result.min_history_days,
        "evaluated_days": result.evaluated_days,
        "skipped_days": [day.isoformat() for day in result.skipped_days],
        "coverage": pct(result.coverage),
        "target": result.target,
        "mean_buffer_mw": mw(result.mean_buffer_mw),
        "days_with_breach_share": pct(result.days_with_breach_share),
        "daily": [
            {
                "delivery_date": day.delivery_date.isoformat(),
                "buffer_mw": mw(day.buffer_mw),
                "coverage": pct(day.coverage),
                "n": day.n,
                "breaches": day.breaches,
            }
            for day in result.daily
        ],
        "caveat": (
            "Each day's buffer uses only delivery days at least two days earlier, so "
            "outcomes that were not published by the cutoff cannot leak into it. "
            "Coverage is pooled over evaluated periods; interpret it with the number "
            "of delivery days, not just period count."
        ),
    }

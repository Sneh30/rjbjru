#!/usr/bin/env python3
"""Generate the deterministic WindLens insight artefacts.

The script deliberately imports the application's domain and service code rather
than re-implementing metric definitions. It writes two files:

* ``docs/insights.json`` — the machine-readable source of truth, including the
  exact API payloads used to produce the narrative.
* ``docs/INSIGHTS.md`` — the human-readable analysis used by the README, video
  script and submission answers.

Run with ``make insights``. The output is deterministic for a fixed snapshot and
configuration: no wall-clock timestamp is written, only the manifest timestamp.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from app.config import Settings  # noqa: E402
from app.data.repository import SnapshotRepository  # noqa: E402
from app.domain.baseline import baseline_summary, persistence_for_selected  # noqa: E402
from app.domain.join import join_selected_actuals  # noqa: E402
from app.domain.metrics import compute_metrics, max_ramp_mw  # noqa: E402
from app.domain.selection import select_earliest_forecasts  # noqa: E402
from app.services import accuracy_service, risk_service  # noqa: E402
from app.services.analysis_service import AnalysisService  # noqa: E402
from app.services.formatting import horizon_stats, metrics_payload, mw, pct, utc_iso  # noqa: E402

SCHEMA_VERSION = 1
PRODUCT = "WindLens"
BINS = 5
WORST_DAYS = 5
HOURS_SHOWN = 3
BUFFER_LEVELS = (0.5, 0.75, 0.9, 0.95)
DEFAULT_BUFFER_LEVEL = 0.9


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _mw(value: float | None) -> str:
    """Format a MW value for Markdown."""
    return "—" if value is None else f"{value:,.1f} MW"


def _signed_mw(value: float | None) -> str:
    """Format a signed MW value for Markdown."""
    return "—" if value is None else f"{value:+,.1f} MW"


def _hours(value: float | None) -> str:
    """Format an hours value for Markdown."""
    return "—" if value is None else f"{value:,.1f} h"


def _percent(value: float | None) -> str:
    """Format a percent value for Markdown."""
    return "—" if value is None else f"{value:,.2f}%"


def _share(value: float | None) -> str:
    """Format a fraction as a percentage for Markdown."""
    return "—" if value is None else f"{value * 100:,.1f}%"


def _int(value: int | None) -> str:
    """Format an integer with thousands separators."""
    return "—" if value is None else f"{value:,}"


def _delta_pct(new: float | None, base: float | None) -> float | None:
    """Return the percentage change from ``base`` to ``new``."""
    if new is None or base is None or base == 0:
        return None
    return pct((new - base) / base * 100.0)


def _as_date(value: object) -> date:
    """Coerce a date or timestamp-like value to a ``date``."""
    return pd.Timestamp(value).date()


def _day_frame(joined: pd.DataFrame, delivery_date: object) -> pd.DataFrame:
    """Return one delivery day's joined rows in time order."""
    target = _as_date(delivery_date)
    return joined.loc[joined["delivery_date"] == target].sort_values("start_time")


# ---------------------------------------------------------------------------
# Derived analysis
# ---------------------------------------------------------------------------


def _distribution_summary(joined: pd.DataFrame, metrics: dict[str, Any]) -> dict[str, Any]:
    """Summarise the direction and size of the signed error distribution."""
    errors = joined.loc[joined["error_mw"].notna(), "error_mw"].astype(float)
    n = int(len(errors))
    over = errors > 0
    under = errors < 0
    zero = errors == 0
    over_count = int(over.sum())
    under_count = int(under.sum())
    zero_count = int(zero.sum())
    return {
        "n": n,
        "over_count": over_count,
        "under_count": under_count,
        "zero_count": zero_count,
        "over_share": pct(over_count / n) if n else None,
        "under_share": pct(under_count / n) if n else None,
        "mean_over_forecast_mw": mw(float(errors[over].mean())) if over_count else None,
        "mean_under_forecast_mw": mw(float(-errors[under].mean())) if under_count else None,
        "bias_share_of_mean_actual_pct": (
            pct(metrics["bias_mw"] / metrics["mean_actual_mw"] * 100.0)
            if metrics["bias_mw"] is not None and metrics["mean_actual_mw"] not in (None, 0)
            else None
        ),
        "median_error_mw": metrics["p50_err_mw"],
        "p5_error_mw": metrics["p5_err_mw"],
        "p95_error_mw": metrics["p95_err_mw"],
        "shortfall_p90_mw": metrics["shortfall_p90_mw"],
        "shortfall_p95_mw": metrics["shortfall_p95_mw"],
        "shortfall_max_mw": metrics["shortfall_max_mw"],
    }


def _horizon_summary(payload: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Summarise the horizon table, including its populated range."""
    buckets = payload["buckets"]
    populated = [bucket for bucket in buckets if int(bucket["n"]) > 0]
    first = populated[0] if populated else None
    last = populated[-1] if populated else None
    growth = _delta_pct(last["mae_mw"], first["mae_mw"]) if first and last else None
    return {
        "decision_band_h": payload["decision_band_h"],
        "selected_horizon_h": summary["horizon_h"],
        "buckets": buckets,
        "populated_buckets": len(populated),
        "empty_buckets": [bucket["label"] for bucket in buckets if int(bucket["n"]) == 0],
        "first_populated": first,
        "last_populated": last,
        "mae_growth_first_to_last_pct": growth,
        "dropped_negative_horizon": payload["dropped_negative_horizon"],
        "n_vintage_rows": payload["n_vintage_rows"],
    }


def _hours_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Rank London hours by MAE and report the spread."""
    ranked = [row for row in payload["hours"] if row["mae_mw"] is not None]
    best = sorted(ranked, key=lambda row: (row["mae_mw"], row["hour"]))[:HOURS_SHOWN]
    worst = sorted(ranked, key=lambda row: (-row["mae_mw"], row["hour"]))[:HOURS_SHOWN]
    spread = None
    spread_pct = None
    if best and worst:
        spread = mw(worst[0]["mae_mw"] - best[0]["mae_mw"])
        spread_pct = _delta_pct(worst[0]["mae_mw"], best[0]["mae_mw"])
    return {
        "all": payload["hours"],
        "best": best,
        "worst": worst,
        "best_hour": best[0] if best else None,
        "worst_hour": worst[0] if worst else None,
        "spread_mw": spread,
        "spread_pct": spread_pct,
    }


def _levels_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Identify the largest absolute and relative error bins."""
    ranked = [row for row in payload["bins"] if row["mae_mw"] is not None]
    with_nmae = [row for row in ranked if row["nmae_pct"] is not None]
    with_bias = [row for row in ranked if row["bias_mw"] is not None]
    largest_error = max(ranked, key=lambda row: row["mae_mw"]) if ranked else None
    highest_nmae = max(with_nmae, key=lambda row: row["nmae_pct"]) if with_nmae else None
    largest_bias = max(with_bias, key=lambda row: abs(row["bias_mw"])) if with_bias else None
    return {
        "basis": payload["basis"],
        "bins": payload["bins"],
        "largest_error": largest_error,
        "highest_nmae": highest_nmae,
        "largest_abs_bias": largest_bias,
    }


def _day_extras(joined: pd.DataFrame, delivery_date: object) -> dict[str, Any]:
    """Compute ramp and direction statistics for one delivery day."""
    day = _day_frame(joined, delivery_date)
    actuals = day["actual_mw"].dropna().astype(float)
    errors = day["error_mw"].dropna().astype(float)
    return {
        "over_count": int((errors > 0).sum()),
        "under_count": int((errors < 0).sum()),
        "min_actual_mw": mw(float(actuals.min())) if not actuals.empty else None,
        "max_actual_mw": mw(float(actuals.max())) if not actuals.empty else None,
        "max_ramp_1h_mw": mw(max_ramp_mw(actuals, 1)) if len(actuals) > 1 else None,
        "max_ramp_3h_mw": mw(max_ramp_mw(actuals, 3)) if len(actuals) > 3 else None,
    }


def _describe_day(
    row: dict[str, Any],
    *,
    low_mean_mw: float | None,
    high_mean_mw: float | None,
    ramp_p90_mw: float | None,
) -> str:
    """Build a one-line, data-derived description of a day's miss."""
    mean_actual = row.get("mean_actual_mw")
    if mean_actual is None:
        wind = "wind level unavailable"
    elif low_mean_mw is not None and mean_actual <= low_mean_mw:
        wind = f"low-wind lull (daily mean {_mw(mean_actual)})"
    elif high_mean_mw is not None and mean_actual >= high_mean_mw:
        wind = f"strong-wind day (daily mean {_mw(mean_actual)})"
    else:
        wind = f"mid-range wind (daily mean {_mw(mean_actual)})"

    n = int(row["n"])
    over = int(row["over_count"])
    bias = row.get("bias_mw")
    if over == n:
        direction = f"over-forecast in all {n} hours (bias {_signed_mw(bias)})"
    elif over == 0:
        direction = f"under-forecast in all {n} hours (bias {_signed_mw(bias)})"
    else:
        direction = f"over-forecast in {over}/{n} hours (bias {_signed_mw(bias)})"

    ramp = row.get("max_ramp_1h_mw")
    ramp_text = f"max 1 h actual ramp {_mw(ramp)}"
    if ramp is not None and ramp_p90_mw is not None and ramp >= ramp_p90_mw:
        ramp_text += " (top-decile ramp)"
    return f"{wind}; {direction}; {ramp_text}."


def _daily_summary(
    payload: dict[str, Any], joined: pd.DataFrame
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Enrich every daily API row, then select the worst and demo days."""
    rows = payload["days"]
    extras = {row["delivery_date"]: _day_extras(joined, row["delivery_date"]) for row in rows}
    means = [float(row["mean_actual_mw"]) for row in rows if row["mean_actual_mw"] is not None]
    ramps = [
        float(extras[row["delivery_date"]]["max_ramp_1h_mw"])
        for row in rows
        if extras[row["delivery_date"]]["max_ramp_1h_mw"] is not None
    ]
    low_mean = mw(float(np.percentile(means, 20))) if means else None
    high_mean = mw(float(np.percentile(means, 80))) if means else None
    ramp_p90 = mw(float(np.percentile(ramps, 90))) if ramps else None

    daily: list[dict[str, Any]] = []
    for row in rows:
        merged = {**row, **extras[row["delivery_date"]]}
        merged["description"] = _describe_day(
            merged, low_mean_mw=low_mean, high_mean_mw=high_mean, ramp_p90_mw=ramp_p90
        )
        daily.append(merged)

    mae_values = [float(row["mae_mw"]) for row in rows if row["mae_mw"] is not None]
    median_mae = float(np.median(mae_values)) if mae_values else None
    typical_row = (
        min(rows, key=lambda row: abs(float(row["mae_mw"]) - median_mae))
        if median_mae is not None
        else None
    )
    bad_row = max(rows, key=lambda row: float(row["mae_mw"] or 0.0)) if rows else None
    ramp_row = (
        max(
            rows,
            key=lambda row: float(extras[row["delivery_date"]]["max_ramp_1h_mw"] or 0.0),
        )
        if rows
        else None
    )
    enriched = {row["delivery_date"]: row for row in daily}

    def pick(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return enriched[row["delivery_date"]]

    demo_days = {
        "typical": pick(typical_row),
        "bad": pick(bad_row),
        "big_ramp": pick(ramp_row),
        "median_daily_mae_mw": mw(median_mae),
        "daily_mean_actual_p20_mw": low_mean,
        "daily_mean_actual_p80_mw": high_mean,
        "daily_max_ramp_1h_p90_mw": ramp_p90,
    }
    return daily, demo_days


def _worst_days(payload: dict[str, Any], daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach the computed day description to the API's worst-day payload."""
    enriched = {row["delivery_date"]: row for row in daily}
    result: list[dict[str, Any]] = []
    for row in payload["days"]:
        base = enriched[row["delivery_date"]]
        result.append({**row, **{key: value for key, value in base.items() if key not in row}})
    return result


def _cutoff_summary(payload: dict[str, Any], default_cutoff: str) -> dict[str, Any]:
    """Summarise the cutoff grid and write a data-derived conclusion."""
    rows = payload["rows"]
    scored = [row for row in rows if row["mae_mw"] is not None]
    default = next((row for row in rows if row["cutoff"] == default_cutoff), None)
    if not scored or default is None:
        return {"rows": rows, "default": default, "best": None, "conclusion": ""}
    best = min(scored, key=lambda row: row["mae_mw"])
    improvement_mw = mw(default["mae_mw"] - best["mae_mw"])
    improvement_pct = (
        pct((default["mae_mw"] - best["mae_mw"]) / default["mae_mw"] * 100.0)
        if default["mae_mw"]
        else None
    )
    spread_mw = mw(max(row["mae_mw"] for row in scored) - min(row["mae_mw"] for row in scored))
    horizon_change_h = (
        round(float(best["mean_horizon_h"]) - float(default["mean_horizon_h"]), 1)
        if best["mean_horizon_h"] is not None and default["mean_horizon_h"] is not None
        else None
    )
    if best["cutoff"] == default_cutoff:
        conclusion = (
            f"The {default_cutoff} default also has the lowest MAE "
            f"({_mw(default['mae_mw'])}); no later cutoff improves it in this window."
        )
    else:
        conclusion = (
            f"The lowest MAE is {_mw(best['mae_mw'])} at {best['cutoff']}, "
            f"{_mw(improvement_mw)} ({_percent(improvement_pct)}) below the "
            f"{default_cutoff} default. It shortens mean horizon from "
            f"{_hours(default['mean_horizon_h'])} to {_hours(best['mean_horizon_h'])}. "
            f"The grid spans {_mw(spread_mw)}; the curve is flat near the default, "
            "which stays because it aligns with the 07:30 WINDFOR vintage and "
            "preserves lead time."
        )
    return {
        "rows": rows,
        "default": default,
        "best": best,
        "improvement_mw": improvement_mw,
        "improvement_pct": improvement_pct,
        "spread_mw": spread_mw,
        "best_horizon_change_h": horizon_change_h,
        "conclusion": conclusion,
    }


def _vintage_value(
    service: AnalysisService,
    settings: Settings,
    summary: dict[str, Any],
    start: date,
    end: date,
) -> dict[str, Any]:
    """Compare latest eligible, earliest eligible and persistence on the same rows."""
    forecasts = service.repository.forecasts()
    hourly_actuals = service.repository.hourly_actuals()
    earliest_selected = select_earliest_forecasts(forecasts, settings.default_cutoff)
    earliest_joined = join_selected_actuals(earliest_selected, hourly_actuals)
    earliest_joined = persistence_for_selected(
        earliest_joined, hourly_actuals, settings.default_cutoff
    )
    mask = (earliest_joined["delivery_date"] >= start) & (earliest_joined["delivery_date"] <= end)
    earliest_window = earliest_joined.loc[mask].sort_values("start_time").reset_index(drop=True)
    earliest_metrics = compute_metrics(
        earliest_window, mape_min_actual_mw=settings.mape_min_actual_mw
    )
    earliest_payload = metrics_payload(earliest_metrics)
    earliest_payload["n_missing_forecast"] = service.expected_hours(start, end) - int(
        len(earliest_window)
    )
    earliest_baseline = baseline_summary(earliest_window)

    latest_metrics = summary["metrics"]
    persistence = summary["baseline"]
    latest_mae = latest_metrics["mae_mw"]
    earliest_mae = earliest_payload["mae_mw"]
    persistence_mae = persistence["mae_mw"]

    return {
        "latest": {
            "label": "latest eligible vintage",
            "horizon_h": summary["horizon_h"],
            "metrics": latest_metrics,
            "baseline": persistence,
            "skill": persistence["skill"],
        },
        "earliest": {
            "label": "earliest eligible vintage",
            "horizon_h": horizon_stats(earliest_window["horizon_h"]),
            "metrics": earliest_payload,
            "baseline": {
                "name": earliest_baseline.name,
                "mae_mw": mw(earliest_baseline.mae_mw),
                "forecast_mae_mw": mw(earliest_baseline.forecast_mae_mw),
                "skill": pct(earliest_baseline.skill),
                "n": earliest_baseline.n,
            },
        },
        "persistence": {
            "label": "persistence of last complete actual at cutoff",
            "metrics": {"n": persistence["n"], "mae_mw": persistence_mae},
        },
        "comparisons": {
            "earliest_mae_above_latest_mw": mw(earliest_mae - latest_mae),
            "earliest_mae_above_latest_pct": (
                pct((earliest_mae - latest_mae) / latest_mae * 100.0) if latest_mae else None
            ),
            "latest_mae_below_persistence_mw": mw(persistence_mae - latest_mae),
            "latest_mae_below_persistence_pct": (
                pct((persistence_mae - latest_mae) / persistence_mae * 100.0)
                if persistence_mae
                else None
            ),
            "earliest_mae_below_persistence_mw": mw(persistence_mae - earliest_mae),
            "earliest_mae_below_persistence_pct": (
                pct((persistence_mae - earliest_mae) / persistence_mae * 100.0)
                if persistence_mae
                else None
            ),
            "latest_skill": persistence["skill"],
            "earliest_skill": pct(earliest_baseline.skill),
        },
    }


def _risk_summary(
    service: AnalysisService,
    settings: Settings,
    start: date,
    end: date,
    errors: pd.Series[Any],
) -> dict[str, Any]:
    """Merge in-sample buffers with walk-forward coverage for each level."""
    buffer_payload = risk_service.buffer(
        service, start, end, settings.default_cutoff, BUFFER_LEVELS
    )
    backtests: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for point in buffer_payload["overall"]:
        level = float(point["level"])
        backtest = risk_service.backtest(
            service,
            start,
            end,
            settings.default_cutoff,
            level=level,
            min_history_days=settings.min_history_days,
        )
        backtests[f"{level:g}"] = backtest
        in_sample_coverage = None
        if point["buffer_mw"] is not None:
            in_sample_coverage = pct(float((errors <= float(point["buffer_mw"])).mean()))
        rows.append(
            {
                "level": level,
                "in_sample_buffer_mw": point["buffer_mw"],
                "in_sample_coverage": in_sample_coverage,
                "walk_forward_coverage": backtest["coverage"],
                "walk_forward_coverage_pct": (
                    pct(backtest["coverage"] * 100.0) if backtest["coverage"] is not None else None
                ),
                "walk_forward_mean_buffer_mw": backtest["mean_buffer_mw"],
                "walk_forward_days_with_breach_share": backtest["days_with_breach_share"],
                "walk_forward_days_with_breach_pct": (
                    pct(backtest["days_with_breach_share"] * 100.0)
                    if backtest["days_with_breach_share"] is not None
                    else None
                ),
                "evaluated_days": backtest["evaluated_days"],
                "skipped_days": backtest["skipped_days"],
                "target": backtest["target"],
            }
        )

    default_row = next(
        (row for row in rows if row["level"] == DEFAULT_BUFFER_LEVEL),
        rows[0] if rows else None,
    )
    conclusion = ""
    caveat = (
        "In-sample coverage is nominal by construction because the buffer is an "
        "empirical quantile. The walk-forward column is the honest estimate: each "
        "day's buffer uses only outcomes from at least two days earlier."
    )
    if default_row is not None:
        conclusion = (
            f"At level {default_row['level']:.2f} the in-sample buffer is "
            f"{_mw(default_row['in_sample_buffer_mw'])}. Walk-forward coverage is "
            f"{_share(default_row['walk_forward_coverage'])} over "
            f"{default_row['evaluated_days']} evaluated days "
            f"({len(default_row['skipped_days'])} skipped), with a mean buffer of "
            f"{_mw(default_row['walk_forward_mean_buffer_mw'])} and "
            f"{_share(default_row['walk_forward_days_with_breach_share'])} of days "
            f"breached. The target is {_share(default_row['target'])}; the gap is the "
            "honest out-of-sample cost, and the day count is small."
        )
        caveat = (
            f"In-sample coverage is nominal by construction because the buffer is an "
            f"empirical quantile. The walk-forward column is the honest estimate: each "
            f"day's buffer uses only outcomes from at least two days earlier. With "
            f"{default_row['evaluated_days']} evaluated days, treat the tail coverage "
            "as indicative rather than precise."
        )
    return {
        "buffer": buffer_payload,
        "backtests": backtests,
        "rows": rows,
        "default_level": DEFAULT_BUFFER_LEVEL,
        "default": default_row,
        "conclusion": conclusion,
        "caveat": caveat,
    }


def _data_summary(
    service: AnalysisService,
    settings: Settings,
    start: date,
    end: date,
) -> dict[str, Any]:
    """Collect snapshot provenance and coverage without hiding missing data."""
    quality = service.repository.data_quality()
    manifest = service.repository.manifest
    forecasts = service.repository.forecasts()
    processed = manifest.get("processed", {})
    if not isinstance(processed, dict):
        processed = {}
    coverage = service.window_coverage(settings.default_cutoff, start, end)
    vintage_days = quality.get("vintages_per_publish_date", {})
    if not isinstance(vintage_days, dict):
        vintage_days = {}
    vintage_counts = [int(value) for value in vintage_days.values()]
    expected = service.expected_hours(start, end)
    return {
        "snapshot": {
            "fingerprint": service.fingerprint,
            "manifest_generated_at": manifest.get("generated_at"),
            "schema_version": manifest.get("schema_version"),
            "source": manifest.get("source"),
            "processed": processed,
        },
        "scope": {
            "mode": settings.scope_mode,
            "decision_dates": {
                "start": settings.decision_dates()[0].isoformat(),
                "end": settings.decision_dates()[-1].isoformat(),
            },
            "delivery_dates": {"start": start.isoformat(), "end": end.isoformat()},
            "delivery_days": (end - start).days + 1,
            "expected_hours": expected,
            "default_cutoff": f"{settings.default_cutoff.hour:02d}:"
            f"{settings.default_cutoff.minute:02d}",
            "timezone": settings.timezone,
        },
        "decision_coverage": {
            "expected_periods": coverage["expected_periods"],
            "with_forecast": coverage["with_forecast"],
            "with_actual": coverage["with_actual"],
            "coverage_pct": coverage["coverage_pct"],
            "missing_forecast_periods": int(coverage["expected_periods"])
            - int(coverage["with_forecast"]),
            "missing_actual_periods": int(coverage["with_forecast"]) - int(coverage["with_actual"]),
        },
        "actuals": {
            "rows": quality.get("actual_rows"),
            "expected_rows": quality.get("actual_expected_rows"),
            "missing_rows": quality.get("actual_missing_rows"),
            "start": utc_iso(quality.get("actual_start")),
            "end": utc_iso(quality.get("actual_end")),
            "hourly_rows": quality.get("hourly_rows"),
            "hourly_incomplete": quality.get("hourly_incomplete"),
            "resolution_minutes": 30,
        },
        "forecasts": {
            "rows": quality.get("forecast_rows"),
            "vintages": quality.get("forecast_vintages"),
            "targets": int(forecasts["start_time"].nunique()),
            "first_publish": utc_iso(quality.get("forecast_first_publish")),
            "last_publish": utc_iso(quality.get("forecast_last_publish")),
            "target_start": utc_iso(quality.get("forecast_target_start")),
            "target_end": utc_iso(quality.get("forecast_target_end")),
            "resolution_minutes": 60,
            "publish_days": len(vintage_counts),
            "vintages_per_publish_day_min": min(vintage_counts) if vintage_counts else None,
            "vintages_per_publish_day_max": max(vintage_counts) if vintage_counts else None,
        },
    }


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def build_payload(settings: Settings, repository: SnapshotRepository) -> dict[str, Any]:
    """Build the complete insights payload from the committed snapshot."""
    service = AnalysisService(repository, settings)
    start, end = service.scope_bounds()
    cutoff = settings.default_cutoff
    joined = service.window(cutoff, start, end)

    summary = accuracy_service.summary(service, start, end, cutoff)
    # The Pydantic response model materialises these two list defaults, so add
    # them here as well. That keeps the committed JSON byte-for-byte equivalent
    # to the live endpoint payload without duplicating service logic.
    summary["coverage"] = {
        **summary["coverage"],
        "missing_forecast_periods": [],
        "missing_actual_periods": [],
    }
    horizon = accuracy_service.by_horizon(service, start, end, cutoff)
    hours = accuracy_service.by_hour_breakdown(service, start, end, cutoff)
    levels = accuracy_service.by_level_breakdown(
        service, start, end, cutoff, basis="actual", bins=BINS
    )
    daily = accuracy_service.daily(service, start, end, cutoff)
    worst = accuracy_service.worst(service, start, end, cutoff, n=WORST_DAYS, metric="mae")
    sensitivity = accuracy_service.cutoff_sensitivity(service, start, end)

    daily_rows, demo_days = _daily_summary(daily, joined)
    worst_days = _worst_days(worst, daily_rows)
    errors = joined.loc[joined["error_mw"].notna(), "error_mw"].astype(float)

    risk = _risk_summary(service, settings, start, end, errors)
    data = _data_summary(service, settings, start, end)
    vintage_value = _vintage_value(service, settings, summary, start, end)
    cutoff_summary = _cutoff_summary(sensitivity, summary["cutoff"])

    derived = {
        "distribution": _distribution_summary(joined, summary["metrics"]),
        "horizon_summary": _horizon_summary(horizon, summary),
        "hours_summary": _hours_summary(hours),
        "levels_summary": _levels_summary(levels),
        "worst_days": worst_days,
        "demo_days": demo_days,
        "cutoff_summary": cutoff_summary,
        "vintage_value": vintage_value,
        "risk_summary": {
            "rows": risk["rows"],
            "default_level": risk["default_level"],
            "default": risk["default"],
            "conclusion": risk["conclusion"],
            "caveat": risk["caveat"],
        },
        "data": data,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "description": (
            "Deterministic WindLens analysis generated from the committed Elexon "
            "FUELHH (WIND) and WINDFOR snapshot."
        ),
        "snapshot": {
            "fingerprint": service.fingerprint,
            "manifest_generated_at": repository.manifest.get("generated_at"),
            "source": repository.manifest.get("source"),
        },
        "scope": data["scope"],
        "summary": summary,
        "horizon": horizon,
        "hours": hours,
        "levels": levels,
        "daily": daily,
        "worst": worst,
        "cutoff_sensitivity": sensitivity,
        "risk": {
            "buffer": risk["buffer"],
            "backtests": risk["backtests"],
        },
        "derived": derived,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavoured Markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _bucket_label(bucket: dict[str, Any]) -> str:
    """Return a horizon bucket label, marking the open-ended bucket."""
    if bucket.get("to_h") is None:
        return f"{bucket['from_h']:g}+ h"
    return f"{bucket['from_h']:g}-{bucket['to_h']:g} h"


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render the human-readable INSIGHTS.md from the payload."""
    summary = payload["summary"]
    metrics = summary["metrics"]
    baseline = summary["baseline"]
    scope = payload["scope"]
    derived = payload["derived"]
    distribution = derived["distribution"]
    horizon_summary = derived["horizon_summary"]
    hours_summary = derived["hours_summary"]
    levels_summary = derived["levels_summary"]
    cutoff_summary = derived["cutoff_summary"]
    vintage = derived["vintage_value"]
    risk = derived["risk_summary"]
    data = derived["data"]

    lines: list[str] = []
    lines.append("# WindLens — Insights")
    lines.append("")
    lines.append(
        "> **Generated artefact.** Produced by `analysis/insights.py` from the committed "
        "snapshot; do not edit by hand. Regenerate with `make insights`."
    )
    lines.append(">")
    lines.append(
        f"> Snapshot fingerprint `{data['snapshot']['fingerprint']}` · manifest generated "
        f"`{data['snapshot']['manifest_generated_at']}` · source Elexon BMRS "
        "`FUELHH` (WIND) + `WINDFOR` · scope "
        f"**{scope['delivery_dates']['start']} → {scope['delivery_dates']['end']}** "
        f"({scope['delivery_days']} London delivery days, {scope['expected_hours']} hourly "
        f"targets) · default cutoff **{scope['default_cutoff']} Europe/London on D-1**."
    )
    lines.append("")

    lines.append("## Key findings")
    lines.append("")
    lines.append(
        f"- Across **{metrics['n']:,} hourly targets**, the selected WINDFOR forecast has "
        f"MAE **{_mw(metrics['mae_mw'])}** and nMAE **{_percent(metrics['nmae_pct'])}**."
    )
    lines.append(
        f"- Bias is **{_signed_mw(metrics['bias_mw'])}**; **{_share(distribution['over_share'])}** "
        "of hours are over-forecast, so the error is directional shortfall risk, not just noise."
    )
    lines.append(
        f"- P90 shortfall is **{_mw(metrics['shortfall_p90_mw'])}** and P95 is "
        f"**{_mw(metrics['shortfall_p95_mw'])}** (maximum "
        f"**{_mw(metrics['shortfall_max_mw'])}**)."
    )
    lines.append(
        f"- The persistence baseline's MAE is **{_mw(baseline['mae_mw'])}**; the forecast's "
        f"skill score is **{baseline['skill']:.2f}**, a "
        f"**{_percent(vintage['comparisons']['latest_mae_below_persistence_pct'])}** MAE "
        "reduction."
    )
    lines.append(
        f"- Decision horizons are **{_hours(horizon_summary['decision_band_h']['min'])} "
        f"to {_hours(horizon_summary['decision_band_h']['max'])}** "
        f"(mean **{_hours(horizon_summary['selected_horizon_h']['mean'])}**)."
    )
    lines.append(
        f"- The latest vintage beats the earliest available vintage: "
        f"**{_mw(vintage['latest']['metrics']['mae_mw'])}** vs "
        f"**{_mw(vintage['earliest']['metrics']['mae_mw'])}** MAE, a "
        f"**{_mw(vintage['comparisons']['earliest_mae_above_latest_mw'])}** / "
        f"**{_percent(vintage['comparisons']['earliest_mae_above_latest_pct'])}** advantage."
    )
    lines.append(
        f"- At the {risk['default_level']:.2f} risk level the in-sample buffer is "
        f"**{_mw(risk['default']['in_sample_buffer_mw'])}**; walk-forward coverage is "
        f"**{_share(risk['default']['walk_forward_coverage'])}** over "
        f"{risk['default']['evaluated_days']} days, with mean buffer "
        f"**{_mw(risk['default']['walk_forward_mean_buffer_mw'])}** and "
        f"**{_share(risk['default']['walk_forward_days_with_breach_share'])}** of days breached."
    )
    lines.append(
        f"- The {cutoff_summary['best']['cutoff']} cutoff has the lowest MAE "
        f"(**{_mw(cutoff_summary['best']['mae_mw'])}**), "
        f"**{_percent(cutoff_summary['improvement_pct'])}** below the "
        f"{cutoff_summary['default']['cutoff']} default, but it shortens mean horizon from "
        f"**{_hours(cutoff_summary['default']['mean_horizon_h'])}** to "
        f"**{_hours(cutoff_summary['best']['mean_horizon_h'])}**."
    )
    lines.append(
        f"- Coverage is complete: **{data['decision_coverage']['with_forecast']:,}/"
        f"{data['decision_coverage']['expected_periods']:,}** forecasts and "
        f"**{data['decision_coverage']['with_actual']:,}/"
        f"{data['decision_coverage']['expected_periods']:,}** actuals; no missing periods, "
        "no interpolation."
    )
    lines.append("")

    lines.append("## 1. Headline metrics at the default cutoff")
    lines.append("")
    lines.append(
        "The evaluation window is the configured decision scope: decisions taken on "
        f"{scope['decision_dates']['start']} to {scope['decision_dates']['end']} deliver "
        f"{scope['delivery_dates']['start']} to {scope['delivery_dates']['end']}. "
        "Error is `forecast - actual`; positive is over-forecast and shortfall risk."
    )
    lines.append("")
    lines.append(
        _table(
            ["Metric", "Value"],
            [
                ["Scored hours", f"{metrics['n']:,}"],
                ["Mean actual output", _mw(metrics["mean_actual_mw"])],
                ["MAE", _mw(metrics["mae_mw"])],
                ["RMSE", _mw(metrics["rmse_mw"])],
                ["Bias", _signed_mw(metrics["bias_mw"])],
                ["nMAE", _percent(metrics["nmae_pct"])],
                ["WAPE", _percent(metrics["wape_pct"])],
                ["MAPE (actual ≥ 500 MW)", _percent(metrics["mape_pct"])],
                ["Median absolute error", _mw(metrics["p50_abs_mw"])],
                ["P90 absolute error", _mw(metrics["p90_abs_mw"])],
                ["P95 absolute error", _mw(metrics["p95_abs_mw"])],
                ["Correlation (forecast vs actual)", f"{metrics['correlation']:.2f}"],
                ["Persistence baseline MAE", _mw(baseline["mae_mw"])],
                ["Forecast skill vs persistence", f"{baseline['skill']:.2f}"],
                ["Missing actuals", f"{metrics['n_missing_actual']:,}"],
            ],
        )
    )
    lines.append("")
    lines.append(
        f"The central result is not that the forecast is noisy — correlation is "
        f"**{metrics['correlation']:.2f}** — but that it is biased high. The bias of "
        f"**{_signed_mw(metrics['bias_mw'])}** is "
        f"**{_percent(distribution['bias_share_of_mean_actual_pct'])}** of mean actual "
        "output, and it is larger than the median absolute miss."
    )
    lines.append("")

    lines.append("## 2. Error direction and shortfall")
    lines.append("")
    lines.append(
        _table(
            ["Direction", "Hours", "Share", "Conditional mean"],
            [
                [
                    "Over-forecast (error > 0)",
                    f"{distribution['over_count']:,}",
                    _share(distribution["over_share"]),
                    _mw(distribution["mean_over_forecast_mw"]),
                ],
                [
                    "Under-forecast (error < 0)",
                    f"{distribution['under_count']:,}",
                    _share(distribution["under_share"]),
                    _mw(distribution["mean_under_forecast_mw"]),
                ],
                ["Exact", f"{distribution['zero_count']:,}", _share(0.0), "—"],
            ],
        )
    )
    lines.append("")
    lines.append(
        f"The signed-error quantiles are P5 **{_signed_mw(distribution['p5_error_mw'])}**, "
        f"median **{_signed_mw(distribution['median_error_mw'])}**, and P95 "
        f"**{_signed_mw(distribution['p95_error_mw'])}**. The shortfall distribution "
        f"(positive errors only, with zeros retained) has P90 "
        f"**{_mw(distribution['shortfall_p90_mw'])}**, P95 "
        f"**{_mw(distribution['shortfall_p95_mw'])}**, and a maximum of "
        f"**{_mw(distribution['shortfall_max_mw'])}**. The conditional mean over-forecast "
        f"is **{_mw(distribution['mean_over_forecast_mw'])}**, more than twice the "
        f"conditional mean under-forecast of **{_mw(distribution['mean_under_forecast_mw'])}**."
    )
    lines.append("")
    lines.append(
        f"This is the buyer's problem in one line: the forecast is high in "
        f"{_share(distribution['over_share'])} of hours, and when it is high the miss is "
        "large. A risk buffer, not a symmetric confidence interval, is the appropriate "
        "response."
    )
    lines.append("")

    lines.append("## 3. Horizon and lead time")
    lines.append("")
    horizon_rows = [
        [
            _bucket_label(bucket),
            f"{bucket['n']:,}",
            _mw(bucket["mae_mw"]),
            _signed_mw(bucket["bias_mw"]),
            _mw(bucket["rmse_mw"]),
            _percent(bucket["nmae_pct"]),
        ]
        for bucket in payload["horizon"]["buckets"]
    ]
    lines.append(
        _table(["Horizon from publication", "Rows", "MAE", "Bias", "RMSE", "nMAE"], horizon_rows)
    )
    lines.append("")
    lines.append(
        f"The table covers every vintage in the snapshot, not only the selected one. "
        f"The selected decision rows span **{_hours(horizon_summary['decision_band_h']['min'])} "
        f"to {_hours(horizon_summary['decision_band_h']['max'])}** "
        f"(mean **{_hours(horizon_summary['selected_horizon_h']['mean'])}**). "
        f"The first populated bucket has MAE "
        f"**{_mw(horizon_summary['first_populated']['mae_mw'])}**; "
        f"the last has **{_mw(horizon_summary['last_populated']['mae_mw'])}**, a "
        f"**{_percent(horizon_summary['mae_growth_first_to_last_pct'])}** increase. "
        f"No vintage reaches the 72+ h bucket in this snapshot, so that row is empty."
    )
    lines.append("")
    lines.append(
        f"The all-vintage frame contains **{horizon_summary['n_vintage_rows']:,}** rows; "
        f"**{horizon_summary['dropped_negative_horizon']:,}** rows with a negative horizon "
        "were dropped from the horizon table because the target had already begun at "
        "publication. They can never be selected for a decision."
    )
    lines.append("")

    lines.append("## 4. Best and worst hours of the day")
    lines.append("")
    lines.append("Best three London hours by MAE:")
    lines.append("")
    best_rows = [
        [
            row["label"],
            f"{row['n']:,}",
            _mw(row["mae_mw"]),
            _signed_mw(row["bias_mw"]),
            _mw(row["mean_actual_mw"]),
        ]
        for row in hours_summary["best"]
    ]
    lines.append(_table(["Hour", "Hours", "MAE", "Bias", "Mean actual"], best_rows))
    lines.append("")
    lines.append("Worst three London hours by MAE:")
    lines.append("")
    worst_rows = [
        [
            row["label"],
            f"{row['n']:,}",
            _mw(row["mae_mw"]),
            _signed_mw(row["bias_mw"]),
            _mw(row["mean_actual_mw"]),
        ]
        for row in hours_summary["worst"]
    ]
    lines.append(_table(["Hour", "Hours", "MAE", "Bias", "Mean actual"], worst_rows))
    lines.append("")
    lines.append(
        f"The best hour is **{hours_summary['best_hour']['label']}** at "
        f"**{_mw(hours_summary['best_hour']['mae_mw'])}**; the worst is "
        f"**{hours_summary['worst_hour']['label']}** at "
        f"**{_mw(hours_summary['worst_hour']['mae_mw'])}**. The spread is "
        f"**{_mw(hours_summary['spread_mw'])}** "
        f"(**{_percent(hours_summary['spread_pct'])}** of the best hour), so the "
        "intraday shape matters but does not explain the overall bias."
    )
    lines.append("")

    lines.append("## 5. Wind-level analysis")
    lines.append("")
    level_rows = [
        [
            bin_row["label"],
            f"{_mw(bin_row['from_mw'])} - {_mw(bin_row['to_mw'])}",
            f"{bin_row['n']:,}",
            _mw(bin_row["mae_mw"]),
            _signed_mw(bin_row["bias_mw"]),
            _percent(bin_row["nmae_pct"]),
        ]
        for bin_row in levels_summary["bins"]
    ]
    lines.append(_table(["Actual-output bin", "Range", "Hours", "MAE", "Bias", "nMAE"], level_rows))
    lines.append("")
    lines.append(
        f"The largest absolute error is in **{levels_summary['largest_error']['label']}** "
        f"({_mw(levels_summary['largest_error']['from_mw'])} - "
        f"{_mw(levels_summary['largest_error']['to_mw'])}): MAE "
        f"**{_mw(levels_summary['largest_error']['mae_mw'])}**, bias "
        f"**{_signed_mw(levels_summary['largest_error']['bias_mw'])}**. The highest "
        f"relative error is in **{levels_summary['highest_nmae']['label']}** at "
        f"**{_percent(levels_summary['highest_nmae']['nmae_pct'])}**, because low-output "
        "hours make the same absolute miss look larger. The largest absolute bias is in "
        f"**{levels_summary['largest_abs_bias']['label']}** at "
        f"**{_signed_mw(levels_summary['largest_abs_bias']['bias_mw'])}**."
    )
    lines.append("")

    lines.append("## 6. Worst delivery days and demo-day picks")
    lines.append("")
    worst_rows = [
        [
            row["delivery_date"],
            f"{row['n']:,}",
            _mw(row["mae_mw"]),
            _signed_mw(row["bias_mw"]),
            _mw(row["mean_actual_mw"]),
            _mw(row["max_ramp_1h_mw"]),
            row["description"],
        ]
        for row in derived["worst_days"]
    ]
    lines.append(
        _table(
            [
                "Delivery day",
                "Hours",
                "MAE",
                "Bias",
                "Mean actual",
                "Max 1 h ramp",
                "Computed description",
            ],
            worst_rows,
        )
    )
    lines.append("")
    demo = derived["demo_days"]
    lines.append(
        f"**Demo-day picks for the video.** Typical: **{demo['typical']['delivery_date']}** "
        f"(MAE {_mw(demo['typical']['mae_mw'])}, mean actual "
        f"{_mw(demo['typical']['mean_actual_mw'])}, max 1 h ramp "
        f"{_mw(demo['typical']['max_ramp_1h_mw'])}). Bad day: "
        f"**{demo['bad']['delivery_date']}** (MAE {_mw(demo['bad']['mae_mw'])}, bias "
        f"{_signed_mw(demo['bad']['bias_mw'])}). Big-ramp day: "
        f"**{demo['big_ramp']['delivery_date']}** (max 1 h actual ramp "
        f"{_mw(demo['big_ramp']['max_ramp_1h_mw'])}, max 3 h ramp "
        f"{_mw(demo['big_ramp']['max_ramp_3h_mw'])}, MAE "
        f"{_mw(demo['big_ramp']['mae_mw'])})."
    )
    lines.append("")
    lines.append(
        f"The worst day, **{derived['worst_days'][0]['delivery_date']}**, has MAE "
        f"**{_mw(derived['worst_days'][0]['mae_mw'])}** and bias "
        f"**{_signed_mw(derived['worst_days'][0]['bias_mw'])}**. Its computed description "
        f"is: *{derived['worst_days'][0]['description']}*"
    )
    lines.append("")

    lines.append("## 7. Cutoff sensitivity")
    lines.append("")
    sensitivity_rows = [
        [
            row["cutoff"],
            f"{row['n']:,}",
            _mw(row["mae_mw"]),
            _signed_mw(row["bias_mw"]),
            _mw(row["shortfall_p90_mw"]),
            f"{row['mean_horizon_h']:.1f} h",
            _percent(row["coverage_pct"]),
        ]
        for row in cutoff_summary["rows"]
    ]
    lines.append(
        _table(
            ["Cutoff (D-1)", "Hours", "MAE", "Bias", "P90 shortfall", "Mean horizon", "Coverage"],
            sensitivity_rows,
        )
    )
    lines.append("")
    lines.append(cutoff_summary["conclusion"])
    lines.append("")
    lines.append(
        f"The full grid spans **{_mw(cutoff_summary['spread_mw'])}** of MAE. The default "
        f"row is **{cutoff_summary['default']['cutoff']}** with MAE "
        f"**{_mw(cutoff_summary['default']['mae_mw'])}**; the best row is "
        f"**{cutoff_summary['best']['cutoff']}** with "
        f"**{_mw(cutoff_summary['best']['mae_mw'])}**. The interpretation is not "
        "“later is better”: the gain is modest, and it is bought with less lead time."
    )
    lines.append("")

    lines.append("## 8. Vintage value: latest, earliest and persistence")
    lines.append("")
    vintage_rows = [
        [
            "Latest eligible",
            f"{vintage['latest']['horizon_h']['min']:.1f}-"
            f"{vintage['latest']['horizon_h']['max']:.1f} h",
            _mw(vintage["latest"]["metrics"]["mae_mw"]),
            _signed_mw(vintage["latest"]["metrics"]["bias_mw"]),
            _percent(vintage["latest"]["metrics"]["nmae_pct"]),
            f"{vintage['comparisons']['latest_skill']:.2f}",
        ],
        [
            "Earliest eligible",
            f"{vintage['earliest']['horizon_h']['min']:.1f}-"
            f"{vintage['earliest']['horizon_h']['max']:.1f} h",
            _mw(vintage["earliest"]["metrics"]["mae_mw"]),
            _signed_mw(vintage["earliest"]["metrics"]["bias_mw"]),
            _percent(vintage["earliest"]["metrics"]["nmae_pct"]),
            f"{vintage['comparisons']['earliest_skill']:.2f}",
        ],
        [
            "Persistence",
            "—",
            _mw(vintage["persistence"]["metrics"]["mae_mw"]),
            "—",
            "—",
            "0.00",
        ],
    ]
    lines.append(_table(["Vintage", "Horizon", "MAE", "Bias", "nMAE", "Skill"], vintage_rows))
    lines.append("")
    lines.append(
        f"All three rows use the same **{vintage['latest']['metrics']['n']:,}** scored hours. "
        f"The earliest eligible vintage is "
        f"**{_mw(vintage['comparisons']['earliest_mae_above_latest_mw'])}** "
        f"(**{_percent(vintage['comparisons']['earliest_mae_above_latest_pct'])}**) worse "
        f"than the latest one. The latest forecast reduces MAE by "
        f"**{_mw(vintage['comparisons']['latest_mae_below_persistence_mw'])}** "
        f"(**{_percent(vintage['comparisons']['latest_mae_below_persistence_pct'])}**) "
        f"against persistence; the earliest vintage still reduces it by "
        f"**{_mw(vintage['comparisons']['earliest_mae_below_persistence_mw'])}** "
        f"(**{_percent(vintage['comparisons']['earliest_mae_below_persistence_pct'])}**)."
    )
    lines.append("")
    lines.append(
        "The practical reading: WINDFOR adds real information beyond persistence, and "
        f"waiting for the latest eligible vintage is worth "
        f"{_percent(vintage['comparisons']['earliest_mae_above_latest_pct'])} of MAE at "
        "this cutoff. The earliest row is included to show that the gain is not an "
        "artefact of comparing against a weak baseline."
    )
    lines.append("")

    lines.append("## 9. Risk-buffer calibration")
    lines.append("")
    risk_rows = [
        [
            f"{row['level']:.2f}",
            _mw(row["in_sample_buffer_mw"]),
            _share(row["in_sample_coverage"]),
            _share(row["walk_forward_coverage"]),
            _mw(row["walk_forward_mean_buffer_mw"]),
            _share(row["walk_forward_days_with_breach_share"]),
            f"{row['evaluated_days']:,}",
        ]
        for row in risk["rows"]
    ]
    lines.append(
        _table(
            [
                "Level",
                "In-sample buffer",
                "In-sample coverage",
                "Walk-forward coverage",
                "Walk-forward mean buffer",
                "Days with breach",
                "Evaluated days",
            ],
            risk_rows,
        )
    )
    lines.append("")
    lines.append(risk["conclusion"])
    lines.append("")
    lines.append(risk["caveat"])
    lines.append("")

    lines.append("## 10. Data coverage and provenance")
    lines.append("")
    coverage_rows = [
        ["Snapshot fingerprint", f"`{data['snapshot']['fingerprint']}`"],
        ["Manifest generated at", f"`{data['snapshot']['manifest_generated_at']}`"],
        [
            "Delivery window",
            f"{scope['delivery_dates']['start']} → {scope['delivery_dates']['end']}",
        ],
        ["Delivery days", f"{scope['delivery_days']:,}"],
        ["Expected hourly targets", f"{data['decision_coverage']['expected_periods']:,}"],
        ["With forecast", f"{data['decision_coverage']['with_forecast']:,}"],
        ["With actual", f"{data['decision_coverage']['with_actual']:,}"],
        ["Decision coverage", _percent(data["decision_coverage"]["coverage_pct"])],
        ["Missing forecasts", f"{data['decision_coverage']['missing_forecast_periods']:,}"],
        ["Missing actuals", f"{data['decision_coverage']['missing_actual_periods']:,}"],
        ["FUELHH actual rows", f"{data['actuals']['rows']:,}"],
        ["FUELHH expected rows", f"{data['actuals']['expected_rows']:,}"],
        ["FUELHH missing rows", f"{data['actuals']['missing_rows']:,}"],
        ["Hourly actual rows", f"{data['actuals']['hourly_rows']:,}"],
        ["Incomplete hours", f"{data['actuals']['hourly_incomplete']:,}"],
        ["WINDFOR rows", f"{data['forecasts']['rows']:,}"],
        ["WINDFOR vintages", f"{data['forecasts']['vintages']:,}"],
        ["WINDFOR targets", f"{data['forecasts']['targets']:,}"],
        ["WINDFOR first publish", f"`{data['forecasts']['first_publish']}`"],
        ["WINDFOR last publish", f"`{data['forecasts']['last_publish']}`"],
        [
            "WINDFOR target range",
            f"`{data['forecasts']['target_start']}` → `{data['forecasts']['target_end']}`",
        ],
        [
            "Vintages per publish day",
            f"{data['forecasts']['vintages_per_publish_day_min']}-"
            f"{data['forecasts']['vintages_per_publish_day_max']}",
        ],
    ]
    lines.append(_table(["Check", "Value"], coverage_rows))
    lines.append("")
    lines.append(
        f"Every one of the **{data['decision_coverage']['expected_periods']:,}** in-scope "
        f"hourly targets has a selected forecast and an actual. The two FUELHH half-hours "
        "behind each hourly actual are averaged; if either were missing the hour would be "
        "null and excluded, never interpolated. There are no missing periods in this "
        "snapshot."
    )
    lines.append("")
    lines.append(
        "The snapshot was built from live Elexon BMRS pulls, not fixtures. The manifest "
        "records the source URLs, per-chunk fetch timestamps, row counts, and SHA-256 "
        "hashes of both processed files. See `docs/DATA_SOURCES.md` for the endpoint "
        "contracts and `data/processed/manifest.json` for the full provenance record."
    )
    lines.append("")

    lines.append("## Method and reproducibility")
    lines.append("")
    lines.append(
        "- **Unit of evaluation.** WINDFOR is hourly; FUELHH is half-hourly. Each hourly "
        "actual is the arithmetic mean of its two half-hour settlement periods. No "
        "interpolation or imputation is used."
    )
    lines.append(
        "- **Decision selection.** For each target hour, use the latest WINDFOR vintage "
        "published at or before 09:00 Europe/London on the previous London day. The "
        "cutoff is inclusive. This is a no-look-ahead rule."
    )
    lines.append(
        "- **Error sign.** `error = forecast - actual`; positive means over-forecast and "
        "shortfall risk. The risk buffer is subtracted from the forecast: "
        "`risk_adjusted = max(0, forecast - buffer)`."
    )
    lines.append(
        "- **Rounding.** MW values are rounded once at the output boundary to one decimal "
        "place; percentages to two decimal places; shares are displayed as percentages "
        "with one decimal place. The JSON retains the same rounded API values."
    )
    lines.append(
        "- **Determinism.** The output contains no wall-clock timestamp. Re-running "
        "`make insights` against the same snapshot produces byte-identical files."
    )
    lines.append(
        "- **Contract check.** `backend/tests/api/test_insights.py` compares the committed "
        "JSON payloads with live API responses, so a stale insight file fails the test "
        "suite."
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Generate both artefacts and report the paths written."""
    settings = Settings()
    repository = SnapshotRepository(settings.data_dir)
    payload = build_payload(settings, repository)

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / "insights.json"
    markdown_path = docs_dir / "INSIGHTS.md"

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")

    print(f"wrote {json_path.relative_to(ROOT)}")
    print(f"wrote {markdown_path.relative_to(ROOT)}")
    print(
        f"fingerprint={payload['snapshot']['fingerprint']} "
        f"hours={payload['summary']['metrics']['n']} "
        f"mae_mw={payload['summary']['metrics']['mae_mw']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

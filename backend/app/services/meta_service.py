"""Metadata and health payloads describing scope, provenance and defaults."""

from __future__ import annotations

from app.config import Settings
from app.data.repository import Repository
from app.domain.constants import (
    ACTUAL_PERIOD_MINUTES,
    FORECAST_PERIOD_HOURS,
    SCOPE_NOTE,
    SIGN_CONVENTION,
)
from app.domain.timeutils import format_cutoff_label

from .formatting import utc_iso

PRODUCT_NAME = "WindLens"
VERSION = "1.0.0"


def health(repository: Repository, settings: Settings) -> dict[str, object]:
    """Return liveness, row counts and the dataset fingerprint."""
    quality = repository.data_quality()
    return {
        "status": "ok",
        "version": VERSION,
        "data_fingerprint": repository.fingerprint,
        "actual_rows": quality.get("actual_rows", len(repository.actuals())),
        "forecast_rows": quality.get("forecast_rows", len(repository.forecasts())),
        "timezone": settings.timezone,
    }


def meta(repository: Repository, settings: Settings) -> dict[str, object]:
    """Return everything the UI needs to describe the dataset and its scope."""
    delivery_dates = settings.delivery_dates()
    decision_dates = settings.decision_dates()
    quality = repository.data_quality()
    manifest = repository.manifest
    source = manifest.get("source", {}) if isinstance(manifest, dict) else {}
    return {
        "product": PRODUCT_NAME,
        "version": VERSION,
        "timezone": settings.timezone,
        "default_cutoff": format_cutoff_label(settings.default_cutoff),
        "cutoff_grid": [format_cutoff_label(value) for value in settings.cutoff_grid],
        "scope": {
            "mode": settings.scope_mode,
            "decision_dates": {
                "start": decision_dates[0].isoformat(),
                "end": decision_dates[-1].isoformat(),
            },
            "delivery_dates": {
                "start": delivery_dates[0].isoformat(),
                "end": delivery_dates[-1].isoformat(),
            },
            "delivery_days": len(delivery_dates),
        },
        "available_delivery_dates": [day.isoformat() for day in delivery_dates],
        "horizon_buckets_h": [float(value) for value in settings.horizon_buckets_h],
        "constants": {
            "period_minutes": ACTUAL_PERIOD_MINUTES,
            "forecast_period_minutes": int(FORECAST_PERIOD_HOURS * 60),
            "sign_convention": SIGN_CONVENTION,
            "mape_min_actual_mw": settings.mape_min_actual_mw,
            "min_history_days": settings.min_history_days,
            "outcome_lag_days": settings.outcome_lag_days,
        },
        "data": {
            "fingerprint": repository.fingerprint,
            "generated_at": manifest.get("generated_at"),
            "source": "Elexon BMRS FUELHH (fuelType=WIND) and WINDFOR",
            "datasets": ["FUELHH", "WINDFOR"],
            "manifest_source": source,
            "coverage": {
                "actual_periods": quality.get("actual_rows"),
                "actual_rows": quality.get("actual_rows"),
                "hourly_actual_periods": quality.get("hourly_rows"),
                "forecast_rows": quality.get("forecast_rows"),
                "forecast_vintages": quality.get("forecast_vintages"),
                "forecast_target_start": utc_iso(quality.get("forecast_target_start")),
                "forecast_target_end": utc_iso(quality.get("forecast_target_end")),
            },
            "quality": {
                "hourly_incomplete": quality.get("hourly_incomplete"),
                "actual_missing_rows": quality.get("actual_missing_rows"),
            },
        },
        "methodology": {
            "selection_rule": "latest WINDFOR vintage with publish_time <= cutoff (inclusive)",
            "cutoff_rule": (
                f"{format_cutoff_label(settings.default_cutoff)} Europe/London on the day "
                "before delivery"
            ),
            "scope_note": SCOPE_NOTE,
            "resolution_note": (
                "WINDFOR is hourly and FUELHH is half-hourly. Each hourly actual is the "
                "mean of its two half-hour settlement periods; no interpolation or "
                "imputation is applied."
            ),
            "error_sign": SIGN_CONVENTION,
            "known_caveat": (
                "Elexon describes both series as operational-metered wind, yet the "
                "observed WINDFOR level exceeds FUELHH WIND outturn in this snapshot. "
                "WindLens reports that measured difference directly rather than "
                "rescaling it away; see docs/METHODOLOGY.md."
            ),
        },
        "ai_disclosure": (
            "Built with an AI coding agent working from a written specification, with "
            "live data checks and independently executed tests. See README.md."
        ),
    }

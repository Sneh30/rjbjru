"""Normalisation tests with deliberately messy raw Elexon-shaped rows."""

from __future__ import annotations

import pandas as pd
import pytest

from app.ingestion.normalise import normalise_actuals, normalise_forecasts


def _actual_row(
    start: str,
    generation: object,
    *,
    fuel: str = "WIND",
    publish: str = "2026-01-01T00:00:00Z",
) -> dict[str, object]:
    return {
        "settlementDate": start[:10],
        "startTime": start,
        "publishTime": publish,
        "fuelType": fuel,
        "generation": generation,
    }


def test_normalise_actuals_filters_non_wind_and_keeps_latest_publication() -> None:
    rows = [
        _actual_row("2026-01-01T00:00:00Z", 1000, publish="2026-01-01T01:00:00Z"),
        _actual_row("2026-01-01T00:00:00Z", 1100, publish="2026-01-01T02:00:00Z"),
        _actual_row("2026-01-01T00:30:00Z", 1200),
        _actual_row("2026-01-01T01:00:00Z", 9999, fuel="CCGT"),
    ]
    result = normalise_actuals(rows)
    assert result.stats.input_rows == 4
    assert result.stats.non_wind_rows == 1
    assert result.stats.duplicate_rows == 1
    assert result.stats.kept_rows == 2
    assert result.frame["generation_mw"].tolist() == pytest.approx([1100.0, 1200.0])
    assert str(result.frame["start_time"].dt.tz) == "UTC"


def test_normalise_actuals_drops_unparseable_generation_and_timestamps() -> None:
    rows = [
        _actual_row("2026-01-01T00:00:00Z", "not-a-number"),
        _actual_row("2026-01-01T00:30:00Z", None),
        _actual_row("2026-01-01T01:00:00Z", 1000),
    ]
    result = normalise_actuals(rows)
    assert result.stats.nan_rows == 2
    assert result.stats.kept_rows == 1
    assert result.frame["generation_mw"].tolist() == pytest.approx([1000.0])


def test_normalise_actuals_empty_input_has_stable_columns() -> None:
    result = normalise_actuals([])
    assert result.stats.input_rows == 0
    assert result.frame.empty
    assert list(result.frame.columns) == ["start_time", "generation_mw"]
    assert isinstance(result.frame["start_time"].dtype, pd.DatetimeTZDtype)


def test_normalise_forecasts_deduplicates_target_and_publication_pairs() -> None:
    rows = [
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T07:30:00Z",
            "generation": 1000,
        },
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T07:30:00Z",
            "generation": 1100,
        },
        {
            "startTime": "2026-01-02T01:00:00Z",
            "publishTime": "2026-01-01T07:30:00Z",
            "generation": 1200,
        },
    ]
    result = normalise_forecasts(rows)
    assert result.stats.duplicate_rows == 1
    assert result.stats.kept_rows == 2
    assert result.frame["generation_mw"].tolist() == pytest.approx([1100.0, 1200.0])
    assert list(result.frame.columns) == ["start_time", "publish_time", "generation_mw"]


def test_normalise_forecasts_drops_invalid_values_and_orders_rows() -> None:
    rows = [
        {
            "startTime": "2026-01-02T02:00:00Z",
            "publishTime": "2026-01-01T09:30:00Z",
            "generation": 1400,
        },
        {
            "startTime": "2026-01-02T00:00:00Z",
            "publishTime": "2026-01-01T07:30:00Z",
            "generation": 1000,
        },
        {
            "startTime": "2026-01-02T01:00:00Z",
            "publishTime": "2026-01-01T07:30:00Z",
            "generation": None,
        },
    ]
    result = normalise_forecasts(rows)
    assert result.stats.nan_rows == 1
    assert result.frame["start_time"].dt.hour.tolist() == [0, 2]
    assert result.frame["generation_mw"].tolist() == pytest.approx([1000.0, 1400.0])


def test_normalise_forecasts_empty_input_has_stable_columns() -> None:
    result = normalise_forecasts([])
    assert result.frame.empty
    assert list(result.frame.columns) == ["start_time", "publish_time", "generation_mw"]


def test_committed_live_samples_still_normalise() -> None:
    """The two documented raw samples remain valid Elexon-shaped payloads."""
    import json
    from pathlib import Path

    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    actual_rows = json.loads((fixtures / "raw_fuelhh_sample.json").read_text())
    forecast_rows = json.loads((fixtures / "raw_windfor_sample.json").read_text())

    actuals = normalise_actuals(actual_rows)
    forecasts = normalise_forecasts(forecast_rows)

    assert actuals.stats.kept_rows == 4
    assert actuals.frame["start_time"].is_monotonic_increasing
    assert forecasts.stats.kept_rows == 4
    assert forecasts.frame["publish_time"].nunique() == 1

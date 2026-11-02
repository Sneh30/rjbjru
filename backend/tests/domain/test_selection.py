"""Decision-time vintage selection, cutoff inclusivity and leakage post-conditions."""

from __future__ import annotations

import pandas as pd
import pytest

from app.domain.errors import DataIntegrityError
from app.domain.selection import (
    SELECTED_COLUMNS,
    select_decision_forecasts,
    select_earliest_forecasts,
)
from tests.helpers import forecast_frame

TARGET = "2026-01-15T12:00:00Z"


def test_latest_eligible_vintage_wins_and_cutoff_is_inclusive() -> None:
    forecasts = forecast_frame(
        [
            (TARGET, "2026-01-14T07:30:00Z", 1000.0),
            (TARGET, "2026-01-14T09:00:00Z", 1100.0),  # exactly at the cutoff
            (TARGET, "2026-01-14T09:30:00Z", 1200.0),  # after the cutoff
        ]
    )
    selected = select_decision_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())

    assert len(selected) == 1
    row = selected.iloc[0]
    assert row["forecast_mw"] == pytest.approx(1100.0)
    assert row["publish_time"] == pd.Timestamp("2026-01-14T09:00:00Z")
    assert row["horizon_h"] == pytest.approx(27.0)
    assert row["delivery_date"] == pd.Timestamp("2026-01-15").date()
    assert row["cutoff_utc"] == pd.Timestamp("2026-01-14T09:00:00Z")


def test_earliest_selector_picks_the_oldest_eligible_vintage() -> None:
    forecasts = forecast_frame(
        [
            (TARGET, "2026-01-13T22:30:00Z", 900.0),
            (TARGET, "2026-01-14T07:30:00Z", 1000.0),
            (TARGET, "2026-01-14T09:00:00Z", 1100.0),
        ]
    )
    selected = select_earliest_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())
    assert selected.iloc[0]["forecast_mw"] == pytest.approx(900.0)
    assert selected.iloc[0]["horizon_h"] == pytest.approx(37.5)


def test_one_row_per_target_across_multiple_days() -> None:
    forecasts = forecast_frame(
        [
            ("2026-01-15T00:00:00Z", "2026-01-14T07:30:00Z", 1000.0),
            ("2026-01-15T00:00:00Z", "2026-01-14T08:30:00Z", 1050.0),
            ("2026-01-16T00:00:00Z", "2026-01-15T07:30:00Z", 2000.0),
            ("2026-01-16T00:00:00Z", "2026-01-15T09:30:00Z", 2100.0),
        ]
    )
    selected = select_decision_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())
    assert len(selected) == 2
    assert selected["start_time"].is_unique
    assert selected.set_index("start_time")["forecast_mw"].to_dict() == {
        pd.Timestamp("2026-01-15T00:00:00Z"): 1050.0,
        pd.Timestamp("2026-01-16T00:00:00Z"): 2000.0,
    }


def test_targets_without_an_eligible_vintage_are_omitted() -> None:
    forecasts = forecast_frame(
        [
            ("2026-01-15T00:00:00Z", "2026-01-14T09:30:00Z", 1000.0),
            ("2026-01-16T00:00:00Z", "2026-01-15T07:30:00Z", 2000.0),
        ]
    )
    selected = select_decision_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())
    assert selected["start_time"].tolist() == [pd.Timestamp("2026-01-16T00:00:00Z")]


def test_no_eligible_vintages_returns_a_stable_empty_frame() -> None:
    forecasts = forecast_frame([(TARGET, "2026-01-14T09:30:00Z", 1000.0)])
    selected = select_decision_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())
    assert selected.empty
    assert list(selected.columns) == list(SELECTED_COLUMNS)


def test_empty_forecast_frame_returns_a_stable_empty_frame() -> None:
    empty = pd.DataFrame(
        {
            "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
            "publish_time": pd.Series(dtype="datetime64[ns, UTC]"),
            "generation_mw": pd.Series(dtype="float64"),
        }
    )
    selected = select_decision_forecasts(empty, pd.Timestamp("2026-01-14T09:00:00").time())
    assert selected.empty
    assert list(selected.columns) == list(SELECTED_COLUMNS)


def test_missing_columns_raise_data_integrity_error() -> None:
    with pytest.raises(DataIntegrityError, match="missing columns"):
        select_decision_forecasts(
            pd.DataFrame({"start_time": pd.Series(dtype="datetime64[ns, UTC]")}),
            pd.Timestamp("2026-01-14T09:00:00").time(),
        )


def test_naive_timestamps_raise_data_integrity_error() -> None:
    naive = pd.DataFrame(
        {
            "start_time": pd.to_datetime(["2026-01-15T12:00:00"]),
            "publish_time": pd.to_datetime(["2026-01-14T07:30:00"]),
            "generation_mw": [1000.0],
        }
    )
    with pytest.raises(DataIntegrityError, match="timezone-aware"):
        select_decision_forecasts(naive, pd.Timestamp("2026-01-14T09:00:00").time())


def test_non_utc_timestamps_raise_data_integrity_error() -> None:
    local = pd.DataFrame(
        {
            "start_time": pd.to_datetime(["2026-01-15T12:00:00+01:00"]),
            "publish_time": pd.to_datetime(["2026-01-14T07:30:00+01:00"]),
            "generation_mw": [1000.0],
        }
    )
    with pytest.raises(DataIntegrityError, match="UTC"):
        select_decision_forecasts(local, pd.Timestamp("2026-01-14T09:00:00").time())


def test_duplicate_forecast_rows_cannot_create_two_selected_targets() -> None:
    duplicated = forecast_frame(
        [
            (TARGET, "2026-01-14T07:30:00Z", 1000.0),
            (TARGET, "2026-01-14T07:30:00Z", 1000.0),
        ]
    )
    # The selector picks one index per target; the post-condition then holds.
    selected = select_decision_forecasts(duplicated, pd.Timestamp("2026-01-14T09:00:00").time())
    assert len(selected) == 1
    assert selected["start_time"].is_unique


def test_dst_day_cutoff_still_uses_the_previous_london_calendar_day() -> None:
    forecasts = forecast_frame(
        [
            ("2025-03-31T12:00:00Z", "2025-03-30T07:30:00Z", 1000.0),
            ("2025-03-31T12:00:00Z", "2025-03-30T09:00:00Z", 1100.0),
            ("2025-03-31T12:00:00Z", "2025-03-30T10:00:00Z", 1200.0),
        ]
    )
    selected = select_decision_forecasts(forecasts, pd.Timestamp("2025-03-30T09:00:00").time())
    # 09:00 London on 30 March is 08:00 UTC, so the 09:00Z row is ineligible.
    assert selected.iloc[0]["forecast_mw"] == pytest.approx(1000.0)
    assert selected.iloc[0]["cutoff_utc"] == pd.Timestamp("2025-03-30T08:00:00Z")

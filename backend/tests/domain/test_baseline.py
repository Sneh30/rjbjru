"""Persistence baseline: only complete hourly actuals known at the cutoff may be used."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.domain.baseline import (
    BASELINE_NAME,
    baseline_summary,
    persistence_for_selected,
)
from tests.helpers import hourly_actuals


def _selected() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "start_time": pd.to_datetime(
                ["2026-01-15T00:00:00Z", "2026-01-15T01:00:00Z"], utc=True
            ),
            "delivery_date": [date(2026, 1, 15), date(2026, 1, 15)],
            "forecast_mw": [1000.0, 1100.0],
        }
    )


def test_persistence_uses_the_latest_complete_hour_before_the_cutoff() -> None:
    actuals = hourly_actuals(
        [
            ("2026-01-14T07:00:00Z", 100.0),
            ("2026-01-14T08:00:00Z", 200.0),  # ends exactly at 09:00Z: eligible
            ("2026-01-14T09:00:00Z", 300.0),  # ends at 10:00Z: not yet known
            ("2026-01-15T00:00:00Z", 400.0),  # future outcome: must not leak
        ]
    )
    cutoff = pd.Timestamp("2026-01-14T09:00:00").time()
    joined = persistence_for_selected(_selected(), actuals, cutoff)
    assert joined["baseline_mw"].tolist() == pytest.approx([200.0, 200.0])


def test_persistence_is_null_when_no_complete_prior_actual_exists() -> None:
    actuals = hourly_actuals([("2026-01-15T00:00:00Z", 400.0)])
    cutoff = pd.Timestamp("2026-01-14T09:00:00").time()
    joined = persistence_for_selected(_selected(), actuals, cutoff)
    assert joined["baseline_mw"].isna().all()


def test_persistence_skips_missing_actual_values() -> None:
    actuals = hourly_actuals([("2026-01-14T08:00:00Z", float("nan"))])
    cutoff = pd.Timestamp("2026-01-14T09:00:00").time()
    joined = persistence_for_selected(_selected(), actuals, cutoff)
    assert joined["baseline_mw"].isna().all()


def test_baseline_summary_uses_only_common_rows_and_reports_skill() -> None:
    joined = pd.DataFrame(
        {
            "forecast_mw": [1050.0, 1150.0, 1000.0],
            "actual_mw": [1000.0, 1200.0, 1100.0],
            "baseline_mw": [900.0, 900.0, float("nan")],
        }
    )
    summary = baseline_summary(joined)
    assert summary.name == BASELINE_NAME
    assert summary.n == 2
    assert summary.forecast_mae_mw == pytest.approx(50.0)
    assert summary.mae_mw == pytest.approx(200.0)
    assert summary.skill == pytest.approx(1.0 - 50.0 / 200.0)


def test_baseline_summary_is_undefined_without_common_rows() -> None:
    joined = pd.DataFrame(
        {
            "forecast_mw": [1000.0],
            "actual_mw": [1000.0],
            "baseline_mw": [float("nan")],
        }
    )
    summary = baseline_summary(joined)
    assert summary.n == 0
    assert summary.mae_mw is None
    assert summary.skill is None

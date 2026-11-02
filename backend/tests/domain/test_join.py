"""Joins preserve the buyer sign convention and never fabricate missing actuals."""

from __future__ import annotations

import pandas as pd
import pytest

from app.domain.join import join_all_vintages, join_selected_actuals
from app.domain.selection import select_decision_forecasts
from tests.helpers import forecast_frame, hourly_actuals


def _selected() -> pd.DataFrame:
    forecasts = forecast_frame(
        [
            ("2026-01-15T12:00:00Z", "2026-01-14T07:30:00Z", 1000.0),
            ("2026-01-15T13:00:00Z", "2026-01-14T07:30:00Z", 1100.0),
        ]
    )
    return select_decision_forecasts(forecasts, pd.Timestamp("2026-01-14T09:00:00").time())


def test_join_derives_signed_error_abs_error_and_shortfall() -> None:
    actuals = hourly_actuals([("2026-01-15T12:00:00Z", 1200.0), ("2026-01-15T13:00:00Z", 900.0)])
    joined = join_selected_actuals(_selected(), actuals)
    assert joined["error_mw"].tolist() == pytest.approx([-200.0, 200.0])
    assert joined["abs_error_mw"].tolist() == pytest.approx([200.0, 200.0])
    assert joined["shortfall_mw"].tolist() == pytest.approx([0.0, 200.0])


def test_missing_actual_is_kept_as_null_and_never_imputed() -> None:
    actuals = hourly_actuals([("2026-01-15T12:00:00Z", 1200.0)])
    joined = join_selected_actuals(_selected(), actuals)
    assert len(joined) == 2
    missing = joined.loc[joined["start_time"] == pd.Timestamp("2026-01-15T13:00:00Z")].iloc[0]
    assert pd.isna(missing["actual_mw"])
    assert pd.isna(missing["error_mw"])
    assert pd.isna(missing["shortfall_mw"])


def test_join_all_vintages_keeps_every_vintage_and_only_targets_with_actuals() -> None:
    forecasts = forecast_frame(
        [
            ("2026-01-15T12:00:00Z", "2026-01-13T07:30:00Z", 900.0),
            ("2026-01-15T12:00:00Z", "2026-01-14T07:30:00Z", 1000.0),
            ("2026-01-16T12:00:00Z", "2026-01-15T07:30:00Z", 1500.0),
        ]
    )
    actuals = hourly_actuals([("2026-01-15T12:00:00Z", 1100.0)])
    joined = join_all_vintages(forecasts, actuals)
    assert len(joined) == 2
    assert joined["start_time"].nunique() == 1
    assert joined["error_mw"].tolist() == pytest.approx([-200.0, -100.0])
    assert joined["forecast_mw"].tolist() == pytest.approx([900.0, 1000.0])
    assert joined["horizon_h"].tolist() == pytest.approx([52.5, 28.5])


def test_join_all_vintages_keeps_negative_horizon_rows_for_the_caller_to_count() -> None:
    forecasts = forecast_frame([("2026-01-15T12:00:00Z", "2026-01-15T13:00:00Z", 1000.0)])
    actuals = hourly_actuals([("2026-01-15T12:00:00Z", 1100.0)])
    joined = join_all_vintages(forecasts, actuals)
    assert len(joined) == 1
    assert joined.iloc[0]["horizon_h"] == pytest.approx(-1.0)

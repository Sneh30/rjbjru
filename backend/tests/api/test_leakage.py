"""Leakage audit against the committed real snapshot.

This is the Tier-1 T2 audit: it does not use the unit-test fixtures. It loads
``data/processed`` through the production repository, re-runs the decision-time
selector, and independently recomputes the latest eligible publication for every
selected target. Any post-cutoff row or any non-latest eligible choice fails.
"""

from __future__ import annotations

from datetime import time

import pandas as pd
import pytest

from app.config import Settings
from app.data.repository import Repository
from app.domain.selection import select_decision_forecasts


@pytest.mark.snapshot
def test_no_leakage_on_real_snapshot(
    repository: Repository,
    settings: Settings,
) -> None:
    """Every selected vintage is the latest one published at or before its cutoff."""
    forecasts = repository.forecasts()
    default_cutoff: time = settings.default_cutoff
    delivery_dates = set(settings.delivery_dates())

    selected = select_decision_forecasts(forecasts, default_cutoff)
    in_scope = selected.loc[selected["delivery_date"].isin(delivery_dates)].reset_index(drop=True)

    assert len(in_scope) == 744, f"expected 744 in-scope hourly targets, got {len(in_scope)}"
    assert not bool(in_scope["start_time"].duplicated().any())

    for row in in_scope.itertuples(index=False):
        same_target = forecasts.loc[forecasts["start_time"] == row.start_time]
        eligible = same_target.loc[same_target["publish_time"] <= row.cutoff_utc]
        assert not eligible.empty, f"no eligible vintage for {row.start_time}"
        latest = eligible["publish_time"].max()
        assert row.publish_time == latest, (
            f"selected {row.publish_time} for {row.start_time}, but {latest} was eligible"
        )
        assert row.publish_time <= row.cutoff_utc, (
            f"selected {row.publish_time} after cutoff {row.cutoff_utc} for {row.start_time}"
        )
        assert row.horizon_h >= 0

    actuals = repository.hourly_actuals()
    merged = in_scope.merge(
        actuals,
        on="start_time",
        how="left",
        validate="one_to_one",
    )
    assert int(merged["actual_mw"].isna().sum()) == 0
    assert len(pd.unique(in_scope["delivery_date"])) == len(delivery_dates)

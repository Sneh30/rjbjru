"""Snapshot validation: hard failures, coverage and the quality report."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import time
from pathlib import Path

import pandas as pd
import pytest

from app.config import Settings
from app.domain.errors import DataIntegrityError
from app.ingestion.normalise import NormaliseStats
from app.ingestion.validate import build_quality_report, write_quality_report

STATS = NormaliseStats(0, 0, 0, 0, 0)


def _settings() -> Settings:
    return Settings(
        data_dir=Path("/tmp/windlens-test-data"),
        scope_mode="delivery_date",
        scope_start=pd.Timestamp("2026-01-01").date(),
        scope_end=pd.Timestamp("2026-01-01").date(),
        default_cutoff=time(9, 0),
        ingest_actuals_start="2026-01-01T00:00:00Z",
        ingest_actuals_end="2026-01-02T00:00:00Z",
        ingest_forecast_publish_start="2025-12-30T00:00:00Z",
        ingest_forecast_publish_end="2026-01-02T00:00:00Z",
        log_level="CRITICAL",
    )


def _actuals() -> pd.DataFrame:
    times = pd.date_range("2026-01-01T00:00:00Z", periods=48, freq="30min", tz="UTC")
    return pd.DataFrame({"start_time": times, "generation_mw": [1000.0] * 48})


def _forecasts() -> pd.DataFrame:
    targets = pd.date_range("2026-01-01T00:00:00Z", periods=24, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "start_time": targets,
            "publish_time": pd.Timestamp("2025-12-31T07:30:00Z"),
            "generation_mw": [1200.0] * 24,
        }
    )


def test_quality_report_accepts_a_complete_day() -> None:
    report = build_quality_report(_settings(), _actuals(), _forecasts(), STATS, STATS)
    assert report["actuals"]["rows"] == 48  # type: ignore[index]
    assert report["actuals"]["missing_periods"] == []  # type: ignore[index]
    assert report["forecasts"]["rows"] == 24  # type: ignore[index]
    assert report["forecasts"]["resolution_minutes"] == 60  # type: ignore[index]
    assert report["decision_coverage"]["coverage_pct"] == 100.0  # type: ignore[index]
    assert report["decision_coverage"]["hourly_periods_expected"] == 24  # type: ignore[index]
    assert report["warnings"] == []
    assert report["errors"] == []


def test_quality_report_warns_about_missing_actuals_and_forecasts() -> None:
    actuals = _actuals().drop(index=24).reset_index(drop=True)
    forecasts = _forecasts().drop(index=12).reset_index(drop=True)
    report = build_quality_report(_settings(), actuals, forecasts, STATS, STATS)
    assert len(report["actuals"]["missing_periods"]) == 1  # type: ignore[index]
    assert report["decision_coverage"]["hourly_periods_missing"] == [  # type: ignore[index]
        "2026-01-01T12:00:00+00:00"
    ]
    assert len(report["warnings"]) == 2  # type: ignore[index]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda frame: pd.DataFrame(columns=["start_time", "generation_mw"]),
        lambda frame: frame.assign(start_time=frame["start_time"].dt.tz_localize(None)),
        lambda frame: frame.assign(start_time=frame["start_time"] + pd.Timedelta(minutes=15)),
        lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True),
        lambda frame: frame.assign(generation_mw=frame["generation_mw"].mask(frame.index == 0)),
        lambda frame: frame.assign(generation_mw=-1.0),
    ],
)
def test_hard_actual_checks_reject_bad_frames(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
) -> None:
    broken = mutate(_actuals())
    with pytest.raises(DataIntegrityError):
        build_quality_report(_settings(), broken, _forecasts(), STATS, STATS)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda frame: pd.DataFrame(columns=["start_time", "publish_time", "generation_mw"]),
        lambda frame: frame.assign(start_time=frame["start_time"] + pd.Timedelta(minutes=30)),
        lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True),
        lambda frame: frame.assign(generation_mw=frame["generation_mw"].mask(frame.index == 0)),
        lambda frame: frame.assign(generation_mw=-1.0),
    ],
)
def test_hard_forecast_checks_reject_bad_frames(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
) -> None:
    broken = mutate(_forecasts())
    with pytest.raises(DataIntegrityError):
        build_quality_report(_settings(), _actuals(), broken, STATS, STATS)


def test_write_quality_report_is_readable_json(tmp_path: Path) -> None:
    path = tmp_path / "quality_report.json"
    report = build_quality_report(_settings(), _actuals(), _forecasts(), STATS, STATS)
    write_quality_report(path, report)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 1
    assert path.read_text(encoding="utf-8").endswith("\n")

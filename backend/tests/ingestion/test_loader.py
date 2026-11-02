"""Snapshot loading, hourly aggregation and repository integrity checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from app.data.loader import (
    hourly_actuals_from_half_hourly,
    load_actuals,
    load_forecasts,
    load_manifest,
    sha256_file,
)
from app.data.repository import SnapshotRepository, delivery_dates_in_frame
from app.domain.errors import DataIntegrityError


def _write_gz(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, compression="gzip")


def _actual_csv(path: Path) -> None:
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": ["2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"],
                "generation_mw": [1000.0, 1200.0],
            }
        ),
    )


def _forecast_csv(path: Path) -> None:
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": ["2026-01-02T00:00:00Z"],
                "publish_time": ["2026-01-01T07:30:00Z"],
                "generation_mw": [1100.0],
            }
        ),
    )


def test_hourly_aggregation_averages_complete_pairs_only() -> None:
    actuals = pd.DataFrame(
        {
            "start_time": pd.to_datetime(
                [
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:30:00Z",
                    "2026-01-01T01:00:00Z",
                    "2026-01-01T02:00:00Z",
                    "2026-01-01T02:30:00Z",
                ],
                utc=True,
            ),
            "generation_mw": [1000.0, 1400.0, 1100.0, 900.0, 1000.0],
        }
    )
    hourly = hourly_actuals_from_half_hourly(actuals)
    assert hourly["start_time"].dt.strftime("%H:%M").tolist() == ["00:00", "01:00", "02:00"]
    assert hourly["half_hours"].tolist() == [2, 1, 2]
    assert hourly["actual_mw"].iloc[0] == pytest.approx(1200.0)
    assert pd.isna(hourly["actual_mw"].iloc[1])
    assert hourly["actual_mw"].iloc[2] == pytest.approx(950.0)


def test_load_actuals_reads_utc_and_sorts(tmp_path: Path) -> None:
    path = tmp_path / "actuals.csv.gz"
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": ["2026-01-01T00:30:00Z", "2026-01-01T00:00:00Z"],
                "generation_mw": [1200.0, 1000.0],
            }
        ),
    )
    frame = load_actuals(path)
    assert str(frame["start_time"].dt.tz) == "UTC"
    assert frame["generation_mw"].tolist() == [1000.0, 1200.0]


def test_load_actuals_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "actuals.csv.gz"
    _write_gz(path, pd.DataFrame({"start_time": ["2026-01-01T00:00:00Z"]}))
    with pytest.raises(DataIntegrityError, match="missing columns"):
        load_actuals(path)


def test_load_actuals_rejects_duplicate_start_times(tmp_path: Path) -> None:
    path = tmp_path / "actuals.csv.gz"
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
                "generation_mw": [1000.0, 1100.0],
            }
        ),
    )
    with pytest.raises(DataIntegrityError, match="duplicate"):
        load_actuals(path)


def test_load_forecasts_reads_utc_and_sorts(tmp_path: Path) -> None:
    path = tmp_path / "forecasts.csv.gz"
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": [
                    "2026-01-02T01:00:00Z",
                    "2026-01-02T00:00:00Z",
                ],
                "publish_time": [
                    "2026-01-01T09:30:00Z",
                    "2026-01-01T07:30:00Z",
                ],
                "generation_mw": [1100.0, 1000.0],
            }
        ),
    )
    frame = load_forecasts(path)
    assert frame["start_time"].dt.hour.tolist() == [0, 1]
    assert str(frame["publish_time"].dt.tz) == "UTC"


def test_load_forecasts_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "forecasts.csv.gz"
    _write_gz(path, pd.DataFrame({"start_time": ["2026-01-02T00:00:00Z"]}))
    with pytest.raises(DataIntegrityError, match="missing columns"):
        load_forecasts(path)


def test_load_forecasts_rejects_duplicate_vintages(tmp_path: Path) -> None:
    path = tmp_path / "forecasts.csv.gz"
    _write_gz(
        path,
        pd.DataFrame(
            {
                "start_time": ["2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"],
                "publish_time": ["2026-01-01T07:30:00Z", "2026-01-01T07:30:00Z"],
                "generation_mw": [1000.0, 1100.0],
            }
        ),
    )
    with pytest.raises(DataIntegrityError, match="duplicate"):
        load_forecasts(path)


def test_load_manifest_requires_an_object(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    with pytest.raises(DataIntegrityError, match="not found"):
        load_manifest(path)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(DataIntegrityError, match="JSON object"):
        load_manifest(path)
    path.write_text('{"fingerprint": "abc"}', encoding="utf-8")
    assert load_manifest(path)["fingerprint"] == "abc"


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"windlens")
    assert sha256_file(path) == hashlib.sha256(b"windlens").hexdigest()


def test_snapshot_repository_verifies_hashes_and_builds_quality(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    actuals_path = processed / "actuals.csv.gz"
    forecasts_path = processed / "forecasts.csv.gz"
    _actual_csv(actuals_path)
    _forecast_csv(forecasts_path)
    manifest = {
        "fingerprint": "abc123",
        "processed": {
            "actuals": {"sha256": sha256_file(actuals_path)},
            "forecasts": {"sha256": sha256_file(forecasts_path)},
        },
    }
    (processed / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    repository = SnapshotRepository(tmp_path)
    assert repository.fingerprint == "abc123"
    assert len(repository.actuals()) == 2
    assert len(repository.forecasts()) == 1
    assert len(repository.hourly_actuals()) == 1
    quality = repository.data_quality()
    assert quality["actual_rows"] == 2
    assert quality["forecast_rows"] == 1
    assert quality["hourly_incomplete"] == 0
    assert quality["actual_missing_rows"] == 0


def test_snapshot_repository_rejects_a_tampered_file(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    actuals_path = processed / "actuals.csv.gz"
    forecasts_path = processed / "forecasts.csv.gz"
    _actual_csv(actuals_path)
    _forecast_csv(forecasts_path)
    manifest = {
        "fingerprint": "abc123",
        "processed": {
            "actuals": {"sha256": sha256_file(actuals_path)},
            "forecasts": {"sha256": sha256_file(forecasts_path)},
        },
    }
    (processed / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    actuals_path.write_bytes(b"tampered")
    with pytest.raises(DataIntegrityError, match="hash"):
        SnapshotRepository(tmp_path)


def test_snapshot_repository_requires_a_manifest(tmp_path: Path) -> None:
    with pytest.raises(DataIntegrityError, match="manifest"):
        SnapshotRepository(tmp_path)


def test_delivery_dates_in_frame_are_sorted_and_local() -> None:
    frame = pd.DataFrame(
        {"start_time": pd.to_datetime(["2026-06-01T23:30:00Z", "2026-06-01T00:00:00Z"], utc=True)}
    )
    assert [day.isoformat() for day in delivery_dates_in_frame(frame)] == [
        "2026-06-01",
        "2026-06-02",
    ]

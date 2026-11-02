"""Ingestion orchestration with a fake HTTP client and a synthetic raw cache."""

from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import pytest

from app.config import Settings
from app.domain.errors import DataIntegrityError
from app.ingestion import pipeline
from app.ingestion.pipeline import (
    _day_range,
    _frame_for_csv,
    _write_frame_gz,
    build_snapshot,
    fetch_all,
    verify_snapshot,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        scope_mode="delivery_date",
        scope_start=date(2026, 1, 1),
        scope_end=date(2026, 1, 1),
        default_cutoff=time(9, 0),
        ingest_actuals_start="2026-01-01T00:00:00Z",
        ingest_actuals_end="2026-01-02T00:00:00Z",
        ingest_forecast_publish_start="2025-12-31T00:00:00Z",
        ingest_forecast_publish_end="2026-01-01T00:00:00Z",
        log_level="CRITICAL",
    )


def _actual_payload() -> bytes:
    rows = [
        {
            "settlementDate": "2026-01-01",
            "startTime": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishTime": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fuelType": "WIND",
            "generation": 1000,
        }
        for stamp in pd.date_range("2026-01-01T00:00:00Z", periods=48, freq="30min", tz="UTC")
    ]
    return json.dumps(rows).encode()


def _forecast_payload() -> bytes:
    rows = [
        {
            "startTime": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishTime": "2025-12-31T07:30:00Z",
            "generation": 1200,
        }
        for stamp in pd.date_range("2026-01-01T00:00:00Z", periods=24, freq="1h", tz="UTC")
    ]
    return json.dumps(rows).encode()


class FakeClient:
    """Stand-in for :class:`ElexonClient` that records calls."""

    calls: ClassVar[list[tuple[str, date]]] = []

    def __init__(self, **_: Any) -> None:
        pass

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def fetch_actuals_day(self, day: date) -> tuple[bytes, str, dict[str, str]]:
        FakeClient.calls.append(("FUELHH", day))
        return (
            _actual_payload(),
            f"https://example.test/FUELHH?date={day.isoformat()}",
            {"settlementDateFrom": day.isoformat()},
        )

    def fetch_forecasts_publish_day(self, day: date) -> tuple[bytes, str, dict[str, str]]:
        FakeClient.calls.append(("WINDFOR", day))
        return (
            _forecast_payload(),
            f"https://example.test/WINDFOR?date={day.isoformat()}",
            {"publishDateTimeFrom": f"{day.isoformat()}T00:00:00Z"},
        )


def test_day_range_is_end_exclusive() -> None:
    assert _day_range(date(2026, 1, 1), date(2026, 1, 4)) == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert _day_range(date(2026, 1, 1), date(2026, 1, 1)) == []


def test_frame_for_csv_formats_timestamps_as_utc_seconds() -> None:
    frame = pd.DataFrame(
        {
            "start_time": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True),
            "publish_time": pd.to_datetime(["2025-12-31T07:30:00Z"], utc=True),
            "generation_mw": [1000.0],
        }
    )
    output = _frame_for_csv(frame, ("start_time", "publish_time"))
    assert output["start_time"].tolist() == ["2026-01-01T00:00:00Z"]
    assert output["publish_time"].tolist() == ["2025-12-31T07:30:00Z"]


def test_write_frame_gz_is_deterministic(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "start_time": pd.to_datetime(["2026-01-01T00:00:00Z"], utc=True),
            "generation_mw": [1000.0],
        }
    )
    first = _write_frame_gz(tmp_path / "a.csv.gz", frame, ("start_time",))
    second = _write_frame_gz(tmp_path / "b.csv.gz", frame, ("start_time",))
    assert first == second
    assert (tmp_path / "a.csv.gz").read_bytes() == (tmp_path / "b.csv.gz").read_bytes()


def test_fetch_all_is_idempotent_and_force_refetches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeClient.calls = []
    monkeypatch.setattr(pipeline, "ElexonClient", FakeClient)
    settings = _settings(tmp_path)

    manifest = fetch_all(settings)
    assert len(manifest["chunks"]) == 2
    assert [call[0] for call in FakeClient.calls] == ["FUELHH", "WINDFOR"]
    for chunk in manifest["chunks"]:
        assert (settings.data_dir / chunk["file"]).exists()
        assert len(chunk["sha256"]) == 64

    fetch_all(settings)
    assert len(FakeClient.calls) == 2  # cached files are not refetched

    fetch_all(settings, force=True)
    assert len(FakeClient.calls) == 4


def _write_raw(settings: Settings) -> None:
    fuelhh = settings.raw_dir / "fuelhh" / "2026-01-01.json"
    windfor = settings.raw_dir / "windfor" / "2025-12-31.json"
    fuelhh.parent.mkdir(parents=True, exist_ok=True)
    windfor.parent.mkdir(parents=True, exist_ok=True)
    fuelhh.write_bytes(_actual_payload())
    windfor.write_bytes(_forecast_payload())


def test_build_snapshot_writes_a_verifiable_manifest(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_raw(settings)
    manifest = build_snapshot(settings)

    assert manifest["fingerprint"]
    assert manifest["selection_rows_default_cutoff"] == 24
    assert manifest["processed"]["actuals"]["rows"] == 48
    assert manifest["processed"]["forecasts"]["rows"] == 24
    assert (settings.processed_dir / "actuals.csv.gz").exists()
    assert (settings.processed_dir / "forecasts.csv.gz").exists()
    assert (settings.processed_dir / "quality_report.json").exists()

    verification = verify_snapshot(settings)
    assert verification["fingerprint_ok"] is True
    assert all(check["ok"] for check in verification["files"])

    # Rebuilding is byte-for-byte deterministic apart from the timestamp.
    original = (settings.processed_dir / "actuals.csv.gz").read_bytes()
    build_snapshot(settings)
    assert (settings.processed_dir / "actuals.csv.gz").read_bytes() == original


def test_build_snapshot_refuses_an_empty_cache(tmp_path: Path) -> None:
    with pytest.raises(DataIntegrityError, match="raw cache is empty"):
        build_snapshot(_settings(tmp_path))


def test_verify_snapshot_detects_tampering(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_raw(settings)
    build_snapshot(settings)
    (settings.processed_dir / "actuals.csv.gz").write_bytes(b"tampered")
    with pytest.raises(DataIntegrityError, match="verification failed"):
        verify_snapshot(settings)


def test_verify_snapshot_requires_a_manifest(tmp_path: Path) -> None:
    with pytest.raises(DataIntegrityError, match="manifest is missing"):
        verify_snapshot(_settings(tmp_path))

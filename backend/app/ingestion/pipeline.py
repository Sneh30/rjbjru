"""Ingestion orchestration: fetch raw chunks, normalise, validate, write snapshot."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import Settings
from app.data.loader import sha256_file
from app.domain.constants import SIGN_CONVENTION
from app.domain.errors import DataIntegrityError
from app.domain.selection import select_decision_forecasts
from app.domain.timeutils import format_cutoff_label

from .elexon_client import ElexonClient, parse_payload
from .normalise import NormaliseStats, normalise_actuals, normalise_forecasts
from .validate import build_quality_report, write_quality_report

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _day_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor < end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    serialised = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    _write_bytes_atomic(path, serialised.encode("utf-8"))


def _read_fetch_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "chunks": []}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DataIntegrityError("raw manifest must be a JSON object")
    payload.setdefault("chunks", [])
    return payload


def _chunk_entry(
    dataset: str,
    day: date,
    url: str,
    params: dict[str, str],
    content: bytes,
    rows: int,
    relative_file: str,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "date": day.isoformat(),
        "url": url,
        "params": params,
        "file": relative_file,
        "rows": rows,
        "sha256": hashlib.sha256(content).hexdigest(),
        "fetched_at": _utc_now(),
    }


def fetch_all(settings: Settings, *, force: bool = False) -> dict[str, Any]:
    """Fetch every required raw chunk, skipping verified existing files.

    Args:
        settings: Window configuration.
        force: Refetch even when a cached chunk exists.

    Returns:
        The raw fetch manifest.
    """
    raw_dir = settings.raw_dir
    manifest_path = raw_dir / "manifest.json"
    manifest = _read_fetch_manifest(manifest_path)
    existing = {(chunk["dataset"], chunk["date"]): chunk for chunk in manifest["chunks"]}

    actual_start = pd.Timestamp(settings.ingest_actuals_start).date()
    actual_end = pd.Timestamp(settings.ingest_actuals_end).date()
    forecast_start = pd.Timestamp(settings.ingest_forecast_publish_start).date()
    forecast_end = pd.Timestamp(settings.ingest_forecast_publish_end).date()

    with ElexonClient(base_url=settings.elexon_base_url) as client:
        for day in _day_range(actual_start, actual_end):
            path = raw_dir / "fuelhh" / f"{day.isoformat()}.json"
            key = ("FUELHH", day.isoformat())
            if path.exists() and not force:
                LOGGER.info("actuals %s cached", day)
                continue
            content, url, params = client.fetch_actuals_day(day)
            rows = parse_payload(content, dataset="FUELHH")
            _write_bytes_atomic(path, content)
            existing[key] = _chunk_entry(
                "FUELHH",
                day,
                url,
                params,
                content,
                len(rows),
                path.relative_to(settings.data_dir).as_posix(),
            )
            LOGGER.info("actuals %s: %d rows", day, len(rows))

        for day in _day_range(forecast_start, forecast_end):
            path = raw_dir / "windfor" / f"{day.isoformat()}.json"
            key = ("WINDFOR", day.isoformat())
            if path.exists() and not force:
                LOGGER.info("forecasts %s cached", day)
                continue
            content, url, params = client.fetch_forecasts_publish_day(day)
            rows = parse_payload(content, dataset="WINDFOR")
            _write_bytes_atomic(path, content)
            existing[key] = _chunk_entry(
                "WINDFOR",
                day,
                url,
                params,
                content,
                len(rows),
                path.relative_to(settings.data_dir).as_posix(),
            )
            LOGGER.info("forecasts %s: %d rows", day, len(rows))

    chunks = [existing[key] for key in sorted(existing)]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "base_url": settings.elexon_base_url,
        "chunks": chunks,
    }
    _write_json_atomic(manifest_path, manifest)
    return manifest


def _read_chunks(
    settings: Settings,
    dataset: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read all cached raw chunks for a dataset and return rows plus file hashes."""
    directory = settings.raw_dir / ("fuelhh" if dataset == "FUELHH" else "windfor")
    rows: list[dict[str, Any]] = []
    hashes: list[str] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise DataIntegrityError(f"{path} is not a JSON array")
        rows.extend(payload)
        hashes.append(sha256_file(path))
    return rows, hashes


def _frame_for_csv(frame: pd.DataFrame, timestamp_columns: tuple[str, ...]) -> pd.DataFrame:
    output = frame.copy()
    for column in timestamp_columns:
        output[column] = pd.to_datetime(output[column], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return output


def _write_frame_gz(path: Path, frame: pd.DataFrame, timestamp_columns: tuple[str, ...]) -> str:
    """Write a deterministic gzip CSV and return its SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    output = _frame_for_csv(frame, timestamp_columns)
    buffer = io.StringIO()
    output.to_csv(buffer, index=False, float_format="%.3f", lineterminator="\n")
    compressed = gzip.compress(buffer.getvalue().encode("utf-8"), compresslevel=9, mtime=0)
    _write_bytes_atomic(path, compressed)
    return hashlib.sha256(compressed).hexdigest()


def _stats_payload(stats: NormaliseStats) -> dict[str, int]:
    return {
        "input_rows": stats.input_rows,
        "kept_rows": stats.kept_rows,
        "non_wind_rows": stats.non_wind_rows,
        "duplicate_rows": stats.duplicate_rows,
        "nan_rows": stats.nan_rows,
    }


def build_snapshot(settings: Settings) -> dict[str, Any]:
    """Build processed files, quality report and manifest from cached raw data.

    Raises:
        DataIntegrityError: if no raw data exists or validation fails.
    """
    actual_rows, actual_hashes = _read_chunks(settings, "FUELHH")
    forecast_rows, forecast_hashes = _read_chunks(settings, "WINDFOR")
    if not actual_rows or not forecast_rows:
        raise DataIntegrityError("raw cache is empty; run the fetch command first")

    actual_result = normalise_actuals(actual_rows)
    forecast_result = normalise_forecasts(forecast_rows)
    quality = build_quality_report(
        settings,
        actual_result.frame,
        forecast_result.frame,
        actual_result.stats,
        forecast_result.stats,
    )

    processed_dir = settings.processed_dir
    actual_path = processed_dir / "actuals.csv.gz"
    forecast_path = processed_dir / "forecasts.csv.gz"
    actual_hash = _write_frame_gz(actual_path, actual_result.frame, ("start_time",))
    forecast_hash = _write_frame_gz(
        forecast_path,
        forecast_result.frame,
        ("start_time", "publish_time"),
    )
    write_quality_report(processed_dir / "quality_report.json", quality)

    raw_manifest = _read_fetch_manifest(settings.raw_dir / "manifest.json")
    fingerprint = hashlib.sha256(
        f"{actual_hash}{forecast_hash}{SCHEMA_VERSION}".encode()
    ).hexdigest()[:16]
    selected = select_decision_forecasts(forecast_result.frame, settings.default_cutoff)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "name": "Elexon BMRS Insights Solution",
            "base_url": settings.elexon_base_url,
            "datasets": ["FUELHH (fuelType=WIND)", "WINDFOR"],
            "documentation": {
                "fuelhh": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream",
                "windfor": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream",
            },
        },
        "window": {
            "actuals_start": settings.ingest_actuals_start,
            "actuals_end": settings.ingest_actuals_end,
            "forecast_publish_start": settings.ingest_forecast_publish_start,
            "forecast_publish_end": settings.ingest_forecast_publish_end,
            "scope_mode": settings.scope_mode,
            "scope_start": settings.scope_start.isoformat(),
            "scope_end": settings.scope_end.isoformat(),
            "delivery_dates": [day.isoformat() for day in settings.delivery_dates()],
        },
        "chunks": raw_manifest["chunks"],
        "processed": {
            "actuals": {
                "file": "actuals.csv.gz",
                "rows": int(len(actual_result.frame)),
                "sha256": actual_hash,
                "columns": ["start_time", "generation_mw"],
                "resolution_minutes": 30,
            },
            "forecasts": {
                "file": "forecasts.csv.gz",
                "rows": int(len(forecast_result.frame)),
                "sha256": forecast_hash,
                "columns": ["start_time", "publish_time", "generation_mw"],
                "resolution_minutes": 60,
            },
        },
        "normalisation": {
            "actuals": _stats_payload(actual_result.stats),
            "forecasts": _stats_payload(forecast_result.stats),
            "raw_chunk_hashes": {
                "actuals": actual_hashes,
                "forecasts": forecast_hashes,
            },
        },
        "policy": {
            "timezone": "UTC in storage, Europe/London for market-day boundaries",
            "sign_convention": SIGN_CONVENTION,
            "default_cutoff": format_cutoff_label(settings.default_cutoff),
            "selection_rule": "latest publish_time <= cutoff, inclusive",
            "forecast_resolution_note": (
                "Verified live: WINDFOR targets are hourly and published up to 8 times/day "
                "on the half-hour. FUELHH remains half-hourly; pairs are averaged for evaluation."
            ),
            "missing_data": "excluded and counted; never imputed",
        },
        "fingerprint": fingerprint,
        "selection_rows_default_cutoff": int(len(selected)),
    }
    _write_json_atomic(processed_dir / "manifest.json", manifest)
    LOGGER.info("wrote snapshot fingerprint %s", fingerprint)
    return manifest


def verify_snapshot(settings: Settings) -> dict[str, Any]:
    """Re-hash processed files and compare them with the manifest.

    Returns:
        A small verification summary.

    Raises:
        DataIntegrityError: if a hash or fingerprint does not match.
    """
    manifest_path = settings.processed_dir / "manifest.json"
    if not manifest_path.exists():
        raise DataIntegrityError("processed manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    processed = manifest.get("processed", {})
    checks: list[dict[str, object]] = []
    for key in ("actuals", "forecasts"):
        path = settings.processed_dir / processed[key]["file"]
        actual = sha256_file(path)
        expected = processed[key]["sha256"]
        checks.append(
            {
                "file": path.name,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            }
        )
    expected_fingerprint = hashlib.sha256(
        f"{processed['actuals']['sha256']}{processed['forecasts']['sha256']}{SCHEMA_VERSION}".encode()
    ).hexdigest()[:16]
    fingerprint_ok = manifest.get("fingerprint") == expected_fingerprint
    if not all(bool(check["ok"]) for check in checks) or not fingerprint_ok:
        raise DataIntegrityError("snapshot verification failed; rebuild with `make ingest`")
    return {
        "fingerprint": manifest.get("fingerprint"),
        "fingerprint_ok": fingerprint_ok,
        "files": checks,
    }

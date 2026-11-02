"""Normalisation of raw Elexon rows into typed frames."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class NormaliseStats:
    """Counts recorded in the quality report."""

    input_rows: int
    kept_rows: int
    non_wind_rows: int
    duplicate_rows: int
    nan_rows: int


@dataclass(frozen=True, slots=True)
class NormalisedFrame:
    """A normalised frame plus provenance counts."""

    frame: pd.DataFrame
    stats: NormaliseStats


def normalise_actuals(rows: list[dict[str, object]]) -> NormalisedFrame:
    """Normalise FUELHH rows to ``start_time`` and ``generation_mw``.

    Non-WIND fuel types are removed, timestamps are parsed as UTC, duplicate
    ``start_time`` rows keep the latest publication, and rows without a numeric
    generation value are dropped with a count. No missing value is imputed.

    Args:
        rows: Decoded JSON rows from FUELHH.

    Returns:
        A frame sorted by ``start_time`` plus normalisation counts.
    """
    frame = pd.DataFrame(rows)
    input_rows = len(frame)
    if frame.empty:
        return NormalisedFrame(
            frame=pd.DataFrame(
                {
                    "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
                    "generation_mw": pd.Series(dtype="float64"),
                }
            ),
            stats=NormaliseStats(0, 0, 0, 0, 0),
        )
    fuel = frame["fuelType"].astype(str).str.upper()
    non_wind = int((fuel != "WIND").sum())
    frame = frame.loc[fuel == "WIND"].copy()
    frame["start_time"] = pd.to_datetime(frame["startTime"], utc=True)
    frame["publish_time"] = pd.to_datetime(frame.get("publishTime"), utc=True, errors="coerce")
    frame["generation_mw"] = pd.to_numeric(frame["generation"], errors="coerce")
    before_nan = len(frame)
    frame = frame.loc[frame["generation_mw"].notna() & frame["start_time"].notna()]
    nan_rows = before_nan - len(frame)
    before_dedupe = len(frame)
    frame = (
        frame.sort_values(["start_time", "publish_time"], na_position="first")
        .drop_duplicates("start_time", keep="last")
        .reset_index(drop=True)
    )
    duplicate_rows = before_dedupe - len(frame)
    frame = frame.loc[:, ["start_time", "generation_mw"]].sort_values("start_time")
    stats = NormaliseStats(
        input_rows=input_rows,
        kept_rows=len(frame),
        non_wind_rows=non_wind,
        duplicate_rows=duplicate_rows,
        nan_rows=nan_rows,
    )
    return NormalisedFrame(frame=frame.reset_index(drop=True), stats=stats)


def normalise_forecasts(rows: list[dict[str, object]]) -> NormalisedFrame:
    """Normalise WINDFOR rows to hourly target and publication timestamps.

    Args:
        rows: Decoded JSON rows from WINDFOR.

    Returns:
        A frame sorted by ``(start_time, publish_time)`` plus counts.
    """
    frame = pd.DataFrame(rows)
    input_rows = len(frame)
    if frame.empty:
        return NormalisedFrame(
            frame=pd.DataFrame(
                {
                    "start_time": pd.Series(dtype="datetime64[ns, UTC]"),
                    "publish_time": pd.Series(dtype="datetime64[ns, UTC]"),
                    "generation_mw": pd.Series(dtype="float64"),
                }
            ),
            stats=NormaliseStats(0, 0, 0, 0, 0),
        )
    frame["start_time"] = pd.to_datetime(frame["startTime"], utc=True)
    frame["publish_time"] = pd.to_datetime(frame["publishTime"], utc=True)
    frame["generation_mw"] = pd.to_numeric(frame["generation"], errors="coerce")
    before_nan = len(frame)
    frame = frame.loc[
        frame["generation_mw"].notna() & frame["start_time"].notna() & frame["publish_time"].notna()
    ]
    nan_rows = before_nan - len(frame)
    before_dedupe = len(frame)
    frame = (
        frame.sort_values(["start_time", "publish_time"])
        .drop_duplicates(["start_time", "publish_time"], keep="last")
        .reset_index(drop=True)
    )
    duplicate_rows = before_dedupe - len(frame)
    frame = (
        frame.loc[:, ["start_time", "publish_time", "generation_mw"]]
        .sort_values(["start_time", "publish_time"])
        .reset_index(drop=True)
    )
    stats = NormaliseStats(
        input_rows=input_rows,
        kept_rows=len(frame),
        non_wind_rows=0,
        duplicate_rows=duplicate_rows,
        nan_rows=nan_rows,
    )
    return NormalisedFrame(frame=frame, stats=stats)

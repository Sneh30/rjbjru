"""Delivery-day, decision-cutoff and London-hour utilities.

All timestamps entering the domain are tz-aware UTC. London conversion happens only
for market-day boundaries and hour-of-day labels.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, cast

import pandas as pd

from .constants import LONDON
from .errors import ConfigError, DataIntegrityError


def london_delivery_date(start_time: pd.Series[Any]) -> pd.Series[Any]:
    """Return the London-local calendar date of each UTC timestamp, normalised.

    Args:
        start_time: UTC ``datetime64[ns, UTC]`` series.

    Returns:
        Naive, midnight-normalised timestamps representing London dates.
    """
    local = start_time.dt.tz_convert(LONDON)
    return local.dt.tz_localize(None).dt.normalize()


def decision_cutoff_utc(start_time: pd.Series[Any], cutoff_local: time) -> pd.Series[Any]:
    """Return the decision cutoff instant (UTC) for each target half-hour/hour.

    The cutoff for delivery date ``D`` is ``D - 1 day`` at ``cutoff_local`` in
    Europe/London. DST is handled explicitly; a nonexistent local time is shifted
    forward and an ambiguous local time raises.

    Args:
        start_time: UTC target timestamps.
        cutoff_local: Wall-clock cutoff on the previous London day.

    Returns:
        UTC cutoff instants aligned to ``start_time``.

    Raises:
        ConfigError: if the configured cutoff falls in an ambiguous DST interval.
    """
    day = london_delivery_date(start_time)
    offset = pd.Timedelta(hours=cutoff_local.hour, minutes=cutoff_local.minute)
    naive = day - pd.Timedelta(days=1) + offset
    local = naive.dt.tz_localize(LONDON, nonexistent="shift_forward", ambiguous="NaT")
    if bool(local.isna().any()):
        raise ConfigError("Decision cutoff is ambiguous at a DST boundary")
    return local.dt.tz_convert("UTC")


def cutoff_for_delivery_date(delivery_date: date, cutoff_local: time) -> datetime:
    """Return the cutoff instant (UTC) for one London delivery date.

    Args:
        delivery_date: London-local delivery date.
        cutoff_local: Wall-clock cutoff on the previous day.

    Returns:
        A tz-aware UTC datetime.
    """
    target = pd.Series([pd.Timestamp(delivery_date, tz="UTC")])
    cutoff = decision_cutoff_utc(target, cutoff_local).iloc[0]
    return cast(datetime, cutoff.to_pydatetime())


def london_hour(start_time: pd.Series[Any]) -> pd.Series[Any]:
    """Return the London-local hour (0-23) of each UTC timestamp."""
    return start_time.dt.tz_convert(LONDON).dt.hour


def format_cutoff_label(cutoff_local: time) -> str:
    """Return ``HH:MM`` for a cutoff time."""
    return f"{cutoff_local.hour:02d}:{cutoff_local.minute:02d}"


def parse_cutoff(value: str) -> time:
    """Parse and validate an ``HH:MM`` cutoff.

    Args:
        value: A 24-hour clock string.

    Returns:
        The parsed time.

    Raises:
        ValueError: if the value is not ``HH:MM`` or is out of range.
    """
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("cutoff must be HH:MM")
    hour_text, minute_text = parts
    if len(hour_text) != 2 or len(minute_text) != 2:
        raise ValueError("cutoff must be HH:MM with two-digit fields")
    if not hour_text.isdigit() or not minute_text.isdigit():
        raise ValueError("cutoff must contain digits only")
    hour, minute = int(hour_text), int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("cutoff must be between 00:00 and 23:59")
    return time(hour, minute)


def delivery_dates_between(start: date, end: date) -> list[date]:
    """Return all dates from ``start`` to ``end`` inclusive.

    Raises:
        DataIntegrityError: if ``start > end``.
    """
    if start > end:
        raise DataIntegrityError("start date must be on or before end date")
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days

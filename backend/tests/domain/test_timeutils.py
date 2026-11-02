"""Cutoff, London-day and DST boundary tests."""

from __future__ import annotations

from datetime import date, time

import pandas as pd
import pytest

from app.domain.errors import ConfigError, DataIntegrityError
from app.domain.timeutils import (
    cutoff_for_delivery_date,
    decision_cutoff_utc,
    delivery_dates_between,
    format_cutoff_label,
    london_delivery_date,
    london_hour,
    parse_cutoff,
)


def _series(*values: str) -> pd.Series[object]:
    return pd.to_datetime(pd.Series(list(values)), utc=True)


def test_london_delivery_date_uses_the_local_calendar_day() -> None:
    # 23:30 UTC in January is 23:30 London, still the same day.
    assert london_delivery_date(_series("2026-01-15T23:30:00Z")).dt.date.tolist() == [
        date(2026, 1, 15)
    ]
    # 23:30 UTC in June is 00:30 BST on the following day.
    assert london_delivery_date(_series("2026-06-01T23:30:00Z")).dt.date.tolist() == [
        date(2026, 6, 2)
    ]
    # 00:30 UTC in June is 01:30 BST, same local day.
    assert london_delivery_date(_series("2026-06-02T00:30:00Z")).dt.date.tolist() == [
        date(2026, 6, 2)
    ]


def test_cutoff_for_delivery_date_in_winter_is_utc() -> None:
    cutoff = cutoff_for_delivery_date(date(2026, 1, 15), time(9, 0))
    assert cutoff.isoformat() == "2026-01-14T09:00:00+00:00"


def test_cutoff_for_delivery_date_after_spring_dst_change_uses_bst() -> None:
    # UK DST starts 2025-03-30 at 01:00 UTC, so 09:00 London is 08:00 UTC.
    cutoff = cutoff_for_delivery_date(date(2025, 3, 31), time(9, 0))
    assert cutoff.isoformat() == "2025-03-30T08:00:00+00:00"


def test_cutoff_for_delivery_date_after_autumn_dst_change_uses_gmt() -> None:
    # UK DST ends 2025-10-26 at 02:00 BST, so 09:00 London is 09:00 UTC.
    cutoff = cutoff_for_delivery_date(date(2025, 10, 27), time(9, 0))
    assert cutoff.isoformat() == "2025-10-26T09:00:00+00:00"


def test_nonexistent_local_cutoff_shifts_forward() -> None:
    # 01:30 does not exist on 2025-03-30; pandas shifts to 02:00 BST == 01:00 UTC.
    cutoff = cutoff_for_delivery_date(date(2025, 3, 31), time(1, 30))
    assert cutoff.isoformat() == "2025-03-30T01:00:00+00:00"


def test_ambiguous_local_cutoff_raises_config_error() -> None:
    # 01:30 occurs twice on 2025-10-26.
    with pytest.raises(ConfigError, match="ambiguous"):
        cutoff_for_delivery_date(date(2025, 10, 27), time(1, 30))


def test_decision_cutoff_is_computed_per_target_delivery_day() -> None:
    targets = _series("2026-01-15T00:00:00Z", "2026-01-15T23:00:00Z", "2026-01-16T00:00:00Z")
    cutoffs = decision_cutoff_utc(targets, time(9, 0))
    assert cutoffs.dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist() == [
        "2026-01-14T09:00:00Z",
        "2026-01-14T09:00:00Z",
        "2026-01-15T09:00:00Z",
    ]


def test_london_hour_uses_local_time() -> None:
    hours = london_hour(_series("2026-06-01T23:30:00Z", "2026-06-02T00:30:00Z"))
    assert hours.tolist() == [0, 1]


def test_format_cutoff_label_pads_to_two_digits() -> None:
    assert format_cutoff_label(time(9, 0)) == "09:00"
    assert format_cutoff_label(time(0, 5)) == "00:05"
    assert format_cutoff_label(time(23, 59)) == "23:59"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:00", time(0, 0)),
        ("09:00", time(9, 0)),
        ("09:20", time(9, 20)),
        ("23:59", time(23, 59)),
    ],
)
def test_parse_cutoff_accepts_valid_values(text: str, expected: time) -> None:
    assert parse_cutoff(text) == expected


@pytest.mark.parametrize(
    "text",
    ["9:00", "09:0", "24:00", "09:60", "aa:bb", "09-00", "", "09:00:00", "09:00 "],
)
def test_parse_cutoff_rejects_invalid_values(text: str) -> None:
    with pytest.raises(ValueError, match="cutoff"):
        parse_cutoff(text)


def test_delivery_dates_between_is_inclusive() -> None:
    assert delivery_dates_between(date(2026, 1, 1), date(2026, 1, 3)) == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert delivery_dates_between(date(2026, 1, 1), date(2026, 1, 1)) == [date(2026, 1, 1)]


def test_delivery_dates_between_rejects_reversed_range() -> None:
    with pytest.raises(DataIntegrityError, match="before"):
        delivery_dates_between(date(2026, 1, 2), date(2026, 1, 1))

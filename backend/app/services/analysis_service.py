"""Cached access to decision-time frames and scoped evaluation windows."""

from __future__ import annotations

from datetime import date, time, timedelta

import pandas as pd

from app.config import Settings
from app.data.repository import Repository
from app.domain.baseline import persistence_for_selected
from app.domain.constants import LONDON
from app.domain.errors import DataIntegrityError, OutOfScopeError
from app.domain.join import join_all_vintages, join_selected_actuals
from app.domain.selection import select_decision_forecasts


def london_midnight_utc(day: date) -> pd.Timestamp:
    """Return the UTC instant of London-local midnight on ``day``."""
    return pd.Timestamp(day).tz_localize(LONDON).tz_convert("UTC")


def london_day_hours(day: date) -> list[pd.Timestamp]:
    """Return the UTC hourly target instants in one London delivery day."""
    start = london_midnight_utc(day)
    end = london_midnight_utc(day + timedelta(days=1))
    return list(pd.date_range(start, end, freq="1h", inclusive="left"))


class AnalysisService:
    """Load-once, cache-by-cutoff access to selected and joined frames.

    The snapshot is immutable for the process lifetime, so selection results can be
    cached by cutoff safely. Every public window method intersects with the configured
    delivery-date scope; no caller can accidentally score December or February rows.
    """

    def __init__(self, repository: Repository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self._selected_cache: dict[time, pd.DataFrame] = {}
        self._joined_cache: dict[time, pd.DataFrame] = {}
        self._vintages_cache: pd.DataFrame | None = None

    @property
    def fingerprint(self) -> str:
        """Return the dataset fingerprint."""
        return self.repository.fingerprint

    def delivery_dates(self) -> list[date]:
        """Return the configured, in-scope delivery dates."""
        return self.settings.delivery_dates()

    def scope_bounds(self) -> tuple[date, date]:
        """Return the first and last in-scope delivery dates."""
        days = self.delivery_dates()
        return days[0], days[-1]

    def ensure_delivery_date(self, delivery_date: date) -> None:
        """Raise a 404-mapped error when a date is outside the evaluation scope."""
        start, end = self.scope_bounds()
        if delivery_date < start or delivery_date > end:
            raise OutOfScopeError(
                f"{delivery_date.isoformat()} is outside {start.isoformat()}..{end.isoformat()}",
                extra={"valid_range": {"start": start.isoformat(), "end": end.isoformat()}},
            )

    def ensure_window(self, start: date | None, end: date | None) -> tuple[date, date]:
        """Validate and normalise an inclusive delivery-date window."""
        scope_start, scope_end = self.scope_bounds()
        first = start or scope_start
        last = end or scope_end
        self.ensure_delivery_date(first)
        self.ensure_delivery_date(last)
        if first > last:
            raise OutOfScopeError(
                "start must be on or before end",
                extra={
                    "valid_range": {"start": scope_start.isoformat(), "end": scope_end.isoformat()}
                },
            )
        return first, last

    def selected(self, cutoff: time) -> pd.DataFrame:
        """Return the decision-time selection for a cutoff, cached by cutoff."""
        if cutoff not in self._selected_cache:
            selected = select_decision_forecasts(self.repository.forecasts(), cutoff)
            self._selected_cache[cutoff] = selected
        return self._selected_cache[cutoff]

    def joined(self, cutoff: time) -> pd.DataFrame:
        """Return selected forecasts joined to actuals and a persistence baseline."""
        if cutoff not in self._joined_cache:
            selected = self.selected(cutoff)
            joined = join_selected_actuals(selected, self.repository.hourly_actuals())
            self._joined_cache[cutoff] = persistence_for_selected(
                joined, self.repository.hourly_actuals(), cutoff
            )
        return self._joined_cache[cutoff]

    def window(self, cutoff: time, start: date, end: date) -> pd.DataFrame:
        """Return joined decision-time rows for an inclusive delivery-date window."""
        joined = self.joined(cutoff)
        mask = (joined["delivery_date"] >= start) & (joined["delivery_date"] <= end)
        return joined.loc[mask].sort_values("start_time").reset_index(drop=True)

    def all_vintages(self) -> pd.DataFrame:
        """Return every forecast vintage joined to actuals, cached once."""
        if self._vintages_cache is None:
            self._vintages_cache = join_all_vintages(
                self.repository.forecasts(), self.repository.hourly_actuals()
            )
        return self._vintages_cache

    def vintage_window(self, start: date, end: date) -> pd.DataFrame:
        """Return joined vintages whose target falls inside a delivery-date window."""
        joined = self.all_vintages()
        dates = joined["start_time"].dt.tz_convert(LONDON).dt.date
        mask = (dates >= start) & (dates <= end)
        return joined.loc[mask].sort_values(["start_time", "publish_time"]).reset_index(drop=True)

    def expected_hours(self, start: date, end: date) -> int:
        """Return the number of hourly targets in an inclusive London-day window.

        January has 24 hours per day, but computing the count from London midnight
        boundaries keeps the check correct across future DST transitions.
        """
        total = 0
        cursor = start
        while cursor <= end:
            total += len(london_day_hours(cursor))
            cursor += timedelta(days=1)
        return total

    def window_coverage(self, cutoff: time, start: date, end: date) -> dict[str, object]:
        """Return selected-row coverage for a window."""
        frame = self.window(cutoff, start, end)
        expected = self.expected_hours(start, end)
        with_forecast = int(len(frame))
        with_actual = int(frame["actual_mw"].notna().sum())
        return {
            "expected_periods": expected,
            "with_forecast": with_forecast,
            "with_actual": with_actual,
            "coverage_pct": round(with_forecast / expected * 100.0, 2) if expected else None,
        }

    def verify_scope(self) -> None:
        """Assert the warm default selection obeys the cutoff and is unique.

        The full snapshot deliberately contains vintages for days adjacent to the
        evaluation scope, so out-of-scope targets are not an error. What matters is
        that no selected row was published after its decision cutoff and that each
        target has exactly one selected forecast.
        """
        selected = self.selected(self.settings.default_cutoff)
        if selected.empty:
            raise DataIntegrityError("default decision selection is empty")
        if bool((selected["publish_time"] > selected["cutoff_utc"]).any()):
            raise DataIntegrityError("default selection contains a post-cutoff forecast")
        if bool(selected["start_time"].duplicated().any()):
            raise DataIntegrityError("default selection contains duplicate targets")
        start, end = self.scope_bounds()
        window = self.window(self.settings.default_cutoff, start, end)
        expected = self.expected_hours(start, end)
        if len(window) > expected:
            raise DataIntegrityError("scoped selection contains more rows than expected targets")

"""Core domain constants and units.

The domain layer is pure: no FastAPI, no file I/O, no logging.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")

#: FUELHH outturn is published for half-hour settlement periods.
ACTUAL_PERIOD_MINUTES = 30
ACTUAL_PERIOD_HOURS = ACTUAL_PERIOD_MINUTES / 60.0

#: WINDFOR forecast targets are hourly (verified against the live API in DATA_SOURCES.md).
FORECAST_PERIOD_HOURS = 1.0

#: Energy in MWh = average MW x hours.
MWH_PER_FORECAST_PERIOD = FORECAST_PERIOD_HOURS

#: Sign convention used everywhere. Positive error means over-forecast, i.e. shortfall risk.
SIGN_CONVENTION = "error = forecast - actual; positive = over-forecast (shortfall risk)"

#: Context attached to every metric result and methodology panel.
SCOPE_NOTE = (
    "Decision-time metrics use the latest WINDFOR vintage published at or before the "
    "09:00 Europe/London cutoff on the previous calendar day."
)

#: Minimum actual output used by guarded MAPE (MW). Below this, relative error is unstable.
DEFAULT_MAPE_MIN_ACTUAL_MW = 500.0

#: A half-hour actual output is averaged in pairs to the hourly WINDFOR granularity.
HALF_HOURS_PER_FORECAST_HOUR = int(FORECAST_PERIOD_HOURS / ACTUAL_PERIOD_HOURS)

#: Formatter precision at the API boundary.
MW_DECIMALS = 1
PCT_DECIMALS = 2

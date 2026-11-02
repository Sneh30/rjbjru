"""Pydantic request and response contracts for the versioned API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

CutoffStr = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]


class ApiModel(BaseModel):
    """Base response model that rejects accidental undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class QueryModel(BaseModel):
    """Base query model: unknown query parameters are a 422, as documented."""

    model_config = ConfigDict(extra="forbid")


class WindowQuery(QueryModel):
    """Inclusive delivery-date window."""

    start: date | None = Field(default=None, description="First delivery date, inclusive")
    end: date | None = Field(default=None, description="Last delivery date, inclusive")


class DateWindowQuery(WindowQuery):
    """Shared inclusive delivery-date window and cutoff selector."""

    cutoff: CutoffStr | None = Field(
        default=None,
        description="Decision cutoff HH:MM Europe/London on D-1; defaults to configured 09:00",
    )


class DecisionQuery(QueryModel):
    """Decision-view parameters."""

    delivery_date: date = Field(description="London delivery date in scope")
    cutoff: CutoffStr | None = Field(
        default=None,
        description="Decision cutoff HH:MM Europe/London on D-1; defaults to configured 09:00",
    )
    include_actuals: bool = Field(
        default=False,
        description="Attach hindsight actuals and errors. Decision-time data only when false.",
    )


class RevisionsQuery(QueryModel):
    """Revision parameters: target instant or delivery date plus hourly period."""

    target_time: datetime | None = Field(
        default=None, description="UTC target instant, on the hour"
    )
    delivery_date: date | None = Field(default=None, description="London delivery date alternative")
    period: int | None = Field(default=None, ge=1, le=24, description="One-based London hour")
    cutoff: CutoffStr | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> RevisionsQuery:
        by_time = self.target_time is not None
        by_period = self.delivery_date is not None and self.period is not None
        if by_time == by_period:
            raise ValueError("provide either target_time or delivery_date plus period")
        if self.delivery_date is not None and self.period is None:
            raise ValueError("period is required when delivery_date is supplied")
        if self.period is not None and self.delivery_date is None:
            raise ValueError("delivery_date is required when period is supplied")
        return self


class ByLevelQuery(DateWindowQuery):
    """Wind-level breakdown parameters."""

    basis: Literal["actual", "forecast"] = "actual"
    bins: int = Field(default=5, ge=3, le=10)


class DistributionQuery(DateWindowQuery):
    """Distribution parameters."""

    bins: int = Field(default=20, ge=3, le=50)


class WorstQuery(DateWindowQuery):
    """Worst-period parameters."""

    n: int = Field(default=5, ge=1, le=20)
    metric: Literal["mae", "rmse", "bias", "shortfall_p90"] = "mae"


class BufferQuery(DateWindowQuery):
    """Risk-buffer parameters."""

    levels: str = Field(default="0.5,0.75,0.9,0.95", description="Comma-separated probabilities")

    @field_validator("levels")
    @classmethod
    def _validate_levels(cls, value: str) -> str:
        try:
            levels = [float(part.strip()) for part in value.split(",") if part.strip()]
        except ValueError as exc:
            raise ValueError("levels must be comma-separated numbers") from exc
        if not levels or len(levels) > 8:
            raise ValueError("provide between 1 and 8 levels")
        if any(not 0 < level < 1 for level in levels):
            raise ValueError("every level must be strictly between 0 and 1")
        return ",".join(f"{level:g}" for level in levels)

    @property
    def parsed_levels(self) -> tuple[float, ...]:
        """Return validated probabilities as a tuple."""
        return tuple(float(part) for part in self.levels.split(","))


class BacktestQuery(QueryModel):
    """Walk-forward back-test parameters."""

    start: date | None = None
    end: date | None = None
    cutoff: CutoffStr | None = None
    level: float = Field(default=0.9, gt=0, lt=1)
    min_history_days: int = Field(default=7, ge=1, le=31)


class ExportQuery(QueryModel):
    """CSV export selectors."""

    table: Literal["daily", "by-horizon", "by-hour", "by-level", "cutoff-sensitivity"] = "daily"
    start: date | None = None
    end: date | None = None
    cutoff: CutoffStr | None = None
    basis: Literal["actual", "forecast"] = "actual"
    bins: int = Field(default=5, ge=3, le=10)


class CutoffOut(ApiModel):
    """Resolved cutoff in UTC and London local time."""

    local: str | None
    utc: str | None
    time: str
    timezone: str


class CoverageOut(ApiModel):
    """Forecast and actual coverage for a day or window."""

    expected_periods: int
    with_forecast: int
    with_actual: int
    missing_forecast_periods: list[str] = Field(default_factory=list)
    missing_actual_periods: list[str] = Field(default_factory=list)
    coverage_pct: float | None = None


class HorizonRange(ApiModel):
    """Summary of forecast horizons in a frame."""

    min: float | None
    mean: float | None = None
    max: float | None


class MetricsOut(ApiModel):
    """Buyer-focused forecast error metrics. MW fields are MW; rates are percent."""

    n: int
    n_missing_actual: int
    n_missing_forecast: int | None = None
    mean_actual_mw: float | None
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    nmae_pct: float | None
    wape_pct: float | None
    mape_pct: float | None
    mape_n: int
    p50_abs_mw: float | None
    p90_abs_mw: float | None
    p95_abs_mw: float | None
    p5_err_mw: float | None
    p50_err_mw: float | None
    p95_err_mw: float | None
    over_forecast_share: float | None
    shortfall_mean_mw: float | None
    shortfall_p90_mw: float | None
    shortfall_p95_mw: float | None
    shortfall_max_mw: float | None
    correlation: float | None


class DecisionPointOut(ApiModel):
    """One hourly decision-time point, with optional hindsight fields."""

    start_time: str | None
    local_time: str | None
    forecast_mw: float | None
    publish_time: str | None
    horizon_h: float
    actual_mw: float | None = None
    error_mw: float | None = None
    shortfall_mw: float | None = None


class DecisionSummaryOut(ApiModel):
    """Day-level forecast shape and vintage summary."""

    mean_mw: float | None
    peak_mw: float | None
    peak_time: str | None
    min_mw: float | None
    min_time: str | None
    energy_mwh: float | None
    max_ramp_1h_mw: float | None
    max_ramp_3h_mw: float | None
    latest_publish_time: str | None
    earliest_publish_time: str | None
    horizon_h: HorizonRange


class DecisionViewOut(ApiModel):
    """Decision desk response."""

    delivery_date: str
    delivery_date_local: str
    cutoff: CutoffOut
    resolution_minutes: int
    points: list[DecisionPointOut]
    summary: DecisionSummaryOut
    coverage: CoverageOut
    day_metrics: MetricsOut | None = None


class RevisionVintageOut(ApiModel):
    """One forecast vintage for a target."""

    publish_time: str | None
    publish_time_local: str | None
    horizon_h: float
    forecast_mw: float | None
    eligible: bool
    selected: bool


class RevisionRangeOut(ApiModel):
    """Spread of eligible forecasts for the target."""

    min: float | None
    max: float | None
    spread: float | None


class RevisionsOut(ApiModel):
    """Revision explorer response."""

    target_time: str | None
    target_time_local: str
    delivery_date: str
    cutoff: CutoffOut
    vintages: list[RevisionVintageOut]
    selected_publish_time: str | None
    selected_forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    revision_range_mw: RevisionRangeOut
    shown_until: str | None
    lookahead_hours: int
    eligibility_note: str
    resolution_minutes: int


class WindowOut(ApiModel):
    """Evaluated date window."""

    start: str
    end: str
    delivery_days: int
    expected_periods: int | None = None


class BaselineOut(ApiModel):
    """Persistence baseline on the common evaluated rows."""

    name: str
    mae_mw: float | None
    forecast_mae_mw: float | None
    skill: float | None
    n: int


class AccuracySummaryOut(ApiModel):
    """Accuracy scorecard response."""

    window: WindowOut
    cutoff: str
    metrics: MetricsOut
    baseline: BaselineOut
    horizon_h: HorizonRange
    coverage: CoverageOut


class DailyRowOut(ApiModel):
    """One daily accuracy row."""

    delivery_date: str
    n: int
    mae_mw: float | None
    bias_mw: float | None
    rmse_mw: float | None
    nmae_pct: float | None
    max_abs_mw: float | None
    max_abs_time: str | None
    shortfall_p90_mw: float | None
    mean_actual_mw: float | None


class DailyOut(ApiModel):
    """Daily accuracy series."""

    start: str
    end: str
    days: list[DailyRowOut]


class HorizonBucketOut(ApiModel):
    """Metrics for one forecast-horizon bucket; ``to_h`` is null for the open bucket."""

    from_h: float
    to_h: float | None
    label: str
    n: int
    nmae_pct: float | None
    mae_mw: float | None
    bias_mw: float | None
    rmse_mw: float | None


class HorizonBandOut(ApiModel):
    """Horizon range of the selected decision-time forecasts."""

    min: float
    max: float


class HorizonOut(ApiModel):
    """Error growth by horizon across all vintages."""

    buckets: list[HorizonBucketOut]
    decision_band_h: HorizonBandOut | None
    dropped_negative_horizon: int
    n_vintage_rows: int


class HourRowOut(ApiModel):
    """One London hour of day."""

    hour: int
    label: str
    n: int
    mae_mw: float | None
    bias_mw: float | None
    rmse_mw: float | None
    shortfall_p90_mw: float | None
    mean_actual_mw: float | None


class HoursOut(ApiModel):
    """Error metrics by London hour."""

    hours: list[HourRowOut]


class LevelBinOut(ApiModel):
    """One wind-output quantile bin."""

    label: str
    from_mw: float | None
    to_mw: float | None
    n: int
    mae_mw: float | None
    bias_mw: float | None
    nmae_pct: float | None


class LevelOut(ApiModel):
    """Error metrics by wind level."""

    basis: str
    bins: list[LevelBinOut]


class HistogramBinOut(ApiModel):
    """One signed-error histogram bin."""

    from_mw: float | None
    to_mw: float | None
    count: int


class QuantilesOut(ApiModel):
    """Quantiles shown beside the histogram."""

    p5: float | None
    p50: float | None
    p95: float | None
    shortfall_p90: float | None


class ScatterPointOut(ApiModel):
    """One forecast/actual scatter point."""

    forecast_mw: float | None
    actual_mw: float | None
    start_time: str | None


class DistributionOut(ApiModel):
    """Signed-error distribution and deterministic scatter sample."""

    histogram: list[HistogramBinOut]
    quantiles: QuantilesOut
    scatter: list[ScatterPointOut]
    scatter_total: int
    scatter_limit: int


class WorstDayOut(ApiModel):
    """A worst-ranked delivery day."""

    delivery_date: str
    n: int
    mae_mw: float | None
    bias_mw: float | None
    rmse_mw: float | None
    max_abs_mw: float | None
    max_abs_time: str | None


class WorstPeriodOut(ApiModel):
    """A worst-ranked target period."""

    start_time: str | None
    delivery_date: str
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None


class WorstOut(ApiModel):
    """Worst days and periods."""

    metric: str
    days: list[WorstDayOut]
    periods: list[WorstPeriodOut]


class SensitivityRowOut(ApiModel):
    """Metrics at one cutoff."""

    cutoff: str
    n: int
    mae_mw: float | None
    bias_mw: float | None
    shortfall_p90_mw: float | None
    mean_horizon_h: float | None
    coverage_pct: float | None


class SensitivityOut(ApiModel):
    """Cutoff sensitivity response."""

    rows: list[SensitivityRowOut]


class BufferPointOut(ApiModel):
    """Empirical signed-error quantile in MW."""

    level: float
    buffer_mw: float | None


class HourBufferOut(ApiModel):
    """Buffers for one London hour."""

    hour: int
    buffers: list[BufferPointOut]


class BufferOut(ApiModel):
    """In-sample risk buffers."""

    basis: str
    window: dict[str, str]
    overall: list[BufferPointOut]
    by_hour: list[HourBufferOut]
    n: int
    caveat: str


class BacktestDayOut(ApiModel):
    """Coverage for one back-tested day."""

    delivery_date: str
    buffer_mw: float | None
    coverage: float | None
    n: int
    breaches: int


class BacktestOut(ApiModel):
    """Walk-forward back-test response."""

    basis: str
    window: dict[str, str]
    level: float
    outcome_lag_days: int
    min_history_days: int
    evaluated_days: int
    skipped_days: list[str]
    coverage: float | None
    target: float
    mean_buffer_mw: float | None
    days_with_breach_share: float | None
    daily: list[BacktestDayOut]
    caveat: str


class HealthOut(ApiModel):
    """Liveness and snapshot identity."""

    status: str
    version: str
    data_fingerprint: str
    actual_rows: int
    forecast_rows: int
    timezone: str


class MetaOut(ApiModel):
    """Scope, defaults, provenance and method metadata."""

    product: str
    version: str
    timezone: str
    default_cutoff: str
    cutoff_grid: list[str]
    scope: dict[str, Any]
    available_delivery_dates: list[str]
    horizon_buckets_h: list[float]
    constants: dict[str, Any]
    data: dict[str, Any]
    methodology: dict[str, Any]
    ai_disclosure: str


class ProblemOut(ApiModel):
    """RFC 7807 problem document."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: list[dict[str, Any]] | None = None
    valid_range: dict[str, str] | None = None

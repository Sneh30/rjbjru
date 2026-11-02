/**
 * Typed transport contracts for the WindLens API.
 *
 * These mirror `backend/app/api/schemas.py`. `make types` regenerates the OpenAPI
 * document; this hand-written layer keeps the UI decoupled from generated names and
 * gives every chart component a precise shape.
 */

export type Cutoff = {
  local: string | null;
  utc: string | null;
  time: string;
  timezone: string;
};

export type Coverage = {
  expected_periods: number;
  with_forecast: number;
  with_actual: number;
  missing_forecast_periods: string[];
  missing_actual_periods: string[];
  coverage_pct?: number | null;
};

export type HorizonRange = {
  min: number | null;
  mean: number | null;
  max: number | null;
};

export type Metrics = {
  n: number;
  n_missing_actual: number;
  n_missing_forecast: number | null;
  mean_actual_mw: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  nmae_pct: number | null;
  wape_pct: number | null;
  mape_pct: number | null;
  mape_n: number;
  p50_abs_mw: number | null;
  p90_abs_mw: number | null;
  p95_abs_mw: number | null;
  p5_err_mw: number | null;
  p50_err_mw: number | null;
  p95_err_mw: number | null;
  over_forecast_share: number | null;
  shortfall_mean_mw: number | null;
  shortfall_p90_mw: number | null;
  shortfall_p95_mw: number | null;
  shortfall_max_mw: number | null;
  correlation: number | null;
};

export type DecisionPoint = {
  start_time: string | null;
  local_time: string | null;
  forecast_mw: number | null;
  publish_time: string | null;
  horizon_h: number;
  actual_mw?: number | null;
  error_mw?: number | null;
  shortfall_mw?: number | null;
};

export type DecisionSummary = {
  mean_mw: number | null;
  peak_mw: number | null;
  peak_time: string | null;
  min_mw: number | null;
  min_time: string | null;
  energy_mwh: number | null;
  max_ramp_1h_mw: number | null;
  max_ramp_3h_mw: number | null;
  latest_publish_time: string | null;
  earliest_publish_time: string | null;
  horizon_h: HorizonRange;
};

export type DecisionView = {
  delivery_date: string;
  delivery_date_local: string;
  cutoff: Cutoff;
  resolution_minutes: number;
  points: DecisionPoint[];
  summary: DecisionSummary;
  coverage: Coverage;
  day_metrics?: Metrics | null;
};

export type Baseline = {
  name: string;
  mae_mw: number | null;
  forecast_mae_mw: number | null;
  skill: number | null;
  n: number;
};

export type AccuracySummary = {
  window: { start: string; end: string; delivery_days: number; expected_periods?: number | null };
  cutoff: string;
  metrics: Metrics;
  baseline: Baseline;
  horizon_h: HorizonRange;
  coverage: Coverage;
};

export type DailyRow = {
  delivery_date: string;
  n: number;
  mae_mw: number | null;
  bias_mw: number | null;
  rmse_mw: number | null;
  nmae_pct: number | null;
  max_abs_mw: number | null;
  max_abs_time: string | null;
  shortfall_p90_mw: number | null;
  mean_actual_mw: number | null;
};

export type DailyResponse = { start: string; end: string; days: DailyRow[] };

export type HorizonBucket = {
  from_h: number;
  to_h: number | null;
  label: string;
  n: number;
  nmae_pct: number | null;
  mae_mw: number | null;
  bias_mw: number | null;
  rmse_mw: number | null;
};

export type HorizonResponse = {
  buckets: HorizonBucket[];
  decision_band_h: { min: number; max: number } | null;
  dropped_negative_horizon: number;
  n_vintage_rows: number;
};

export type HourRow = {
  hour: number;
  label: string;
  n: number;
  mae_mw: number | null;
  bias_mw: number | null;
  rmse_mw: number | null;
  shortfall_p90_mw: number | null;
  mean_actual_mw: number | null;
};

export type HoursResponse = { hours: HourRow[] };

export type LevelBin = {
  label: string;
  from_mw: number | null;
  to_mw: number | null;
  n: number;
  mae_mw: number | null;
  bias_mw: number | null;
  nmae_pct: number | null;
};

export type LevelResponse = { basis: "actual" | "forecast"; bins: LevelBin[] };

export type HistogramBin = { from_mw: number | null; to_mw: number | null; count: number };

export type ScatterDatum = {
  forecast_mw: number | null;
  actual_mw: number | null;
  start_time: string | null;
};

export type DistributionResponse = {
  histogram: HistogramBin[];
  quantiles: { p5: number | null; p50: number | null; p95: number | null; shortfall_p90: number | null };
  scatter: ScatterDatum[];
  scatter_total: number;
  scatter_limit: number;
};

export type WorstDay = {
  delivery_date: string;
  n: number;
  mae_mw: number | null;
  bias_mw: number | null;
  rmse_mw: number | null;
  max_abs_mw: number | null;
  max_abs_time: string | null;
};

export type WorstPeriod = {
  start_time: string | null;
  delivery_date: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
};

export type WorstResponse = { metric: string; days: WorstDay[]; periods: WorstPeriod[] };

export type SensitivityRow = {
  cutoff: string;
  n: number;
  mae_mw: number | null;
  bias_mw: number | null;
  shortfall_p90_mw: number | null;
  mean_horizon_h: number | null;
  coverage_pct?: number | null;
};

export type SensitivityResponse = { rows: SensitivityRow[] };

export type BufferPoint = { level: number; buffer_mw: number | null };

export type BufferResponse = {
  basis: string;
  window: { start: string; end: string };
  overall: BufferPoint[];
  by_hour: { hour: number; buffers: BufferPoint[] }[];
  n: number;
  caveat: string;
};

export type BacktestDay = {
  delivery_date: string;
  buffer_mw: number | null;
  coverage: number | null;
  n: number;
  breaches: number;
};

export type BacktestResponse = {
  basis: string;
  window: { start: string; end: string };
  level: number;
  outcome_lag_days: number;
  min_history_days: number;
  evaluated_days: number;
  skipped_days: string[];
  coverage: number | null;
  target: number;
  mean_buffer_mw: number | null;
  days_with_breach_share: number | null;
  daily: BacktestDay[];
  caveat: string;
};

export type RevisionVintage = {
  publish_time: string | null;
  publish_time_local: string | null;
  horizon_h: number;
  forecast_mw: number | null;
  eligible: boolean;
  selected: boolean;
};

export type RevisionsResponse = {
  target_time: string | null;
  target_time_local: string;
  delivery_date: string;
  cutoff: Cutoff;
  vintages: RevisionVintage[];
  selected_publish_time: string | null;
  selected_forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
  revision_range_mw: { min: number | null; max: number | null; spread: number | null };
  shown_until: string | null;
  lookahead_hours: number;
  eligibility_note: string;
  resolution_minutes: number;
};

export type Meta = {
  product: string;
  version: string;
  timezone: string;
  default_cutoff: string;
  cutoff_grid: string[];
  scope: {
    mode: string;
    decision_dates: { start: string; end: string };
    delivery_dates: { start: string; end: string };
    delivery_days: number;
  };
  available_delivery_dates: string[];
  horizon_buckets_h: number[];
  constants: {
    period_minutes: number;
    forecast_period_minutes: number;
    sign_convention: string;
    mape_min_actual_mw: number;
    min_history_days: number;
    outcome_lag_days: number;
  };
  data: {
    fingerprint: string;
    generated_at: string | null;
    source: string;
    datasets: string[];
    manifest_source: Record<string, unknown>;
    coverage: Record<string, number | string | null>;
    quality: Record<string, number | null>;
  };
  methodology: Record<string, string>;
  ai_disclosure: string;
};

export type Health = {
  status: string;
  version: string;
  data_fingerprint: string;
  actual_rows: number;
  forecast_rows: number;
  timezone: string;
};

export type ProblemDocument = {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  errors?: { loc: (string | number)[]; msg: string; type: string }[];
  valid_range?: { start: string; end: string };
};

export type WindowParams = { start?: string; end?: string; cutoff?: string };

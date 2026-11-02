/** Dynamic "so what" copy. Every sentence is derived from API values. */

import type {
  AccuracySummary,
  BacktestResponse,
  BufferResponse,
  DailyRow,
  DecisionView,
  DistributionResponse,
  HorizonBucket,
  HorizonResponse,
  HourRow,
  LevelBin,
  RevisionsResponse,
  SensitivityRow,
  WorstResponse,
} from "../types/api";
import {
  formatDateLong,
  formatHorizon,
  formatMW,
  formatPct,
  formatShare,
  formatSignedMW,
  isFiniteNumber,
} from "./format";

function lowest<T>(rows: T[], value: (row: T) => number | null): T | null {
  let best: T | null = null;
  let bestValue = Number.POSITIVE_INFINITY;
  for (const row of rows) {
    const candidate = value(row);
    if (isFiniteNumber(candidate) && candidate < bestValue) {
      best = row;
      bestValue = candidate;
    }
  }
  return best;
}

function highest<T>(rows: T[], value: (row: T) => number | null): T | null {
  let best: T | null = null;
  let bestValue = Number.NEGATIVE_INFINITY;
  for (const row of rows) {
    const candidate = value(row);
    if (isFiniteNumber(candidate) && candidate > bestValue) {
      best = row;
      bestValue = candidate;
    }
  }
  return best;
}

export function deskHeadline(view: DecisionView): string {
  const latest = view.summary.latest_publish_time;
  const min = view.summary.horizon_h.min;
  const max = view.summary.horizon_h.max;
  const coverageValue = isFiniteNumber(view.coverage.coverage_pct)
    ? view.coverage.coverage_pct / 100
    : view.coverage.expected_periods > 0
      ? view.coverage.with_forecast / view.coverage.expected_periods
      : null;
  const coverage = formatShare(coverageValue);
  const latestLabel = latest ? formatTimeLabel(latest) : "a vintage before the cutoff";
  return `Forecasts published up to ${view.cutoff.local ? formatDateLong(view.cutoff.local.slice(0, 10)) : "—"}, ${view.cutoff.time} London. Latest vintage used: ${latestLabel}. Horizon ${formatHorizon(min)}–${formatHorizon(max)}. Coverage ${coverage}.`;
}

function formatTimeLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date);
}

export function deskShapeInsight(view: DecisionView): string {
  const { summary } = view;
  const peak = summary.peak_time ? `${formatTimeLabel(summary.peak_time)} London` : "—";
  const trough = summary.min_time ? `${formatTimeLabel(summary.min_time)} London` : "—";
  return `Mean wind ${formatMW(summary.mean_mw)}; peak ${formatMW(summary.peak_mw)} at ${peak}; trough ${formatMW(summary.min_mw)} at ${trough}. Largest 3 h ramp ${formatMW(summary.max_ramp_3h_mw)}.`;
}

export function deskHindsightInsight(view: DecisionView): string {
  const metrics = view.day_metrics;
  if (!metrics) return "Enable hindsight to compare the decision-time forecast with outturn.";
  const direction =
    isFiniteNumber(metrics.bias_mw) && metrics.bias_mw >= 0 ? "over-forecast" : "under-forecast";
  return `Day MAE ${formatMW(metrics.mae_mw)}, bias ${formatSignedMW(metrics.bias_mw)} (${direction}); ${formatShare(metrics.over_forecast_share)} of hours were over-forecast.`;
}

export function riskBufferInsight(buffer: BufferResponse, level: number): string {
  const point = buffer.overall.find((entry) => entry.level === level);
  if (!point || !isFiniteNumber(point.buffer_mw)) {
    return "No empirical buffer is available at this level for the selected window.";
  }
  return `At P${Math.round(level * 100)}, the historical signed-error buffer is ${formatMW(point.buffer_mw)}. Risk-adjusted wind is forecast − buffer, floored at zero.`;
}

export function backtestInsight(backtest: BacktestResponse): string {
  if (!isFiniteNumber(backtest.coverage)) {
    return "Not enough history to evaluate the buffer walk-forward in this window.";
  }
  return `Walk-forward coverage ${formatShare(backtest.coverage)} against a ${formatShare(backtest.target)} target across ${backtest.evaluated_days} evaluated days; mean buffer ${formatMW(backtest.mean_buffer_mw)}. Days with any breach: ${formatShare(backtest.days_with_breach_share)}.`;
}

export function dailyInsight(days: DailyRow[]): string {
  const worst = highest(days, (row) => row.mae_mw);
  if (!worst) return "No completed delivery days in this window.";
  return `Worst day is ${formatDateLong(worst.delivery_date)} with MAE ${formatMW(worst.mae_mw)}; its largest single miss was ${formatMW(worst.max_abs_mw)}.`;
}

export function horizonInsight(response: HorizonResponse, summary?: AccuracySummary): string {
  const filled = response.buckets.filter((bucket) => bucket.n > 0 && isFiniteNumber(bucket.nmae_pct));
  const decision = summary?.horizon_h ?? null;
  const bandText = response.decision_band_h
    ? `Decision-time horizons span ${formatHorizon(response.decision_band_h.min)}–${formatHorizon(response.decision_band_h.max)}.`
    : "No decision-time horizon band is available.";
  if (filled.length === 0) return bandText;
  const first = filled[0] as HorizonBucket;
  const last = filled[filled.length - 1] as HorizonBucket;
  const band =
    decision && isFiniteNumber(decision.mean)
      ? ` Mean selected horizon ${formatHorizon(decision.mean)}.`
      : "";
  return `Across all vintages, nMAE moves from ${formatPct(first.nmae_pct)} at ${first.label} to ${formatPct(last.nmae_pct)} at ${last.label}. ${bandText}${band}`;
}

export function hourInsight(hours: HourRow[]): string {
  const filled = hours.filter((row) => row.n > 0);
  if (filled.length === 0) return "No decision-time hours in this window.";
  const worst = highest(filled, (row) => row.mae_mw);
  const best = lowest(filled, (row) => row.mae_mw);
  if (!worst || !best) return "No decision-time hours in this window.";
  const biasHour = highest(filled, (row) => row.bias_mw);
  return `Worst London hour is ${worst.label} (MAE ${formatMW(worst.mae_mw)}); best is ${best.label} (${formatMW(best.mae_mw)}). Largest positive bias at ${biasHour?.label ?? "—"} (${formatSignedMW(biasHour?.bias_mw)}).`;
}

export function levelInsight(bins: LevelBin[], basis: "actual" | "forecast"): string {
  const filled = bins.filter((bin) => bin.n > 0);
  if (filled.length === 0) return "No wind-level bins in this window.";
  const worst = highest(filled, (bin) => bin.mae_mw);
  if (!worst) return "No wind-level bins in this window.";
  return `Using ${basis} quintiles, the highest MAE is ${formatMW(worst.mae_mw)} in ${worst.label} (${formatMW(worst.from_mw)}–${formatMW(worst.to_mw)} actual range); bias there is ${formatSignedMW(worst.bias_mw)}.`;
}

export function distributionInsight(distribution: DistributionResponse): string {
  const { quantiles } = distribution;
  return `Median signed error ${formatSignedMW(quantiles.p50)}; the central 90% runs ${formatSignedMW(quantiles.p5)} to ${formatSignedMW(quantiles.p95)}. P90 shortfall ${formatMW(quantiles.shortfall_p90)}.`;
}

export function sensitivityInsight(rows: SensitivityRow[]): string {
  const filled = rows.filter((row) => row.n > 0 && isFiniteNumber(row.mae_mw));
  if (filled.length === 0) return "No cutoff rows carry observations.";
  const best = lowest(filled, (row) => row.mae_mw);
  const worst = highest(filled, (row) => row.mae_mw);
  if (!best || !worst) return "No cutoff rows carry observations.";
  if (best.cutoff === worst.cutoff) {
    return `All cutoffs return MAE ${formatMW(best.mae_mw)} across this window.`;
  }
  return `MAE is lowest at ${best.cutoff} (${formatMW(best.mae_mw)}) and highest at ${worst.cutoff} (${formatMW(worst.mae_mw)}); the gap is ${formatMW((worst.mae_mw ?? 0) - (best.mae_mw ?? 0))}.`;
}

export function revisionsInsight(revisions: RevisionsResponse): string {
  const { selected_forecast_mw, revision_range_mw, actual_mw, error_mw } = revisions;
  const spread = revision_range_mw.spread;
  const actualText = isFiniteNumber(actual_mw)
    ? ` Outturn was ${formatMW(actual_mw)}, leaving a signed error of ${formatSignedMW(error_mw)}.`
    : " Outturn is not available in the snapshot.";
  return `The selected vintage forecast ${formatMW(selected_forecast_mw)}; vintages span ${formatMW(revision_range_mw.min)}–${formatMW(revision_range_mw.max)} (spread ${formatMW(spread)}).${actualText}`;
}

export function worstInsight(worst: WorstResponse): string {
  const day = worst.days[0];
  const period = worst.periods[0];
  if (!day || !period) return "No ranked misses in this window.";
  return `Largest daily miss: ${formatDateLong(day.delivery_date)} at MAE ${formatMW(day.mae_mw)}. Single largest error: ${formatSignedMW(period.error_mw)} at ${formatTimeLabel(period.start_time ?? "")} London on ${formatDateLong(period.delivery_date)}.`;
}

export function coverageInsight(summary: AccuracySummary): string {
  const coverage = summary.coverage;
  return `${coverage.with_forecast}/${coverage.expected_periods} periods have an eligible forecast and ${coverage.with_actual}/${coverage.expected_periods} have an actual. Missing forecasts are excluded, never imputed.`;
}

export function headlineInsight(summary: AccuracySummary): string {
  const metrics = summary.metrics;
  const baseline = summary.baseline;
  return `At ${summary.cutoff} London, MAE is ${formatMW(metrics.mae_mw)} (nMAE ${formatPct(metrics.nmae_pct)}) and bias ${formatSignedMW(metrics.bias_mw)}. Persistence MAE is ${formatMW(baseline.mae_mw)}; skill ${baseline.skill === null ? "—" : baseline.skill.toFixed(2)}.`;
}

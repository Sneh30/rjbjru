import { describe, expect, it } from "vitest";

import {
  backtestInsight,
  coverageInsight,
  dailyInsight,
  deskHeadline,
  deskHindsightInsight,
  deskShapeInsight,
  distributionInsight,
  headlineInsight,
  horizonInsight,
  hourInsight,
  levelInsight,
  revisionsInsight,
  riskBufferInsight,
  sensitivityInsight,
  worstInsight,
} from "../lib/insights";
import {
  backtest,
  buffer,
  daily,
  decision,
  decisionNoActuals,
  distribution,
  horizon,
  hours,
  levelsActual,
  levelsForecast,
  revisions,
  sensitivity,
  summary,
  worstMae,
} from "../test/server";
import type {
  AccuracySummary,
  BacktestResponse,
  BufferResponse,
  DecisionView,
  DistributionResponse,
  HorizonResponse,
  RevisionsResponse,
  SensitivityResponse,
  WorstResponse,
} from "../types/api";

const decisionView = decision as unknown as DecisionView;
const decisionWithoutActuals = decisionNoActuals as unknown as DecisionView;
const summaryData = summary as unknown as AccuracySummary;
const horizonData = horizon as unknown as HorizonResponse;
const distributionData = distribution as unknown as DistributionResponse;
const bufferData = buffer as unknown as BufferResponse;
const backtestData = backtest as unknown as BacktestResponse;
const revisionsData = revisions as unknown as RevisionsResponse;
const sensitivityData = sensitivity as unknown as SensitivityResponse;
const worstData = worstMae as unknown as WorstResponse;

describe("decision desk copy", () => {
  it("describes the selected vintage, horizon and coverage", () => {
    const text = deskHeadline(decisionView);
    expect(text).toContain("09:00 London");
    expect(text).toContain("Latest vintage used:");
    expect(text).toContain("Horizon");
    expect(text).toContain("Coverage 100%");
  });

  it("summarises shape and energy", () => {
    const text = deskShapeInsight(decisionView);
    expect(text).toContain("Mean wind");
    expect(text).toContain("Largest 3 h ramp");
    expect(text).toContain("London");
  });

  it("asks for hindsight when actuals are absent and describes bias when present", () => {
    expect(deskHindsightInsight(decisionWithoutActuals)).toContain("Enable hindsight");
    expect(deskHindsightInsight(decisionView)).toContain("over-forecast");
    expect(deskHindsightInsight(decisionView)).toContain("Day MAE");
  });

  it("degrades gracefully when the API returns null values", () => {
    const empty = structuredClone(decisionView);
    empty.cutoff.local = null;
    empty.summary.latest_publish_time = null;
    empty.summary.horizon_h = { min: null, mean: null, max: null };
    empty.coverage.coverage_pct = null;
    const text = deskHeadline(empty);
    expect(text).toContain("a vintage before the cutoff");
    expect(text).toContain("Coverage 100%");
  });
});

describe("accuracy lab copy", () => {
  it("states the headline metrics and persistence skill", () => {
    const text = headlineInsight(summaryData);
    expect(text).toContain("At 09:00 London");
    expect(text).toContain("MAE");
    expect(text).toContain("skill 0.51");
  });

  it("reports coverage without imputation", () => {
    expect(coverageInsight(summaryData)).toContain("744/744");
    expect(coverageInsight(summaryData)).toContain("never imputed");
  });

  it("identifies the worst day", () => {
    expect(dailyInsight(daily.days)).toContain("Worst day is");
    expect(dailyInsight([])).toContain("No completed delivery days");
  });

  it("describes horizon movement and the decision band", () => {
    const text = horizonInsight(horizonData, summaryData);
    expect(text).toContain("nMAE moves from");
    expect(text).toContain("Decision-time horizons span");
    expect(text).toContain("Mean selected horizon");
    expect(horizonInsight({ ...horizonData, buckets: [], decision_band_h: null })).toContain(
      "No decision-time horizon band",
    );
  });

  it("finds worst, best and bias hours", () => {
    const text = hourInsight(hours.hours);
    expect(text).toContain("Worst London hour");
    expect(text).toContain("Largest positive bias");
    expect(hourInsight([])).toContain("No decision-time hours");
  });

  it("explains level bins on both bases", () => {
    expect(levelInsight(levelsActual.bins, "actual")).toContain("actual quintiles");
    expect(levelInsight(levelsForecast.bins, "forecast")).toContain("forecast quintiles");
    expect(levelInsight([], "actual")).toContain("No wind-level bins");
  });

  it("describes the error distribution", () => {
    const text = distributionInsight(distributionData);
    expect(text).toContain("Median signed error");
    expect(text).toContain("central 90%");
    expect(text).toContain("P90 shortfall");
  });

  it("compares cutoffs and handles empty rows", () => {
    expect(sensitivityInsight(sensitivityData.rows)).toContain("MAE is lowest");
    expect(sensitivityInsight([])).toContain("No cutoff rows");
    expect(
      sensitivityInsight([
        { cutoff: "09:00", n: 1, mae_mw: 10, bias_mw: 0, shortfall_p90_mw: 1, mean_horizon_h: 1, coverage_pct: 100 },
        { cutoff: "10:00", n: 1, mae_mw: 10, bias_mw: 0, shortfall_p90_mw: 1, mean_horizon_h: 1, coverage_pct: 100 },
      ]),
    ).toContain("All cutoffs return MAE");
  });

  it("ranks worst days and periods", () => {
    const text = worstInsight(worstData);
    expect(text).toContain("Largest daily miss");
    expect(text).toContain("Single largest error");
    expect(worstInsight({ metric: "mae", days: [], periods: [] })).toContain("No ranked misses");
  });
});

describe("risk and revisions copy", () => {
  it("quotes the empirical buffer at the selected level", () => {
    expect(riskBufferInsight(bufferData, 0.9)).toContain("At P90");
    expect(riskBufferInsight(bufferData, 0.62)).toContain("No empirical buffer");
  });

  it("reports walk-forward coverage, or its absence", () => {
    const text = backtestInsight(backtestData);
    expect(text).toContain("Walk-forward coverage");
    expect(text).toContain("target");
    expect(backtestInsight({ ...backtestData, coverage: null })).toContain(
      "Not enough history",
    );
  });

  it("describes vintage spread and outturn", () => {
    const text = revisionsInsight(revisionsData);
    expect(text).toContain("selected vintage forecast");
    expect(text).toContain("vintages span");
    expect(text).toContain("Outturn was");
    expect(
      revisionsInsight({
        ...revisionsData,
        actual_mw: null,
        error_mw: null,
      }),
    ).toContain("Outturn is not available");
  });
});

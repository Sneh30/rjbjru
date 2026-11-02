import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  useAccuracySummary,
  useBacktest,
  useBuffer,
  useDaily,
  useDistribution,
  useHorizon,
  useHours,
  useLevels,
  useMeta,
  useSensitivity,
  useWorst,
} from "../api/hooks";
import { humaniseProblem } from "../api/client";
import { ChartFrame } from "../components/ChartFrame";
import { CutoffSelect } from "../components/Controls";
import { DataTable, type DataColumn } from "../components/DataTable";
import {
  BufferLevelChart,
  DailyTrendChart,
  ErrorHistogram,
  HorizonChart,
  HourChart,
  HourlyBufferChart,
  LevelChart,
  ScatterPlot,
} from "../components/LabCharts";
import { KpiCard, PageHeader, StatRow } from "../components/Metric";
import { ErrorState, PageSkeleton, Skeleton } from "../components/States";
import { apiCsvUrl } from "../lib/csv";
import {
  formatDateLong,
  formatDateShort,
  formatHorizon,
  formatMW,
  formatNumber,
  formatPct,
  formatShare,
  formatSignedMW,
  formatTime,
  londonHour,
} from "../lib/format";
import {
  backtestInsight,
  coverageInsight,
  dailyInsight,
  distributionInsight,
  headlineInsight,
  horizonInsight,
  hourInsight,
  levelInsight,
  riskBufferInsight,
  sensitivityInsight,
  worstInsight,
} from "../lib/insights";
import {
  deskHref,
  revisionHref,
  useBooleanParam,
  useCutoff,
  useLabBasis,
  useRiskLevel,
  useWindow,
} from "../lib/urlState";
import type {
  DailyRow,
  HorizonBucket,
  HourRow,
  LevelBin,
  WorstDay,
  WorstPeriod,
} from "../types/api";

function SectionHeading({
  id,
  eyebrow,
  title,
  description,
}: {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-3 mt-8" id={id}>
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-1 text-3xl">{title}</h2>
      <p className="mt-1 max-w-3xl text-sm text-soft">{description}</p>
    </div>
  );
}

export function LabPage() {
  const navigate = useNavigate();
  const meta = useMeta();
  const [cutoff, setCutoff] = useCutoff();
  const window = useWindow(meta.data);
  const [basis, setBasis] = useLabBasis();
  const [riskLevel, setRiskLevel] = useRiskLevel();
  const [viewMode, setViewMode] = useBufferView();

  const summary = useAccuracySummary({ start: window.start, end: window.end, cutoff });
  const daily = useDaily({ start: window.start, end: window.end, cutoff });
  const horizon = useHorizon({ start: window.start, end: window.end, cutoff });
  const hours = useHours({ start: window.start, end: window.end, cutoff });
  const levels = useLevels({ start: window.start, end: window.end, cutoff }, basis);
  const distribution = useDistribution({ start: window.start, end: window.end, cutoff });
  const worst = useWorst({ start: window.start, end: window.end, cutoff }, "mae", 5);
  const sensitivity = useSensitivity({ start: window.start, end: window.end });
  const buffer = useBuffer({ start: window.start, end: window.end });
  const backtest = useBacktest({ start: window.start, end: window.end }, riskLevel);

  const exportHref = (table: string, extra: Record<string, string | number | undefined> = {}) =>
    apiCsvUrl("/api/v1/export/accuracy.csv", {
      table,
      start: window.start,
      end: window.end,
      cutoff,
      ...extra,
    });

  const dailyColumns: DataColumn<DailyRow>[] = useMemo(
    () => [
      {
        key: "date",
        header: "Delivery day",
        render: (row) => (
          <Link className="underline" to={deskHref(row.delivery_date, cutoff)}>
            {formatDateShort(row.delivery_date)}
          </Link>
        ),
        sortValue: (row) => row.delivery_date,
      },
      { key: "n", header: "n", align: "right", render: (row) => formatNumber(row.n), sortValue: (row) => row.n },
      {
        key: "mae",
        header: "MAE",
        align: "right",
        render: (row) => formatMW(row.mae_mw),
        sortValue: (row) => row.mae_mw,
      },
      {
        key: "bias",
        header: "Bias",
        align: "right",
        render: (row) => formatSignedMW(row.bias_mw),
        sortValue: (row) => row.bias_mw,
      },
      {
        key: "rmse",
        header: "RMSE",
        align: "right",
        render: (row) => formatMW(row.rmse_mw),
        sortValue: (row) => row.rmse_mw,
      },
      {
        key: "max",
        header: "Max |error|",
        align: "right",
        render: (row) => formatMW(row.max_abs_mw),
        sortValue: (row) => row.max_abs_mw,
      },
      {
        key: "shortfall",
        header: "P90 shortfall",
        align: "right",
        render: (row) => formatMW(row.shortfall_p90_mw),
        sortValue: (row) => row.shortfall_p90_mw,
      },
    ],
    [cutoff],
  );

  const horizonColumns: DataColumn<HorizonBucket>[] = [
    { key: "label", header: "Horizon bucket", render: (row) => row.label },
    { key: "n", header: "n", align: "right", render: (row) => formatNumber(row.n) },
    {
      key: "nmae",
      header: "nMAE",
      align: "right",
      render: (row) => formatPct(row.nmae_pct),
    },
    { key: "mae", header: "MAE", align: "right", render: (row) => formatMW(row.mae_mw) },
    {
      key: "bias",
      header: "Bias",
      align: "right",
      render: (row) => formatSignedMW(row.bias_mw),
    },
    { key: "rmse", header: "RMSE", align: "right", render: (row) => formatMW(row.rmse_mw) },
  ];

  const hourColumns: DataColumn<HourRow>[] = [
    { key: "label", header: "London hour", render: (row) => row.label },
    { key: "n", header: "n", align: "right", render: (row) => formatNumber(row.n) },
    { key: "mae", header: "MAE", align: "right", render: (row) => formatMW(row.mae_mw) },
    {
      key: "bias",
      header: "Bias",
      align: "right",
      render: (row) => formatSignedMW(row.bias_mw),
    },
    {
      key: "shortfall",
      header: "P90 shortfall",
      align: "right",
      render: (row) => formatMW(row.shortfall_p90_mw),
    },
  ];

  const levelColumns: DataColumn<LevelBin>[] = [
    { key: "label", header: "Bin", render: (row) => row.label },
    {
      key: "range",
      header: "Range",
      render: (row) => `${formatMW(row.from_mw)}–${formatMW(row.to_mw)}`,
    },
    { key: "n", header: "n", align: "right", render: (row) => formatNumber(row.n) },
    { key: "mae", header: "MAE", align: "right", render: (row) => formatMW(row.mae_mw) },
    {
      key: "bias",
      header: "Bias",
      align: "right",
      render: (row) => formatSignedMW(row.bias_mw),
    },
    { key: "nmae", header: "nMAE", align: "right", render: (row) => formatPct(row.nmae_pct) },
  ];

  const worstDayColumns: DataColumn<WorstDay>[] = [
    {
      key: "date",
      header: "Delivery day",
      render: (row) => (
        <Link className="underline" to={deskHref(row.delivery_date, cutoff)}>
          {formatDateLong(row.delivery_date)}
        </Link>
      ),
    },
    { key: "mae", header: "MAE", align: "right", render: (row) => formatMW(row.mae_mw) },
    {
      key: "bias",
      header: "Bias",
      align: "right",
      render: (row) => formatSignedMW(row.bias_mw),
    },
    {
      key: "max",
      header: "Max |error|",
      align: "right",
      render: (row) => formatMW(row.max_abs_mw),
    },
  ];

  const worstPeriodColumns: DataColumn<WorstPeriod>[] = [
    {
      key: "time",
      header: "London hour",
      render: (row) => (
        <Link
          className="underline"
          to={revisionHref(row.delivery_date, (londonHour(row.start_time) ?? 0) + 1, cutoff)}
          title={`Revisions for ${formatDateLong(row.delivery_date)}`}
        >
          {formatDateShort(row.delivery_date)} {formatTime(row.start_time)}
        </Link>
      ),
    },
    {
      key: "forecast",
      header: "Forecast",
      align: "right",
      render: (row) => formatMW(row.forecast_mw),
    },
    {
      key: "actual",
      header: "Actual",
      align: "right",
      render: (row) => formatMW(row.actual_mw),
    },
    {
      key: "error",
      header: "Error",
      align: "right",
      render: (row) => formatSignedMW(row.error_mw),
    },
  ];

  if (meta.isError) {
    return (
      <ErrorState
        title="The snapshot metadata did not load"
        message={humaniseProblem(meta.error)}
        onRetry={() => void meta.refetch()}
      />
    );
  }
  if (!meta.data) {
    return <PageSkeleton label="Loading the accuracy lab" />;
  }
  if (summary.isError) {
    return (
      <ErrorState
        title="The accuracy scorecard did not load"
        message={humaniseProblem(summary.error)}
        onRetry={() => void summary.refetch()}
      />
    );
  }
  if (!summary.data) {
    return <PageSkeleton label="Loading the accuracy scorecard" />;
  }

  const data = summary.data;
  const metrics = data.metrics;
  const bufferData = buffer.data;

  return (
    <>
      <PageHeader
        eyebrow="Accuracy Lab · decision-time evaluation"
        title="Where the forecast breaks, and by how much"
        description={
          <>
            Pooled accuracy for delivery days <strong>{formatDateLong(window.start)}</strong> to{" "}
            <strong>{formatDateLong(window.end)}</strong> at the <strong>{cutoff} London</strong>{" "}
            cutoff. Every hour uses the latest eligible vintage. Hindsight is used only for scoring.
          </>
        }
        actions={
          <a className="btn" href={exportHref("daily")}>
            Export daily CSV
          </a>
        }
      />

      <section className="card mb-4 p-4" aria-label="Lab controls">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-12">
          <div className="lg:col-span-3">
            <label className="label" htmlFor="window-start">
              Window start
            </label>
            <input
              id="window-start"
              type="date"
              className="field w-full"
              value={window.start}
              min={meta.data.scope.delivery_dates.start}
              max={window.end}
              onChange={(event) => {
                if (event.target.value) window.setStart(event.target.value);
              }}
            />
          </div>
          <div className="lg:col-span-3">
            <label className="label" htmlFor="window-end">
              Window end
            </label>
            <input
              id="window-end"
              type="date"
              className="field w-full"
              value={window.end}
              min={window.start}
              max={meta.data.scope.delivery_dates.end}
              onChange={(event) => {
                if (event.target.value) window.setEnd(event.target.value);
              }}
            />
          </div>
          <div className="lg:col-span-2">
            <CutoffSelect value={cutoff} options={meta.data.cutoff_grid} onChange={setCutoff} />
          </div>
          <div className="flex items-end lg:col-span-4">
            <button
              type="button"
              className="btn"
              onClick={window.reset}
              disabled={window.isDefault}
            >
              Reset to full window
            </button>
          </div>
        </div>
      </section>

      <section aria-labelledby="scorecard-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Scorecard</p>
            <h2 className="mt-1 text-3xl" id="scorecard-title">
              {formatDateShort(data.window.start)} – {formatDateShort(data.window.end)}
            </h2>
            <p className="mt-1 text-sm text-soft">{headlineInsight(data)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="chip">{data.window.delivery_days} delivery days</span>
            <span className="chip">{formatNumber(metrics.n)} scored hours</span>
            <span className="chip">Cutoff {data.cutoff}</span>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          <KpiCard
            label="MAE"
            value={formatMW(metrics.mae_mw)}
            sub={`n = ${formatNumber(metrics.n)}`}
            tone="forecast"
            hint="Mean absolute error of forecast minus actual, in MW."
          />
          <KpiCard
            label="RMSE"
            value={formatMW(metrics.rmse_mw)}
            sub="Penalises large misses"
            hint="Square root of mean squared error."
          />
          <KpiCard
            label="Bias"
            value={formatSignedMW(metrics.bias_mw)}
            sub={
              typeof metrics.bias_mw === "number" && metrics.bias_mw > 0
                ? "Over-forecast on average"
                : "Under-forecast on average"
            }
            tone={typeof metrics.bias_mw === "number" && metrics.bias_mw > 0 ? "over" : "under"}
            hint="Mean signed error; positive means wind was over-forecast and buyers face shortfall risk."
          />
          <KpiCard
            label="nMAE"
            value={formatPct(metrics.nmae_pct)}
            sub={`Mean actual ${formatMW(metrics.mean_actual_mw)}`}
            hint="MAE divided by mean actual output. No installed-capacity data is used."
          />
          <KpiCard
            label="P90 |error|"
            value={formatMW(metrics.p90_abs_mw)}
            sub={`P95 ${formatMW(metrics.p95_abs_mw)}`}
            hint="90th percentile of absolute error."
          />
          <KpiCard
            label="P90 shortfall"
            value={formatMW(metrics.shortfall_p90_mw)}
            sub={`Max ${formatMW(metrics.shortfall_max_mw)}`}
            tone="over"
            hint="90th percentile of max(0, forecast − actual); the buyer-relevant tail."
          />
          <KpiCard
            label="Over-forecast share"
            value={formatShare(metrics.over_forecast_share)}
            sub={`${formatNumber(
              Math.round((metrics.over_forecast_share ?? 0) * metrics.n),
            )} of ${formatNumber(metrics.n)} hours`}
            tone="over"
            hint="Share of hours where forecast exceeded actual."
          />
          <KpiCard
            label="Skill vs persistence"
            value={data.baseline.skill === null ? "—" : data.baseline.skill.toFixed(2)}
            sub={`Persistence MAE ${formatMW(data.baseline.mae_mw)}`}
            hint="1 − MAE_forecast / MAE_persistence. Above zero beats holding the last known actual flat."
          />
          <KpiCard
            label="Correlation"
            value={data.metrics.correlation === null ? "—" : data.metrics.correlation.toFixed(2)}
            sub="Forecast vs actual"
            hint="Pearson correlation across scored hours."
          />
          <KpiCard
            label="Coverage"
            value={formatPct(data.coverage.coverage_pct)}
            sub={`${data.coverage.with_forecast}/${data.coverage.expected_periods} forecast · ${data.coverage.with_actual}/${data.coverage.expected_periods} actual`}
            tone="under"
            hint="Expected hourly periods versus periods with an eligible forecast and a complete actual average."
          />
        </div>
        <p className="mt-2 text-xs text-muted">{coverageInsight(data)}</p>
      </section>

      <SectionHeading
        id="daily"
        eyebrow="Stability"
        title="Daily accuracy"
        description="Bars are daily MAE; the line is daily bias. Click a bar to open that delivery day on the Desk."
      />
      <ChartFrame
        id="daily-chart"
        title="Daily MAE and bias"
        insight={dailyInsight(daily.data?.days ?? [])}
        description="Bars show daily mean absolute error in MW; the line shows daily mean signed error."
        actions={
          <a className="btn btn-ghost text-xs" href={exportHref("daily")}>
            CSV
          </a>
        }
        table={
          daily.data ? (
            <DataTable
              rows={daily.data.days}
              columns={dailyColumns}
              caption="Daily accuracy table"
              rowKey={(row) => row.delivery_date}
              initialSort={{ key: "date", direction: "asc" }}
            />
          ) : undefined
        }
      >
        {daily.data ? (
          <DailyTrendChart
            days={daily.data.days}
            onSelect={(date) => navigate(deskHref(date, cutoff))}
          />
        ) : (
          <Skeleton className="h-72" label="Loading daily accuracy" />
        )}
      </ChartFrame>

      <SectionHeading
        id="horizon"
        eyebrow="Lead time"
        title="Error by forecast horizon"
        description="All vintages, not only the selected one, bucketed by hours between publication and target. The shaded band is the horizon implied by this cutoff."
      />
      <ChartFrame
        id="horizon-chart"
        title="nMAE by horizon"
        insight={horizon.data ? horizonInsight(horizon.data, data) : "Loading horizon buckets."}
        description="Bars show normalised mean absolute error by forecast horizon; the shaded region marks the decision-time horizon band."
        actions={
          <a className="btn btn-ghost text-xs" href={exportHref("by-horizon")}>
            CSV
          </a>
        }
        table={
          horizon.data ? (
            <DataTable
              rows={horizon.data.buckets}
              columns={horizonColumns}
              caption="Accuracy by horizon table"
              rowKey={(row) => row.label}
            />
          ) : undefined
        }
        footnote={
          horizon.data
            ? `${formatNumber(horizon.data.n_vintage_rows)} vintage rows; ${formatNumber(
                horizon.data.dropped_negative_horizon,
              )} rows with negative horizon were excluded from buckets.`
            : undefined
        }
      >
        {horizon.data ? (
          <HorizonChart
            buckets={horizon.data.buckets}
            band={horizon.data.decision_band_h}
          />
        ) : (
          <Skeleton className="h-72" label="Loading horizon accuracy" />
        )}
      </ChartFrame>

      <SectionHeading
        id="hours"
        eyebrow="Time of day"
        title="Error by London hour"
        description="Decision-time accuracy within the local delivery day. Bars are MAE; the line is bias."
      />
      <ChartFrame
        id="hour-chart"
        title="Hour-of-day error"
        insight={hours.data ? hourInsight(hours.data.hours) : "Loading hour buckets."}
        description="Bars show mean absolute error by London hour; the line shows mean signed error."
        actions={
          <a className="btn btn-ghost text-xs" href={exportHref("by-hour")}>
            CSV
          </a>
        }
        table={
          hours.data ? (
            <DataTable
              rows={hours.data.hours}
              columns={hourColumns}
              caption="Accuracy by London hour table"
              rowKey={(row) => row.label}
            />
          ) : undefined
        }
      >
        {hours.data ? (
          <HourChart hours={hours.data.hours} />
        ) : (
          <Skeleton className="h-72" label="Loading hour accuracy" />
        )}
      </ChartFrame>

      <SectionHeading
        id="levels"
        eyebrow="Output level"
        title="Error by wind level"
        description="Equal-count quintiles. Switch the basis to ask whether errors cluster by what was forecast or by what actually happened."
      />
      <ChartFrame
        id="level-chart"
        title="MAE by wind-output quintile"
        insight={levels.data ? levelInsight(levels.data.bins, levels.data.basis) : "Loading wind-level bins."}
        description="Bars show mean absolute error for each equal-count wind-output bin."
        actions={
          <>
            <select
              className="field text-xs"
              aria-label="Wind-level basis"
              value={basis}
              onChange={(event) => setBasis(event.target.value === "forecast" ? "forecast" : "actual")}
            >
              <option value="actual">Basis: actual</option>
              <option value="forecast">Basis: forecast</option>
            </select>
            <a className="btn btn-ghost text-xs" href={exportHref("by-level", { basis })}>
              CSV
            </a>
          </>
        }
        table={
          levels.data ? (
            <DataTable
              rows={levels.data.bins}
              columns={levelColumns}
              caption="Accuracy by wind level table"
              rowKey={(row) => row.label}
            />
          ) : undefined
        }
      >
        {levels.data ? (
          <LevelChart bins={levels.data.bins} />
        ) : (
          <Skeleton className="h-72" label="Loading wind-level accuracy" />
        )}
      </ChartFrame>

      <SectionHeading
        id="distribution"
        eyebrow="Shape of error"
        title="Distribution and scatter"
        description="Signed error is forecast minus actual. The scatter compares each decision-time forecast with its outturn; the dashed line is perfect foresight."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartFrame
          id="histogram-chart"
          title="Signed-error histogram"
          insight={
            distribution.data
              ? distributionInsight(distribution.data)
              : "Loading error distribution."
          }
          description="Histogram of signed hourly forecast error in MW."
        >
          {distribution.data ? (
            <>
              <ErrorHistogram distribution={distribution.data} />
              <div className="mt-3">
                <StatRow
                  items={[
                    { label: "P5 error", value: formatSignedMW(distribution.data.quantiles.p5) },
                    { label: "P50 error", value: formatSignedMW(distribution.data.quantiles.p50) },
                    { label: "P95 error", value: formatSignedMW(distribution.data.quantiles.p95) },
                    {
                      label: "P90 shortfall",
                      value: formatMW(distribution.data.quantiles.shortfall_p90),
                      tone: "over",
                    },
                  ]}
                />
              </div>
            </>
          ) : (
            <Skeleton className="h-64" label="Loading histogram" />
          )}
        </ChartFrame>
        <ChartFrame
          id="scatter-chart"
          title="Actual vs forecast"
          insight={
            distribution.data
              ? `Scatter shows ${formatNumber(distribution.data.scatter.length)} of ${formatNumber(
                  distribution.data.scatter_total,
                )} scored hours${distribution.data.scatter_total > distribution.data.scatter_limit ? " (deterministic sample)" : ""}. Points above the 1:1 line were under-forecast.`
              : "Loading scatter."
          }
          description="Scatter plot of decision-time forecast MW on the x-axis and actual MW on the y-axis, with a dashed 1:1 line."
        >
          {distribution.data ? (
            <ScatterPlot distribution={distribution.data} />
          ) : (
            <Skeleton className="h-64" label="Loading scatter" />
          )}
        </ChartFrame>
      </div>

      <SectionHeading
        id="worst"
        eyebrow="Drill-down"
        title="Worst days and hours"
        description="Ranked at the selected cutoff. Day links open the Desk; period links open the Revisions explorer."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card p-4" aria-labelledby="worst-days-title">
          <h2 className="text-xl font-semibold" id="worst-days-title">
            Worst delivery days
          </h2>
          <p className="mt-1 text-sm text-soft">
            {worst.data ? worstInsight(worst.data) : "Loading ranked misses."}
          </p>
          <div className="mt-3">
            {worst.data ? (
              <DataTable
                rows={worst.data.days}
                columns={worstDayColumns}
                caption="Worst delivery days table"
                rowKey={(row) => row.delivery_date}
                maxHeight="20rem"
              />
            ) : (
              <Skeleton className="h-44" label="Loading worst days" />
            )}
          </div>
        </section>
        <section className="card p-4" aria-labelledby="worst-periods-title">
          <h2 className="text-xl font-semibold" id="worst-periods-title">
            Worst individual hours
          </h2>
          <p className="mt-1 text-sm text-soft">
            Largest absolute signed error across the window. Click through to see every vintage for
            that delivery day.
          </p>
          <div className="mt-3">
            {worst.data ? (
              <DataTable
                rows={worst.data.periods}
                columns={worstPeriodColumns}
                caption="Worst individual hours table"
                rowKey={(row) => `${row.delivery_date}-${row.start_time ?? ""}`}
                maxHeight="20rem"
              />
            ) : (
              <Skeleton className="h-44" label="Loading worst hours" />
            )}
          </div>
        </section>
      </div>

      <SectionHeading
        id="sensitivity"
        eyebrow="Decision timing"
        title="Cutoff sensitivity"
        description="Re-selects vintages at each cutoff on the D−1 grid. Earlier cutoffs see older forecasts; later cutoffs see more information. This is a robustness check, not a recommendation to move the market gate."
      />
      <ChartFrame
        id="sensitivity-chart"
        title="MAE, bias and shortfall by cutoff"
        insight={sensitivity.data ? sensitivityInsight(sensitivity.data.rows) : "Loading cutoff grid."}
        description="Table of accuracy metrics across the configured cutoff grid."
        actions={
          <a className="btn btn-ghost text-xs" href={exportHref("cutoff-sensitivity")}>
            CSV
          </a>
        }
      >
        {sensitivity.data ? (
          <div className="table-wrap" style={{ maxHeight: "24rem" }} tabIndex={0} role="region" aria-label="Cutoff sensitivity table">
            <table className="data-table">
              <caption className="sr-only">Cutoff sensitivity</caption>
              <thead>
                <tr>
                  <th scope="col">Cutoff</th>
                  <th scope="col" className="text-right">
                    n
                  </th>
                  <th scope="col" className="text-right">
                    MAE
                  </th>
                  <th scope="col" className="text-right">
                    Bias
                  </th>
                  <th scope="col" className="text-right">
                    P90 shortfall
                  </th>
                  <th scope="col" className="text-right">
                    Mean horizon
                  </th>
                </tr>
              </thead>
              <tbody>
                {sensitivity.data.rows.map((row) => (
                  <tr
                    key={row.cutoff}
                    style={
                      row.cutoff === cutoff
                        ? { background: "var(--forecast-soft)", fontWeight: 600 }
                        : undefined
                    }
                  >
                    <td>
                      {row.cutoff}
                      {row.cutoff === cutoff ? " · selected" : ""}
                    </td>
                    <td className="num">{formatNumber(row.n)}</td>
                    <td className="num">{formatMW(row.mae_mw)}</td>
                    <td className="num">{formatSignedMW(row.bias_mw)}</td>
                    <td className="num">{formatMW(row.shortfall_p90_mw)}</td>
                    <td className="num">{formatHorizon(row.mean_horizon_h)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Skeleton className="h-56" label="Loading cutoff sensitivity" />
        )}
      </ChartFrame>

      <SectionHeading
        id="risk"
        eyebrow="Decision aid"
        title="Risk buffer and calibration"
        description="In-sample empirical buffers size the downside; a walk-forward back-test asks whether those buffers actually covered outturn using only information available at the time."
      />
      <section className="card p-4 sm:p-5" aria-labelledby="risk-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold" id="risk-title">
              Empirical buffer
            </h2>
            <p className="mt-1 max-w-3xl text-sm text-soft">
              {bufferData
                ? riskBufferInsight(bufferData, riskLevel)
                : "Loading empirical buffers."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="label mb-0" htmlFor="buffer-level">
              Level
            </label>
            <select
              id="buffer-level"
              className="field"
              value={riskLevel}
              onChange={(event) => setRiskLevel(Number(event.target.value))}
            >
              <option value={0.5}>P50</option>
              <option value={0.75}>P75</option>
              <option value={0.9}>P90</option>
              <option value={0.95}>P95</option>
            </select>
            <div className="flex overflow-hidden rounded-lg border" role="group" aria-label="Buffer view">
              <button
                type="button"
                className={`px-2.5 py-1.5 text-xs font-medium ${viewMode === "overall" ? "bg-sunken" : ""}`}
                aria-pressed={viewMode === "overall"}
                onClick={() => setViewMode("overall")}
              >
                Overall
              </button>
              <button
                type="button"
                className={`px-2.5 py-1.5 text-xs font-medium ${viewMode === "hourly" ? "bg-sunken" : ""}`}
                aria-pressed={viewMode === "hourly"}
                onClick={() => setViewMode("hourly")}
              >
                By hour
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            {bufferData ? (
              viewMode === "overall" ? (
                <div role="img" aria-label="Empirical buffer MW at each risk level">
                  <BufferLevelChart points={bufferData.overall} />
                </div>
              ) : (
                <div role="img" aria-label="Empirical buffer MW by London delivery hour">
                  <HourlyBufferChart rows={bufferData.by_hour} level={riskLevel} />
                </div>
              )
            ) : (
              <Skeleton className="h-52" label="Loading buffer chart" />
            )}
            <p className="mt-1 text-xs text-muted">
              Buffer = empirical quantile of signed error. Risk-adjusted wind = max(0, forecast −
              buffer).
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Walk-forward {levelLabel(riskLevel)} calibration
            </h3>
            {backtest.data ? (
              <>
                <p className="mt-1 text-sm text-soft">{backtestInsight(backtest.data)}</p>
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-muted">
                    <span>Empirical coverage</span>
                    <span>
                      {formatShare(backtest.data.coverage)} vs target{" "}
                      {formatShare(backtest.data.target)}
                    </span>
                  </div>
                  <div
                    role="meter"
                    aria-label="Walk-forward coverage against target"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round((backtest.data.coverage ?? 0) * 100)}
                    className="relative mt-1 h-4 overflow-hidden rounded-full"
                    style={{ background: "var(--paper-sunken)", border: "1px solid var(--rule)" }}
                  >
                    <div
                      className="h-full"
                      style={{
                        width: `${(backtest.data.coverage ?? 0) * 100}%`,
                        background: "var(--under)",
                      }}
                    />
                    <div
                      aria-hidden="true"
                      className="absolute inset-y-0 border-l-2 border-dashed"
                      style={{
                        left: `${backtest.data.target * 100}%`,
                        borderColor: "var(--ink)",
                      }}
                    />
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div className="card-quiet px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted">Evaluated days</p>
                    <p className="font-semibold">{formatNumber(backtest.data.evaluated_days)}</p>
                  </div>
                  <div className="card-quiet px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted">Skipped days</p>
                    <p className="font-semibold">{formatNumber(backtest.data.skipped_days.length)}</p>
                  </div>
                  <div className="card-quiet px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted">Mean buffer</p>
                    <p className="font-semibold">{formatMW(backtest.data.mean_buffer_mw)}</p>
                  </div>
                  <div className="card-quiet px-3 py-2">
                    <p className="text-[11px] uppercase tracking-wide text-muted">Days with breach</p>
                    <p className="font-semibold">
                      {formatShare(backtest.data.days_with_breach_share)}
                    </p>
                  </div>
                </div>
                <p className="mt-2 text-xs text-muted">
                  {formatNumber(backtest.data.outcome_lag_days)}-day outcome lag; minimum{" "}
                  {formatNumber(backtest.data.min_history_days)} history days.{" "}
                  {backtest.data.caveat}
                </p>
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm underline">
                    Daily coverage table
                  </summary>
                  <div className="mt-2">
                    <DataTable
                      rows={backtest.data.daily}
                      columns={[
                        { key: "date", header: "Day", render: (row) => formatDateShort(row.delivery_date) },
                        {
                          key: "buffer",
                          header: "Buffer",
                          align: "right",
                          render: (row) => formatMW(row.buffer_mw),
                        },
                        {
                          key: "coverage",
                          header: "Coverage",
                          align: "right",
                          render: (row) => formatShare(row.coverage),
                        },
                        {
                          key: "breaches",
                          header: "Breaches",
                          align: "right",
                          render: (row) => `${formatNumber(row.breaches)}/${formatNumber(row.n)}`,
                        },
                      ]}
                      caption="Walk-forward daily coverage"
                      rowKey={(row) => row.delivery_date}
                    />
                  </div>
                </details>
              </>
            ) : (
              <Skeleton className="h-52" label="Loading walk-forward back-test" />
            )}
          </div>
        </div>
        <p className="mt-4 border-t pt-3 text-xs text-muted" style={{ borderColor: "var(--rule)" }}>
          Limitations: 31 delivery days, one season, in-sample quantiles for the headline buffer,
          a two-day outcome lag in the back-test, and no demand, price or capacity data. This is an
          empirical decision aid, not financial advice.
        </p>
      </section>

      <section className="card mt-6 p-4" aria-labelledby="quality-title">
        <h2 className="text-xl font-semibold" id="quality-title">
          Data quality
        </h2>
        <p className="mt-1 text-sm text-soft">
          Snapshot <span className="font-mono">{meta.data.data.fingerprint.slice(0, 12)}</span>{" "}
          ingested {meta.data.data.generated_at ?? "—"}. Source: {meta.data.data.source}. No missing
          actual or forecast periods are filled.
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(meta.data.data.quality).map(([key, value]) => (
            <div className="card-quiet px-3 py-2" key={key}>
              <dt className="text-[11px] uppercase tracking-wide text-muted">
                {key.replaceAll("_", " ")}
              </dt>
              <dd className="font-semibold">{value ?? "—"}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-muted">
          Quality counters come from the committed ingestion report. Coverage shown above counts
          hourly periods after averaging complete half-hour pairs.
        </p>
      </section>
    </>
  );
}

function levelLabel(level: number): string {
  return `P${Math.round(level * 100)}`;
}

function useBufferView(): ["overall" | "hourly", (value: "overall" | "hourly") => void] {
  const [hourly, setHourly] = useBooleanParam("hourly", false);
  return [hourly ? "hourly" : "overall", (value) => setHourly(value === "hourly")];
}

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useBacktest, useBuffer, useDecisionView, useMeta } from "../api/hooks";
import { humaniseProblem } from "../api/client";
import { ChartFrame } from "../components/ChartFrame";
import { CutoffSelect, DeliveryDatePicker, Toggle } from "../components/Controls";
import { DataTable, type DataColumn } from "../components/DataTable";
import { ForecastChart } from "../components/ForecastChart";
import { KpiCard, PageHeader } from "../components/Metric";
import { EmptyState, ErrorState, PageSkeleton } from "../components/States";
import { VintageStrip } from "../components/VintageStrip";
import { downloadCsv, toCsv } from "../lib/csv";
import {
  formatCoverage,
  formatDateLong,
  formatDateTime,
  formatEnergy,
  formatHorizon,
  formatMW,
  formatMWValue,
  formatSignedMW,
  formatTime,
} from "../lib/format";
import {
  backtestInsight,
  deskHeadline,
  deskHindsightInsight,
  deskShapeInsight,
  riskBufferInsight,
} from "../lib/insights";
import {
  deskHref,
  revisionHref,
  useBooleanParam,
  useCutoff,
  useDeliveryDate,
  useRiskLevel,
} from "../lib/urlState";
import type { DecisionPoint } from "../types/api";

type HourRow = {
  point: DecisionPoint;
  riskAdjusted: number | null;
  buffer: number | null;
  residual: number | null;
  residualRisk: number | null;
};

function hourOf(iso: string | null): number | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      hourCycle: "h23",
    }).format(date),
  );
}

export function DeskPage() {
  const meta = useMeta();
  const [cutoff, setCutoff] = useCutoff();
  const { date, setDate, dates, previous, next } = useDeliveryDate(meta.data);
  const [hindsight, setHindsight] = useBooleanParam("hindsight", false);
  const [riskEnabled, setRiskEnabled] = useBooleanParam("band", true);
  const [riskLevel, setRiskLevel] = useRiskLevel();
  const [demandRaw, setDemandRaw] = useState("");

  const decision = useDecisionView(date, cutoff, hindsight);
  const buffer = useBuffer({}, "0.5,0.75,0.9,0.95");
  const backtest = useBacktest({}, riskLevel);

  const demand = useMemo(() => {
    const trimmed = demandRaw.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed.replace(/,/g, ""));
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  }, [demandRaw]);

  const levelLabel = `P${Math.round(riskLevel * 100)}`;

  const buffersByHour = useMemo(() => {
    const map = new Map<number, number>();
    for (const row of buffer.data?.by_hour ?? []) {
      const point = row.buffers.find((entry) => entry.level === riskLevel);
      if (point && typeof point.buffer_mw === "number") map.set(row.hour, point.buffer_mw);
    }
    return map;
  }, [buffer.data, riskLevel]);

  const rows: HourRow[] = useMemo(() => {
    const points = decision.data?.points ?? [];
    return points.map((point) => {
      const hour = hourOf(point.local_time);
      const bufferValue = hour !== null ? (buffersByHour.get(hour) ?? null) : null;
      const riskAdjusted =
        typeof point.forecast_mw === "number" && bufferValue !== null
          ? Math.max(0, point.forecast_mw - bufferValue)
          : null;
      const residual =
        demand !== null && typeof point.forecast_mw === "number" ? demand - point.forecast_mw : null;
      const residualRisk = demand !== null && riskAdjusted !== null ? demand - riskAdjusted : null;
      return { point, riskAdjusted, buffer: bufferValue, residual, residualRisk };
    });
  }, [decision.data, buffersByHour, demand]);

  const meanRiskAdjusted = useMemo(() => {
    const values = rows.map((row) => row.riskAdjusted).filter((value): value is number => value !== null);
    return values.length ? values.reduce((total, value) => total + value, 0) / values.length : null;
  }, [rows]);

  const overallBuffer = useMemo(
    () =>
      buffer.data?.overall.find((point) => point.level === riskLevel)?.buffer_mw ?? null,
    [buffer.data, riskLevel],
  );

  const residualStats = useMemo(() => {
    if (demand === null) return null;
    const forecastMean = decision.data?.summary.mean_mw ?? null;
    const residualMean = forecastMean !== null ? demand - forecastMean : null;
    const residualRiskMean = meanRiskAdjusted !== null ? demand - meanRiskAdjusted : null;
    const maxResidual = rows.reduce<number | null>((current, row) => {
      if (row.residual === null) return current;
      return current === null ? row.residual : Math.max(current, row.residual);
    }, null);
    return { residualMean, residualRiskMean, maxResidual };
  }, [demand, decision.data, meanRiskAdjusted, rows]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(target.tagName)) return;
      if (event.key === "ArrowLeft" && previous) setDate(previous);
      if (event.key === "ArrowRight" && next) setDate(next);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, previous, setDate]);

  const view = decision.data;

  const columns: DataColumn<HourRow>[] = useMemo(
    () => [
      {
        key: "time",
        header: "London hour",
        render: (row) => (
          <span className="font-mono text-xs">{formatTime(row.point.local_time)}</span>
        ),
        sortValue: (row) => row.point.local_time,
      },
      {
        key: "forecast",
        header: "Forecast",
        align: "right",
        render: (row) => formatMW(row.point.forecast_mw),
        sortValue: (row) => row.point.forecast_mw,
      },
      {
        key: "vintage",
        header: "Vintage",
        render: (row) => (
          <span title={formatDateTime(row.point.publish_time)}>
            {formatTime(row.point.publish_time)}
          </span>
        ),
        sortValue: (row) => row.point.publish_time,
      },
      {
        key: "horizon",
        header: "Horizon",
        align: "right",
        render: (row) => formatHorizon(row.point.horizon_h),
        sortValue: (row) => row.point.horizon_h,
      },
      {
        key: "risk",
        header: `Risk-adj. ${levelLabel}`,
        align: "right",
        render: (row) => formatMW(row.riskAdjusted),
        sortValue: (row) => row.riskAdjusted,
      },
      ...(hindsight
        ? [
            {
              key: "actual",
              header: "Actual",
              align: "right" as const,
              render: (row: HourRow) => formatMW(row.point.actual_mw),
              sortValue: (row: HourRow) => row.point.actual_mw ?? null,
            },
            {
              key: "error",
              header: "Error",
              align: "right" as const,
              render: (row: HourRow) => (
                <span
                  style={{
                    color:
                      typeof row.point.error_mw === "number" && row.point.error_mw > 0
                        ? "var(--over)"
                        : "var(--under)",
                  }}
                >
                  {formatSignedMW(row.point.error_mw)}
                </span>
              ),
              sortValue: (row: HourRow) => row.point.error_mw ?? null,
            },
          ]
        : []),
      ...(demand !== null
        ? [
            {
              key: "residual",
              header: "Residual to procure",
              align: "right" as const,
              render: (row: HourRow) => formatSignedMW(row.residual),
              sortValue: (row: HourRow) => row.residual,
            },
          ]
        : []),
    ],
    [hindsight, demand, levelLabel],
  );

  const exportCsv = () => {
    if (!view) return;
    const content = toCsv(
      rows.map((row) => ({
        delivery_date: view.delivery_date,
        cutoff: cutoff,
        local_time: formatTime(row.point.local_time),
        start_time_utc: row.point.start_time ?? "",
        forecast_mw: formatMWValue(row.point.forecast_mw),
        publish_time_utc: row.point.publish_time ?? "",
        horizon_h: row.point.horizon_h,
        risk_adjusted_mw: formatMWValue(row.riskAdjusted),
        buffer_mw: formatMWValue(row.buffer),
        actual_mw: hindsight ? formatMWValue(row.point.actual_mw) : "",
        error_mw: hindsight ? formatMWValue(row.point.error_mw) : "",
        demand_what_if_mw: demand ?? "",
        residual_to_procure_mw: formatMWValue(row.residual),
      })),
      [
        { header: "delivery_date", value: (row) => row.delivery_date },
        { header: "cutoff", value: (row) => row.cutoff },
        { header: "local_time", value: (row) => row.local_time },
        { header: "start_time_utc", value: (row) => row.start_time_utc },
        { header: "forecast_mw", value: (row) => row.forecast_mw },
        { header: "publish_time_utc", value: (row) => row.publish_time_utc },
        { header: "horizon_h", value: (row) => row.horizon_h },
        { header: "risk_adjusted_mw", value: (row) => row.risk_adjusted_mw },
        { header: "buffer_mw", value: (row) => row.buffer_mw },
        { header: "actual_mw", value: (row) => row.actual_mw },
        { header: "error_mw", value: (row) => row.error_mw },
        { header: "demand_what_if_mw", value: (row) => row.demand_what_if_mw },
        { header: "residual_to_procure_mw", value: (row) => row.residual_to_procure_mw },
      ],
    );
    downloadCsv(`windlens-${view.delivery_date}-${cutoff.replace(":", "")}.csv`, content);
  };

  if (meta.isError) {
    return (
      <ErrorState
        title="The snapshot metadata did not load"
        message={humaniseProblem(meta.error)}
        onRetry={() => void meta.refetch()}
      />
    );
  }
  if (!meta.data || (decision.isPending && !view)) {
    return <PageSkeleton label="Loading the decision desk" />;
  }
  if (decision.isError) {
    return (
      <ErrorState
        title="The decision view did not load"
        message={humaniseProblem(decision.error)}
        onRetry={() => void decision.refetch()}
      />
    );
  }
  if (!view) {
    return <PageSkeleton label="Loading the decision desk" />;
  }

  const summary = view.summary;

  return (
    <>
      <PageHeader
        eyebrow={`Decision desk · ${formatDateLong(date)}`}
        title="The forecast you actually had, and what it implies"
        description={
          <>
            Latest eligible WINDFOR vintage per hour, cutoff at <strong>{cutoff} London</strong> on
            D−1. Actuals stay hidden until you ask for hindsight. Use ← / → to change delivery day.
          </>
        }
        actions={
          <>
            <button className="btn" onClick={exportCsv} disabled={rows.length === 0}>
              Export day CSV
            </button>
            <Link className="btn btn-ghost" to={`/lab?cutoff=${encodeURIComponent(cutoff)}`}>
              Open in Accuracy Lab
            </Link>
          </>
        }
      />

      <section className="card mb-4 p-4" aria-label="Desk controls">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-12">
          <div className="lg:col-span-3">
            <DeliveryDatePicker
              date={date}
              dates={dates}
              onChange={setDate}
              previous={previous}
              next={next}
            />
          </div>
          <div className="lg:col-span-2">
            <CutoffSelect value={cutoff} options={meta.data.cutoff_grid} onChange={setCutoff} />
          </div>
          <div className="lg:col-span-2">
            <label className="label" htmlFor="risk-level">
              Risk level
            </label>
            <select
              id="risk-level"
              className="field w-full"
              value={riskLevel}
              onChange={(event) => setRiskLevel(Number(event.target.value))}
            >
              <option value={0.5}>P50 · median</option>
              <option value={0.75}>P75</option>
              <option value={0.9}>P90 · default</option>
              <option value={0.95}>P95</option>
            </select>
            <p className="mt-1 text-[11px] text-muted">Empirical signed-error buffer.</p>
          </div>
          <div className="lg:col-span-2">
            <label className="label" htmlFor="demand">
              Demand what-if (MW)
            </label>
            <input
              id="demand"
              className="field w-full"
              type="number"
              inputMode="numeric"
              min={0}
              step={100}
              placeholder="e.g. 24000"
              value={demandRaw}
              onChange={(event) => setDemandRaw(event.target.value)}
              aria-describedby="demand-help"
            />
            <p className="mt-1 text-[11px] text-muted" id="demand-help">
              Flat, user-entered; not Elexon data.
            </p>
          </div>
          <div className="lg:col-span-1">
            <Toggle
              label="Hindsight"
              checked={hindsight}
              onChange={setHindsight}
              hint="Show actuals"
            />
          </div>
          <div className="lg:col-span-2">
            <Toggle
              label="Risk band"
              checked={riskEnabled}
              onChange={setRiskEnabled}
              hint={`${levelLabel} shaded`}
            />
          </div>
        </div>
      </section>

      <section
        className="card mb-4 border-l-4 p-5"
        style={{ borderLeftColor: "var(--forecast)" }}
        aria-labelledby="decision-banner-title"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="eyebrow">Decision-time view{hindsight ? " · hindsight on" : ""}</p>
            <h2 className="mt-1 text-2xl" id="decision-banner-title">
              {deskHeadline(view)}
            </h2>
            <p className="mt-2 text-sm text-soft">{deskShapeInsight(view)}</p>
            {hindsight ? (
              <p className="mt-1 text-sm font-medium" style={{ color: "var(--over)" }}>
                {deskHindsightInsight(view)}
              </p>
            ) : null}
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div className="card-quiet px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-muted">Latest vintage</dt>
              <dd className="font-semibold">{formatTime(summary.latest_publish_time)}</dd>
            </div>
            <div className="card-quiet px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-muted">Horizon</dt>
              <dd className="font-semibold">
                {formatHorizon(summary.horizon_h.min)}–{formatHorizon(summary.horizon_h.max)}
              </dd>
            </div>
            <div className="card-quiet px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-muted">Forecast coverage</dt>
              <dd className="font-semibold">
                {view.coverage.with_forecast}/{view.coverage.expected_periods}
              </dd>
            </div>
            <div className="card-quiet px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-muted">Actual coverage</dt>
              <dd className="font-semibold">
                {hindsight
                  ? `${view.coverage.with_actual}/${view.coverage.expected_periods}`
                  : "hidden"}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {view.points.length === 0 ? (
        <EmptyState
          title="No forecast was published before this cutoff"
          message="Every delivery hour is missing an eligible WINDFOR vintage. Nothing has been filled or interpolated. Try a later cutoff or another day."
          action={
            <Link className="btn" to="/lab">
              Inspect window coverage
            </Link>
          }
        />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <KpiCard
              label="Mean wind"
              value={formatMW(summary.mean_mw)}
              sub={`${view.points.length} hourly points`}
              tone="forecast"
              hint="Arithmetic mean of the decision-time hourly forecast."
            />
            <KpiCard
              label="Peak"
              value={formatMW(summary.peak_mw)}
              sub={`at ${formatTime(summary.peak_time)} London`}
            />
            <KpiCard
              label="Trough"
              value={formatMW(summary.min_mw)}
              sub={`at ${formatTime(summary.min_time)} London`}
            />
            <KpiCard
              label="Forecast energy"
              value={formatEnergy(summary.energy_mwh)}
              sub="Σ hourly MW × 1 h"
              hint="Each point is a one-hour mean, so MWh equals MW × 1 h."
            />
            <KpiCard
              label="Largest 3 h ramp"
              value={formatMW(summary.max_ramp_3h_mw)}
              sub={`1 h: ${formatMW(summary.max_ramp_1h_mw)}`}
              hint="Largest absolute change between two hours three hours apart. The API also exposes the 1 h ramp."
            />
            <KpiCard
              label="Risk-adj. mean"
              value={formatMW(meanRiskAdjusted)}
              sub={`${levelLabel} buffer ${formatMW(overallBuffer)}`}
              tone="band"
              hint="Mean of max(0, hourly forecast − hourly empirical P90 buffer)."
            />
          </div>

          <div className="space-y-4">
            <ChartFrame
              id="forecast-chart"
              title={`Decision-time wind for ${formatDateLong(date)}`}
              insight={deskHeadline(view)}
              description={`Hourly decision-time wind forecast for ${formatDateLong(
                date,
              )}, ${view.points.length} points, ${formatMW(
                summary.min_mw,
              )} to ${formatMW(summary.peak_mw)}.`}
              actions={
                <button className="btn btn-ghost text-xs" onClick={exportCsv}>
                  Download CSV
                </button>
              }
              table={
                <DataTable
                  rows={rows}
                  columns={columns}
                  caption={`Decision-time hourly detail for ${date}`}
                  rowKey={(row) => row.point.start_time ?? String(row.point.horizon_h)}
                  emptyMessage="No hours to display."
                />
              }
              footnote="Forecast: latest WINDFOR vintage at or before the cutoff. Actual: FUELHH WIND averaged over the two half-hours. Sign: forecast − actual; positive means shortfall risk."
            >
              <ForecastChart
                view={view}
                buffer={buffer.data}
                level={riskLevel}
                includeActuals={hindsight}
                riskEnabled={riskEnabled}
                demandMw={demand}
              />
            </ChartFrame>

            <VintageStrip view={view} />

            <div className="grid gap-4 lg:grid-cols-2">
              <section className="card p-5" id="risk" aria-labelledby="desk-risk-title">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="eyebrow">Decision aid</p>
                    <h2 className="mt-1 text-2xl" id="desk-risk-title">
                      Risk buffer
                    </h2>
                  </div>
                  <span className="chip">{levelLabel}</span>
                </div>
                <p className="mt-2 text-sm text-soft">
                  {buffer.isError
                    ? humaniseProblem(buffer.error)
                    : buffer.data
                      ? riskBufferInsight(buffer.data, riskLevel)
                      : "Loading empirical buffers…"}
                </p>
                <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  {(buffer.data?.overall ?? []).map((point) => (
                    <div className="card-quiet px-3 py-2" key={point.level}>
                      <dt className="text-[11px] uppercase tracking-wide text-muted">
                        P{Math.round(point.level * 100)} buffer
                      </dt>
                      <dd className="font-semibold">{formatMW(point.buffer_mw)}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-4 border-t pt-3" style={{ borderColor: "var(--rule)" }}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                    Walk-forward check · {levelLabel}
                  </p>
                  <p className="mt-1 text-sm text-soft">
                    {backtest.data
                      ? backtestInsight(backtest.data)
                      : backtest.isError
                        ? humaniseProblem(backtest.error)
                        : "Loading back-test…"}
                  </p>
                  <Link className="mt-2 inline-block text-sm underline" to="/lab#risk">
                    Inspect calibration in the Lab
                  </Link>
                </div>
              </section>

              <section className="card p-5" aria-labelledby="demand-title">
                <p className="eyebrow">User-entered, clearly labelled</p>
                <h2 className="mt-1 text-2xl" id="demand-title">
                  Demand what-if
                </h2>
                <p className="mt-2 text-sm text-soft">
                  Enter flat demand to see the residual wind still to procure. This is a
                  hypothetical wedge, not a demand forecast and not Elexon data.
                </p>
                {demand === null ? (
                  <p className="mt-4 rounded-lg bg-sunken p-4 text-sm text-muted">
                    Add demand above to reveal residual-to-procure at the forecast and at the
                    risk-adjusted wind level.
                  </p>
                ) : (
                  <dl className="mt-4 grid gap-2 sm:grid-cols-2">
                    <div className="card-quiet px-3 py-3">
                      <dt className="text-[11px] uppercase tracking-wide text-muted">
                        Residual at forecast
                      </dt>
                      <dd className="mt-1 text-xl font-semibold">
                        {formatSignedMW(residualStats?.residualMean)}
                        <span className="mt-0.5 block text-[11px] font-normal text-muted">
                          demand {formatMW(demand)} − mean wind {formatMW(summary.mean_mw)}
                        </span>
                      </dd>
                    </div>
                    <div className="card-quiet px-3 py-3">
                      <dt className="text-[11px] uppercase tracking-wide text-muted">
                        Residual at risk-adjusted wind
                      </dt>
                      <dd className="mt-1 text-xl font-semibold" style={{ color: "var(--band-ink)" }}>
                        {formatSignedMW(residualStats?.residualRiskMean)}
                        <span className="mt-0.5 block text-[11px] font-normal text-muted">
                          A positive number is power still to procure.
                        </span>
                      </dd>
                    </div>
                    <div className="card-quiet px-3 py-3 sm:col-span-2">
                      <dt className="text-[11px] uppercase tracking-wide text-muted">
                        Largest hourly residual
                      </dt>
                      <dd className="mt-1 text-xl font-semibold">
                        {formatSignedMW(residualStats?.maxResidual)}
                        <span className="mt-0.5 block text-[11px] font-normal text-muted">
                          Peak residual across the delivery day at the decision-time forecast.
                        </span>
                      </dd>
                    </div>
                  </dl>
                )}
              </section>
            </div>

            <section className="card p-5" aria-labelledby="detail-title">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-xl font-semibold" id="detail-title">
                    Hourly detail
                  </h2>
                  <p className="text-sm text-soft">
                    Sort any column. All times London; raw UTC is retained in the CSV and tooltips.
                  </p>
                </div>
                <div className="flex gap-2">
                  <Link
                    className="btn btn-ghost text-xs"
                    to={revisionHref(date, 13, cutoff)}
                  >
                    Revisions for 12:00
                  </Link>
                  <a
                    className="btn btn-ghost text-xs"
                    href={`/api/v1/export/decision-view.csv?delivery_date=${encodeURIComponent(
                      date,
                    )}&cutoff=${encodeURIComponent(cutoff)}${
                      hindsight ? "&include_actuals=true" : ""
                    }`}
                  >
                    API CSV
                  </a>
                </div>
              </div>
              <div className="mt-3">
                <DataTable
                  rows={rows}
                  columns={columns}
                  caption={`Hourly decision-time detail for ${date}`}
                  rowKey={(row) => row.point.start_time ?? String(row.point.horizon_h)}
                />
              </div>
            </section>
          </div>
        </>
      )}

      <p className="mt-4 text-xs text-muted">
        Selected day {formatDateLong(date)} · cutoff {formatDateTime(view.cutoff.utc)} ·{" "}
        {formatCoverage(view.coverage.coverage_pct)} hourly forecast coverage.{" "}
        <Link className="underline" to={deskHref(date, cutoff)}>
          Permalink
        </Link>
        .
      </p>
    </>
  );
}

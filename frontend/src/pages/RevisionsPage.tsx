import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";

import { humaniseProblem } from "../api/client";
import { useDecisionView, useMeta, useRevisions } from "../api/hooks";
import { ChartFrame } from "../components/ChartFrame";
import { CutoffSelect, DeliveryDatePicker } from "../components/Controls";
import { KpiCard, PageHeader } from "../components/Metric";
import { EmptyState, ErrorState, PageSkeleton } from "../components/States";
import { RevisionChart } from "../components/RevisionChart";
import {
  formatDateLong,
  formatDateTime,
  formatHorizon,
  formatMW,
  formatSignedMW,
  formatTime,
  formatTimeUtc,
  londonHour,
} from "../lib/format";
import { revisionsInsight } from "../lib/insights";
import {
  deskHref,
  useCutoff,
  useRevisionTarget,
} from "../lib/urlState";

function periodLabel(period: number): string {
  return `${String(period - 1).padStart(2, "0")}:00–${String(period).padStart(2, "0")}:00`;
}

export function RevisionsPage() {
  const meta = useMeta();
  const [cutoff, setCutoff] = useCutoff();
  const target = useRevisionTarget(meta.data);
  const decision = useDecisionView(target.date, cutoff, false);
  const revisions = useRevisions(target.date, target.period, cutoff);

  const peakPeriod = useMemo(() => {
    const points = decision.data?.points ?? [];
    let best: { hour: number; value: number } | null = null;
    for (const point of points) {
      if (typeof point.forecast_mw !== "number") continue;
      const hour = londonHour(point.local_time);
      if (hour === null) continue;
      if (!best || point.forecast_mw > best.value) best = { hour, value: point.forecast_mw };
    }
    return best ? best.hour + 1 : null;
  }, [decision.data]);

  const { hasPeriod, setPeriod } = target;
  useEffect(() => {
    if (!hasPeriod && peakPeriod !== null) {
      setPeriod(peakPeriod);
    }
  }, [hasPeriod, setPeriod, peakPeriod]);

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
    return <PageSkeleton label="Loading the revisions explorer" />;
  }
  if (revisions.isError) {
    return (
      <ErrorState
        title="The revision history did not load"
        message={humaniseProblem(revisions.error)}
        onRetry={() => void revisions.refetch()}
      />
    );
  }
  if (!revisions.data) {
    return <PageSkeleton label="Loading the revision history" />;
  }

  const data = revisions.data;
  const selected = data.vintages.find((vintage) => vintage.selected);
  const eligibility = data.vintages.filter((vintage) => vintage.eligible);
  const postCutoff = data.vintages.length - eligibility.length;

  return (
    <>
      <PageHeader
        eyebrow="Revisions explorer · one target, every vintage"
        title="Which forecast was actually in hand?"
        description={
          <>
            Every WINDFOR publication for the selected delivery hour, with the decision cutoff
            drawn in. The highlighted vintage is the latest one at or before the cutoff. Later
            vintages are shown only to make the leakage boundary legible.
          </>
        }
        actions={
          <Link className="btn" to={deskHref(target.date, cutoff)}>
            Open day on the Desk
          </Link>
        }
      />

      <section className="card mb-4 p-4" aria-label="Revision controls">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-12">
          <div className="lg:col-span-3">
            <DeliveryDatePicker
              date={target.date}
              dates={target.dates}
              onChange={target.setDate}
              previous={
                target.dates.indexOf(target.date) > 0
                  ? (target.dates[target.dates.indexOf(target.date) - 1] ?? null)
                  : null
              }
              next={
                target.dates.indexOf(target.date) >= 0 &&
                target.dates.indexOf(target.date) < target.dates.length - 1
                  ? (target.dates[target.dates.indexOf(target.date) + 1] ?? null)
                  : null
              }
            />
          </div>
          <div className="lg:col-span-3">
            <label className="label" htmlFor="revision-period">
              Delivery hour
            </label>
            <select
              id="revision-period"
              className="field w-full"
              value={target.period}
              onChange={(event) => target.setPeriod(Number(event.target.value))}
            >
              {Array.from({ length: 24 }, (_, index) => index + 1).map((period) => (
                <option value={period} key={period}>
                  {periodLabel(period)} London
                </option>
              ))}
            </select>
            <p className="mt-1 text-[11px] text-muted">
              Period {target.period} of 24.{" "}
              {peakPeriod !== null && peakPeriod !== target.period ? (
                <button
                  type="button"
                  className="underline"
                  onClick={() => target.setPeriod(peakPeriod)}
                >
                  Jump to peak forecast (period {peakPeriod})
                </button>
              ) : null}
            </p>
          </div>
          <div className="lg:col-span-2">
            <CutoffSelect value={cutoff} options={meta.data.cutoff_grid} onChange={setCutoff} />
          </div>
          <div className="flex items-end lg:col-span-4">
            <p className="text-xs text-muted">
              The vintage list includes publications after the cutoff so you can see what the
              decision could not use. They never enter the forecast selection.
            </p>
          </div>
        </div>
      </section>

      {data.vintages.length === 0 ? (
        <EmptyState
          title="No WINDFOR vintages exist for this target"
          message="The snapshot has no publication for this delivery hour, so there is nothing to select. Choose another hour or day."
        />
      ) : (
        <>
          <section
            className="card mb-4 border-l-4 p-5"
            style={{ borderLeftColor: "var(--forecast)" }}
            aria-labelledby="revision-banner-title"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <p className="eyebrow">
                  Target {formatDateLong(data.delivery_date)} · {formatTime(data.target_time)} London
                </p>
                <h2 className="mt-1 text-2xl" id="revision-banner-title">
                  {revisionsInsight(data)}
                </h2>
                <p className="mt-2 text-sm text-soft">
                  Cutoff {data.cutoff.time} London on D−1 ({formatDateTime(data.cutoff.utc)}).{" "}
                  {eligibility.length} of {data.vintages.length} vintages were eligible;{" "}
                  {postCutoff} arrived after the cutoff. {data.eligibility_note}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <div className="card-quiet px-3 py-2">
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Selected</dt>
                  <dd className="font-semibold">{formatTime(data.selected_publish_time)}</dd>
                </div>
                <div className="card-quiet px-3 py-2">
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Horizon</dt>
                  <dd className="font-semibold">{formatHorizon(selected?.horizon_h)}</dd>
                </div>
                <div className="card-quiet px-3 py-2">
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Vintage UTC</dt>
                  <dd className="font-semibold">{formatTimeUtc(data.selected_publish_time)}</dd>
                </div>
                <div className="card-quiet px-3 py-2">
                  <dt className="text-[11px] uppercase tracking-wide text-muted">Look-ahead shown</dt>
                  <dd className="font-semibold">{formatHorizon(data.lookahead_hours, 0)}</dd>
                </div>
              </dl>
            </div>
          </section>

          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <KpiCard
              label="Selected forecast"
              value={formatMW(data.selected_forecast_mw)}
              sub={`vintage ${formatTime(data.selected_publish_time)} London`}
              tone="forecast"
              hint="The latest eligible WINDFOR forecast for this target at the chosen cutoff."
            />
            <KpiCard
              label="Actual outturn"
              value={formatMW(data.actual_mw)}
              sub="FUELHH WIND, hourly average"
              hint="Hindsight only. Two half-hour FUELHH settlement periods averaged without imputation."
            />
            <KpiCard
              label="Signed error"
              value={formatSignedMW(data.error_mw)}
              sub="Forecast − actual"
              tone={
                typeof data.error_mw === "number" && data.error_mw > 0 ? "over" : "under"
              }
              hint="Positive means over-forecast and shortfall risk for a buyer."
            />
            <KpiCard
              label="Vintage spread"
              value={formatMW(data.revision_range_mw.spread)}
              sub={`${formatMW(data.revision_range_mw.min)}–${formatMW(data.revision_range_mw.max)}`}
              hint="Range of forecast values across every vintage shown, including post-cutoff rows."
            />
            <KpiCard
              label="Revisions shown"
              value={String(data.vintages.length)}
              sub={`${eligibility.length} eligible · ${postCutoff} after cutoff`}
              hint="All WINDFOR publications returned for this target and look-ahead window."
            />
            <KpiCard
              label="Resolution"
              value={`${data.resolution_minutes} min`}
              sub="Hourly evaluation"
              hint="FUELHH is half-hourly; two periods are averaged into one hourly actual. WINDFOR is hourly."
            />
          </div>

          <ChartFrame
            id="revision-chart"
            title={`Vintages for ${formatTime(data.target_time)} London`}
            insight={revisionsInsight(data)}
            description="Scatter of forecast MW against publication time, with the decision cutoff marked as a vertical line and the actual outturn as a horizontal line."
            footnote="Source: WINDFOR vintages. Eligibility is inclusive of the cutoff; a publication exactly at the cutoff counts."
          >
            <RevisionChart revisions={data} />
          </ChartFrame>

          <section className="card mt-4 p-4" aria-labelledby="vintage-table-title">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-xl font-semibold" id="vintage-table-title">
                  Every vintage
                </h2>
                <p className="text-sm text-soft">
                  Publications after the cutoff are retained to show the leakage boundary. The
                  selected row is the latest eligible one.
                </p>
              </div>
              <span className="chip">{data.vintages.length} rows</span>
            </div>
            <div className="mt-3 table-wrap" style={{ maxHeight: "28rem" }} tabIndex={0} role="region" aria-label="Forecast vintages">
              <table className="data-table">
                <caption className="sr-only">
                  All forecast vintages for {formatDateLong(data.delivery_date)} at{" "}
                  {formatTime(data.target_time)} London
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Published (London)</th>
                    <th scope="col">Published (UTC)</th>
                    <th scope="col" className="text-right">
                      Forecast
                    </th>
                    <th scope="col" className="text-right">
                      Horizon
                    </th>
                    <th scope="col">Eligible</th>
                    <th scope="col">Selected</th>
                  </tr>
                </thead>
                <tbody>
                  {data.vintages.map((vintage) => (
                    <tr
                      key={`${vintage.publish_time}-${vintage.forecast_mw}`}
                      style={
                        vintage.selected
                          ? { background: "var(--band-soft)", fontWeight: 600 }
                          : vintage.eligible
                            ? undefined
                            : { color: "var(--ink-muted)" }
                      }
                    >
                      <td>{formatTime(vintage.publish_time)}</td>
                      <td className="font-mono text-xs">
                        {formatTimeUtc(vintage.publish_time)}
                      </td>
                      <td className="num">{formatMW(vintage.forecast_mw)}</td>
                      <td className="num">{formatHorizon(vintage.horizon_h)}</td>
                      <td>
                        {vintage.eligible ? (
                          "Yes"
                        ) : (
                          <span style={{ color: "var(--over)" }}>No — after cutoff</span>
                        )}
                      </td>
                      <td>
                        {vintage.selected ? (
                          <span className="chip" style={{ borderColor: "var(--band)" }}>
                            Selected
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card mt-4 p-4" aria-labelledby="why-title">
            <h2 className="text-xl font-semibold" id="why-title">
              Why this vintage?
            </h2>
            <p className="mt-1 text-sm text-soft">
              The rule is maximum <code>publish_time</code> subject to{" "}
              <code>publish_time ≤ cutoff</code>, evaluated separately for every target hour. It is
              not the newest row in the dataset, and it is not an interpolation between rows. A
              vintage published at exactly {data.cutoff.time} London would be included; one minute
              later would not.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link className="btn btn-primary" to={deskHref(data.delivery_date, cutoff)}>
                See the full day on the Desk
              </Link>
              <Link className="btn" to="/about#cutoff">
                Read the cutoff worked example
              </Link>
              <Link
                className="btn btn-ghost"
                to={`/lab?cutoff=${encodeURIComponent(cutoff)}`}
              >
                Accuracy at this cutoff
              </Link>
            </div>
          </section>
        </>
      )}

      <p className="mt-4 text-xs text-muted">
        Target {formatDateShortLocal(data.target_time_local)} · cutoff{" "}
        {formatDateTime(data.cutoff.utc)} · {data.vintages.length} vintages.{" "}
        {selected ? `Selected publication ${formatTimeUtc(selected.publish_time)}.` : ""}
      </p>
    </>
  );
}

function formatDateShortLocal(iso: string | null): string {
  if (!iso) return "—";
  return formatDateTime(iso);
}

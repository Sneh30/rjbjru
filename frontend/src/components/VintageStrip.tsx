import { formatTime } from "../lib/format";
import type { DecisionView } from "../types/api";

export function VintageStrip({ view }: { view: DecisionView }) {
  const publishTimes = Array.from(
    new Set(view.points.map((point) => point.publish_time).filter((value): value is string => Boolean(value))),
  ).sort();
  const indexByTime = new Map(publishTimes.map((time, index) => [time, index]));
  const count = Math.max(1, publishTimes.length - 1);
  return (
    <section className="card p-4" aria-labelledby="vintage-strip-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold" id="vintage-strip-title">
            Vintage strip
          </h2>
          <p className="text-sm text-soft">
            Which publication each delivery hour came from. Darker = later vintage. Every point is
            at or before the cutoff.
          </p>
        </div>
        <p className="text-xs text-muted">
          {publishTimes.length === 1
            ? `One vintage: ${formatTime(publishTimes[0])} London`
            : `${publishTimes.length} vintages · ${formatTime(publishTimes[0])} → ${formatTime(
                publishTimes[publishTimes.length - 1],
              )} London`}
        </p>
      </div>
      <div
        className="mt-3 grid gap-1"
        style={{ gridTemplateColumns: "repeat(24, minmax(0, 1fr))" }}
        role="list"
        aria-label="Publication vintage by delivery hour"
      >
        {view.points.map((point) => {
          const index = point.publish_time ? (indexByTime.get(point.publish_time) ?? 0) : 0;
          const opacity = 0.4 + (index / count) * 0.6;
          return (
            <div
              key={point.start_time ?? point.local_time ?? String(point.horizon_h)}
              role="listitem"
              className="spark-cell h-9 rounded-sm"
              style={{
                backgroundColor: `color-mix(in srgb, var(--forecast) ${Math.round(
                  opacity * 100,
                )}%, transparent)`,
              }}
              title={`${formatTime(point.local_time)} London · vintage ${formatTime(
                point.publish_time,
              )} · ${point.forecast_mw?.toLocaleString("en-GB") ?? "—"} MW`}
            />
          );
        })}
      </div>
      <div
        className="mt-1 grid gap-1 text-[10px] text-muted"
        style={{ gridTemplateColumns: "repeat(24, minmax(0, 1fr))" }}
        aria-hidden="true"
      >
        {view.points.map((point, index) => (
          <span key={point.start_time ?? String(index)} className="text-center">
            {index % 3 === 0 ? formatTime(point.local_time).slice(0, 2) : ""}
          </span>
        ))}
      </div>
      <p className="sr-only">
        Vintage strip: {view.points.length} hourly points.{" "}
        {view.points
          .map(
            (point) =>
              `${formatTime(point.local_time)} from ${formatTime(point.publish_time)} (${point.forecast_mw} MW)`,
          )
          .join("; ")}
        .
      </p>
    </section>
  );
}

import {
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import { formatDateTime, formatHorizon, formatMW, formatTime } from "../lib/format";
import type { RevisionVintage, RevisionsResponse } from "../types/api";

type RevisionPoint = RevisionVintage & {
  x: number;
  y: number | null;
};

function RevisionTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0]?.payload as RevisionPoint | undefined;
  if (!point) return null;
  return (
    <div className="chart-tooltip">
      <p className="font-semibold">{formatDateTime(point.publish_time)}</p>
      <dl className="mt-1 grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5">
        <dt className="text-muted">Forecast</dt>
        <dd className="text-right font-semibold">{formatMW(point.forecast_mw)}</dd>
        <dt className="text-muted">Horizon</dt>
        <dd className="text-right">{formatHorizon(point.horizon_h)}</dd>
        <dt className="text-muted">Eligible</dt>
        <dd className="text-right">{point.eligible ? "Yes" : "No — after cutoff"}</dd>
        <dt className="text-muted">Selected</dt>
        <dd className="text-right">{point.selected ? "Yes" : "No"}</dd>
      </dl>
    </div>
  );
}

export function RevisionChart({ revisions }: { revisions: RevisionsResponse }) {
  const points: RevisionPoint[] = revisions.vintages
    .filter((vintage): vintage is RevisionVintage & { publish_time: string } =>
      Boolean(vintage.publish_time),
    )
    .map((vintage) => ({
      ...vintage,
      x: new Date(vintage.publish_time).getTime(),
      y: vintage.forecast_mw,
    }))
    .filter((point) => Number.isFinite(point.x));
  const times = points.map((point) => point.x);
  const min = times.length ? Math.min(...times) : 0;
  const max = times.length ? Math.max(...times) : 1;
  const pad = Math.max((max - min) * 0.04, 15 * 60_000);
  const cutoffMs = revisions.cutoff.utc ? new Date(revisions.cutoff.utc).getTime() : null;
  const selected = points.filter((point) => point.selected);

  return (
    <div aria-hidden="true" style={{ width: "100%", height: 330 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 14, right: 18, left: 4, bottom: 10 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis
            type="number"
            dataKey="x"
            name="Published"
            domain={[min - pad, max + pad]}
            tickFormatter={(value: number) => formatTime(new Date(value).toISOString())}
            tickMargin={8}
            label={{ value: "Publication time (London)", position: "insideBottom", offset: -2, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Forecast"
            tickFormatter={(value: number) => value.toLocaleString("en-GB")}
            width={62}
            axisLine={false}
            tickLine={false}
            label={{ value: "Forecast MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <ZAxis range={[34, 34]} />
          <Tooltip content={<RevisionTooltip />} />
          <Legend verticalAlign="top" height={28} />
          {cutoffMs !== null && Number.isFinite(cutoffMs) ? (
            <ReferenceLine
              x={cutoffMs}
              stroke="var(--over)"
              strokeWidth={2}
              strokeDasharray="6 4"
              ifOverflow="extendDomain"
            />
          ) : null}
          {typeof revisions.actual_mw === "number" ? (
            <ReferenceLine
              y={revisions.actual_mw}
              stroke="var(--actual)"
              strokeWidth={1.6}
              strokeDasharray="3 3"
              label={{ value: "Actual", position: "insideTopRight", fontSize: 10 }}
            />
          ) : null}
          <Scatter
            data={points}
            name="All vintages"
            fill="var(--forecast)"
            fillOpacity={0.5}
            isAnimationActive={false}
          />
          <Scatter
            data={selected}
            name="Selected vintage"
            fill="var(--band)"
            stroke="var(--ink)"
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

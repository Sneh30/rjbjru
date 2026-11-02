import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import { formatHorizon, formatMW, formatSignedMW, formatTime, londonHour } from "../lib/format";
import type { BufferResponse, DecisionView } from "../types/api";

type ChartPoint = {
  label: string;
  fullLabel: string;
  forecast: number | null;
  actual: number | null;
  bandBase: number | null;
  bandSpan: number | null;
  shortfall: number | null;
  under: number | null;
  demand: number | null;
  publish: string | null;
  horizon: number;
  hour: number | null;
  localIso: string | null;
  error: number | null;
};

function ForecastTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0]?.payload as ChartPoint | undefined;
  if (!point) return null;
  return (
    <div className="chart-tooltip">
      <p className="font-semibold">{point.fullLabel}</p>
      <dl className="mt-1 grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5">
        <dt className="text-muted">Forecast</dt>
        <dd className="text-right font-semibold">{formatMW(point.forecast)}</dd>
        {point.bandBase !== null && point.bandSpan !== null ? (
          <>
            <dt className="text-muted">Risk-adjusted</dt>
            <dd className="text-right">{formatMW(point.bandBase)}</dd>
            <dt className="text-muted">Buffer</dt>
            <dd className="text-right">{formatMW(point.bandSpan)}</dd>
          </>
        ) : null}
        {point.actual !== null ? (
          <>
            <dt className="text-muted">Actual</dt>
            <dd className="text-right">{formatMW(point.actual)}</dd>
            <dt className="text-muted">Error</dt>
            <dd className="text-right">{formatSignedMW(point.error)}</dd>
          </>
        ) : null}
        {point.demand !== null ? (
          <>
            <dt className="text-muted">Demand what-if</dt>
            <dd className="text-right">{formatMW(point.demand)}</dd>
          </>
        ) : null}
        <dt className="text-muted">Vintage</dt>
        <dd className="text-right">{formatTime(point.publish)}</dd>
        <dt className="text-muted">Horizon</dt>
        <dd className="text-right">{formatHorizon(point.horizon)}</dd>
      </dl>
    </div>
  );
}

function buildData(
  view: DecisionView,
  buffer: BufferResponse | undefined,
  level: number,
  includeActuals: boolean,
  riskEnabled: boolean,
  demandMw: number | null,
): ChartPoint[] {
  const buffersByHour = new Map<number, number>();
  if (buffer) {
    for (const row of buffer.by_hour) {
      const point = row.buffers.find((entry) => entry.level === level);
      if (point && typeof point.buffer_mw === "number") {
        buffersByHour.set(row.hour, point.buffer_mw);
      }
    }
  }
  return view.points.map((point) => {
    const hour = londonHour(point.local_time);
    const bufferValue = riskEnabled && hour !== null ? buffersByHour.get(hour) : undefined;
    const canBand =
      typeof point.forecast_mw === "number" && typeof bufferValue === "number" && bufferValue >= 0;
    const actual = includeActuals && typeof point.actual_mw === "number" ? point.actual_mw : null;
    const error = includeActuals && typeof point.error_mw === "number" ? point.error_mw : null;
    return {
      label: formatTime(point.local_time),
      fullLabel: `${view.delivery_date_local} ${formatTime(point.local_time)} London`,
      forecast: point.forecast_mw,
      actual,
      bandBase: canBand ? (point.forecast_mw ?? 0) - (bufferValue ?? 0) : null,
      bandSpan: canBand ? bufferValue : null,
      shortfall: error !== null && error > 0 ? error : null,
      under: error !== null && error < 0 ? error : null,
      demand: demandMw,
      publish: point.publish_time,
      horizon: point.horizon_h,
      hour,
      localIso: point.local_time,
      error,
    };
  });
}

export function ForecastChart({
  view,
  buffer,
  level,
  includeActuals,
  riskEnabled,
  demandMw,
}: {
  view: DecisionView;
  buffer?: BufferResponse;
  level: number;
  includeActuals: boolean;
  riskEnabled: boolean;
  demandMw: number | null;
}) {
  const data = buildData(view, buffer, level, includeActuals, riskEnabled, demandMw);
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 360 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="label"
            interval={2}
            tickMargin={8}
            axisLine
            tickLine={false}
            label={{
              value: "London local time",
              position: "insideBottom",
              offset: -2,
              fontSize: 11,
            }}
          />
          <YAxis
            tickFormatter={(value: number) => value.toLocaleString("en-GB")}
            width={62}
            axisLine={false}
            tickLine={false}
            label={{ value: "MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip content={<ForecastTooltip />} />
          <Legend verticalAlign="top" height={30} iconType="plainline" />
          <ReferenceLine y={0} stroke="var(--rule-strong)" />
          {riskEnabled ? (
            <>
              <Area
                type="monotone"
                dataKey="bandBase"
                stackId="band"
                stroke="none"
                fill="transparent"
                isAnimationActive={false}
                legendType="none"
                name="band base"
              />
              <Area
                type="monotone"
                dataKey="bandSpan"
                stackId="band"
                stroke="none"
                fill="var(--band)"
                fillOpacity={0.28}
                isAnimationActive={false}
                name={`Risk band P${Math.round(level * 100)}`}
              />
            </>
          ) : null}
          {includeActuals ? (
            <>
              <Area
                type="monotone"
                dataKey="shortfall"
                stroke="none"
                fill="var(--over)"
                fillOpacity={0.18}
                isAnimationActive={false}
                legendType="none"
                name="shortfall"
              />
              <Area
                type="monotone"
                dataKey="under"
                stroke="none"
                fill="var(--under)"
                fillOpacity={0.18}
                isAnimationActive={false}
                legendType="none"
                name="under-forecast"
              />
            </>
          ) : null}
          <Line
            type="monotone"
            dataKey="forecast"
            name="Decision-time forecast"
            stroke="var(--forecast)"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
          {includeActuals ? (
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual (hindsight)"
              stroke="var(--actual)"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              isAnimationActive={false}
            />
          ) : null}
          {demandMw !== null && demandMw > 0 ? (
            <Line
              type="monotone"
              dataKey="demand"
              name="Demand what-if"
              stroke="var(--demand)"
              strokeWidth={1.8}
              strokeDasharray="2 4"
              dot={false}
              isAnimationActive={false}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

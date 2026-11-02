import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import {
  formatMonthDay,
  formatMW,
  formatNumber,
  formatPct,
  isFiniteNumber,
} from "../lib/format";
import type {
  BufferPoint,
  DailyRow,
  DistributionResponse,
  HorizonBucket,
  HourRow,
  LevelBin,
  ScatterDatum,
} from "../types/api";

const TOOLTIP_STYLE = {
  background: "var(--paper-raised)",
  border: "1px solid var(--rule-strong)",
  borderRadius: 10,
  color: "var(--ink)",
  fontSize: 12,
};

export function DailyTrendChart({
  days,
  onSelect,
}: {
  days: DailyRow[];
  onSelect: (date: string) => void;
}) {
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={days}
          margin={{ top: 10, right: 12, left: 4, bottom: 8 }}
          onClick={(state) => {
            const payload = state?.activePayload?.[0]?.payload as DailyRow | undefined;
            if (payload) onSelect(payload.delivery_date);
          }}
        >
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="delivery_date"
            tickFormatter={(value: string) => formatMonthDay(value)}
            interval={2}
            tickMargin={8}
          />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={(label: string) => formatMonthDay(label)}
            formatter={(value, name) => [formatMW(Number(value)), name]}
          />
          <ReferenceLine y={0} stroke="var(--rule-strong)" />
          <Bar
            dataKey="mae_mw"
            name="Daily MAE"
            fill="var(--forecast)"
            radius={[3, 3, 0, 0]}
            cursor="pointer"
            isAnimationActive={false}
          />
          <Line
            dataKey="bias_mw"
            name="Bias"
            stroke="var(--over)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function bandLabels(buckets: HorizonBucket[], min: number, max: number): [string, string] | null {
  const inside = buckets.filter((bucket) => {
    const to = bucket.to_h ?? Number.POSITIVE_INFINITY;
    return bucket.n > 0 && to > min && bucket.from_h <= max;
  });
  if (inside.length === 0) return null;
  const first = inside[0];
  const last = inside[inside.length - 1];
  return first && last ? [first.label, last.label] : null;
}

export function HorizonChart({
  buckets,
  band,
}: {
  buckets: HorizonBucket[];
  band: { min: number; max: number } | null;
}) {
  const shaded = band ? bandLabels(buckets, band.min, band.max) : null;
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={buckets} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => `${value}%`}
            width={48}
            axisLine={false}
            tickLine={false}
            label={{ value: "nMAE", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [formatPct(Number(value)), name]}
          />
          {shaded ? (
            <ReferenceArea
              x1={shaded[0]}
              x2={shaded[1]}
              fill="var(--band)"
              fillOpacity={0.16}
              label={{ value: "Decision-time band", position: "insideTop", fontSize: 10 }}
            />
          ) : null}
          <Bar
            dataKey="nmae_pct"
            name="nMAE"
            fill="var(--forecast)"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HourChart({ hours }: { hours: HourRow[] }) {
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={hours} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" interval={2} tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [formatMW(Number(value)), name]}
          />
          <ReferenceLine y={0} stroke="var(--rule-strong)" />
          <Bar
            dataKey="mae_mw"
            name="MAE"
            fill="var(--forecast)"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Line
            dataKey="bias_mw"
            name="Bias"
            stroke="var(--over)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LevelChart({ bins }: { bins: LevelBin[] }) {
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={bins} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "MAE (MW)", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [formatMW(Number(value)), name]}
            labelFormatter={(label: string) => {
              const bin = bins.find((candidate) => candidate.label === label);
              return bin ? `${bin.label}: ${formatMW(bin.from_mw)}–${formatMW(bin.to_mw)}` : label;
            }}
          />
          <Bar
            dataKey="mae_mw"
            name="MAE"
            fill="var(--forecast)"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ErrorHistogram({ distribution }: { distribution: DistributionResponse }) {
  const data = distribution.histogram.map((bin, index) => ({
    ...bin,
    label: `${formatNumber(bin.from_mw)}…${formatNumber(bin.to_mw)}`,
    mid: index,
  }));
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="mid" tickFormatter={(value: number) => data[value]?.label ?? ""} interval={3} tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={44}
            axisLine={false}
            tickLine={false}
            label={{ value: "Hours", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelFormatter={(value) => `Error ${data[Number(value)]?.label ?? ""} MW`}
            formatter={(value) => [formatNumber(Number(value)), "Hours"]}
          />
          <ReferenceLine x={0} stroke="var(--over)" />
          <Bar
            dataKey="count"
            name="Hours"
            fill="var(--forecast)"
            radius={[2, 2, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ScatterPlot({ distribution }: { distribution: DistributionResponse }) {
  const scatter = distribution.scatter.filter(
    (point): point is ScatterDatum & { forecast_mw: number; actual_mw: number } =>
      isFiniteNumber(point.forecast_mw) && isFiniteNumber(point.actual_mw),
  );
  const values = scatter.flatMap((point) => [point.forecast_mw, point.actual_mw]);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const padding = (max - min) * 0.04;
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" />
          <XAxis
            type="number"
            dataKey="forecast_mw"
            name="Forecast"
            domain={[min - padding, max + padding]}
            tickFormatter={(value: number) => formatNumber(value)}
            tickMargin={8}
            label={{ value: "Forecast MW", position: "insideBottom", offset: -2, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="actual_mw"
            name="Actual"
            domain={[min - padding, max + padding]}
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "Actual MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <ZAxis range={[12, 12]} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [formatMW(Number(value)), name]}
          />
          <ReferenceLine
            segment={[
              { x: min, y: min },
              { x: max, y: max },
            ]}
            stroke="var(--actual)"
            strokeDasharray="5 4"
          />
          <Scatter
            data={scatter}
            name="Hours"
            fill="var(--forecast)"
            fillOpacity={0.42}
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BufferLevelChart({ points }: { points: BufferPoint[] }) {
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 220 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={points.map((point) => ({
            ...point,
            label: `P${Math.round(point.level * 100)}`,
          }))}
          margin={{ top: 10, right: 12, left: 4, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "Buffer MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value) => [formatMW(Number(value)), "Buffer"]}
          />
          <Bar
            dataKey="buffer_mw"
            name="Buffer"
            fill="var(--band)"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HourlyBufferChart({
  rows,
  level,
}: {
  rows: { hour: number; buffers: BufferPoint[] }[];
  level: number;
}) {
  const data = rows.map((row) => ({
    hour: `${String(row.hour).padStart(2, "0")}:00`,
    buffer: row.buffers.find((point) => point.level === level)?.buffer_mw ?? null,
  }));
  return (
    <div aria-hidden="true" style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 12, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="hour" interval={2} tickMargin={8} />
          <YAxis
            tickFormatter={(value: number) => formatNumber(value)}
            width={58}
            axisLine={false}
            tickLine={false}
            label={{ value: "Buffer MW", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value) => [formatMW(Number(value)), "Buffer"]}
          />
          <Bar
            dataKey="buffer"
            name="Buffer"
            fill="var(--band)"
            radius={[2, 2, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

import type { ReactNode } from "react";

import { InfoTip } from "./InfoTip";

export function KpiCard({
  label,
  value,
  sub,
  tone = "neutral",
  hint,
}: {
  label: string;
  value: string;
  sub?: ReactNode;
  tone?: "neutral" | "forecast" | "over" | "under" | "band";
  hint?: string;
}) {
  const toneColour =
    tone === "forecast"
      ? "var(--forecast)"
      : tone === "over"
        ? "var(--over)"
        : tone === "under"
          ? "var(--under)"
          : tone === "band"
            ? "var(--band-ink)"
            : "var(--ink)";
  return (
    <div className="card flex min-h-[7.5rem] flex-col justify-between p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="eyebrow">{label}</p>
        {hint ? <InfoTip label={label}>{hint}</InfoTip> : null}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight" style={{ color: toneColour }}>
        {value}
      </p>
      {sub ? <p className="mt-1 text-xs text-muted">{sub}</p> : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 pb-5">
      <div className="max-w-3xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-1 text-3xl leading-tight sm:text-4xl">{title}</h1>
        <p className="mt-2 text-soft">{description}</p>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function StatRow({
  items,
}: {
  items: { label: string; value: string; tone?: "over" | "under" | "neutral" }[];
}) {
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {items.map((item) => (
        <div className="card-quiet p-3" key={item.label}>
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            {item.label}
          </dt>
          <dd
            className="mt-1 text-lg font-semibold"
            style={{
              color:
                item.tone === "over"
                  ? "var(--over)"
                  : item.tone === "under"
                    ? "var(--under)"
                    : "var(--ink)",
            }}
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

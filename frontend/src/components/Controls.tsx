import { useId } from "react";

import { formatDateLong } from "../lib/format";

export function DeliveryDatePicker({
  date,
  dates,
  onChange,
  previous,
  next,
}: {
  date: string;
  dates: string[];
  onChange: (value: string) => void;
  previous: string | null;
  next: string | null;
}) {
  const id = useId();
  const min = dates[0];
  const max = dates[dates.length - 1];
  return (
    <div>
      <label className="label" htmlFor={id}>
        Delivery day
      </label>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          className="btn px-2"
          onClick={() => previous && onChange(previous)}
          disabled={!previous}
          aria-label="Previous delivery day"
        >
          ←
        </button>
        <input
          id={id}
          type="date"
          className="field w-full min-w-[9.5rem]"
          value={date}
          min={min}
          max={max}
          onChange={(event) => {
            if (event.target.value) onChange(event.target.value);
          }}
          aria-describedby={`${id}-help`}
        />
        <button
          type="button"
          className="btn px-2"
          onClick={() => next && onChange(next)}
          disabled={!next}
          aria-label="Next delivery day"
        >
          →
        </button>
      </div>
      <p className="mt-1 text-[11px] text-muted" id={`${id}-help`}>
        {formatDateLong(date)} · {dates.length} in scope
      </p>
    </div>
  );
}

export function CutoffSelect({
  value,
  options,
  onChange,
  label = "Decision cutoff (D−1)",
}: {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  label?: string;
}) {
  const id = useId();
  const choices = Array.from(new Set([...options, value])).sort();
  return (
    <div>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="field w-full"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {choices.map((option) => (
          <option key={option} value={option}>
            {option} London
          </option>
        ))}
      </select>
      <p className="mt-1 text-[11px] text-muted">London time on the day before delivery.</p>
    </div>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  hint?: string;
}) {
  const id = useId();
  return (
    <div>
      <span className="label">{label}</span>
      <label
        htmlFor={id}
        className="flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-2.5 text-sm"
        style={{ borderColor: "var(--rule-strong)" }}
      >
        <input
          id={id}
          type="checkbox"
          role="switch"
          aria-label={label}
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="h-4 w-4 accent-[var(--forecast)]"
        />
        <span>{checked ? "On" : "Off"}</span>
      </label>
      {hint ? <p className="mt-1 text-[11px] text-muted">{hint}</p> : null}
    </div>
  );
}

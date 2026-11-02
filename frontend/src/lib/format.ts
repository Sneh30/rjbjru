/** Number, date and unit formatting. One place so every view agrees. */

const LONDON = "Europe/London";
const NBSP = "\u00a0";

const dateLong = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  weekday: "short",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const dateShort = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  day: "2-digit",
  month: "short",
});

const timeShort = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const dateTimeLong = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZoneName: "short",
});

export function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function formatMW(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  return `${value.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}${NBSP}MW`;
}

export function formatMWValue(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  return value.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatSignedMW(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${formatMW(Math.abs(value), digits)}`;
}

export function formatPct(value: number | null | undefined, digits = 1): string {
  if (!isFiniteNumber(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatShare(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSignedShare(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${(Math.abs(value) * 100).toFixed(digits)} pp`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (!isFiniteNumber(value)) return "—";
  return value.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatHorizon(value: number | null | undefined, digits = 1): string {
  if (!isFiniteNumber(value)) return "—";
  return `${value.toFixed(digits)}${NBSP}h`;
}

export function formatDateLong(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const parsed = parseDateOnly(isoDate);
  if (!parsed) return "—";
  return dateLong.format(parsed);
}

export function formatDateShort(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const parsed = parseDateOnly(isoDate);
  if (!parsed) return "—";
  return dateShort.format(parsed);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  return dateTimeLong.format(parsed);
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  return timeShort.format(parsed);
}

export function formatTimeUtc(iso: string | null | undefined): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  return `${parsed.toISOString().slice(11, 16)}${NBSP}UTC`;
}

export function londonHour(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return null;
  const hour = new Intl.DateTimeFormat("en-GB", {
    timeZone: LONDON,
    hour: "2-digit",
    hourCycle: "h23",
  }).format(parsed);
  const value = Number.parseInt(hour, 10);
  return Number.isFinite(value) ? value : null;
}

export function londonDateKey(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: LONDON,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(parsed);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function formatMonthDay(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const parsed = parseDateOnly(isoDate);
  if (!parsed) return "—";
  return dateShort.format(parsed);
}

export function formatPeakTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return `${formatTime(iso)} London`;
}

export function formatEnergy(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return "—";
  return `${formatNumber(value, 0)}${NBSP}MWh`;
}

export function formatCoverage(value: number | null | undefined): string {
  return formatPct(value, 1);
}

export function addDays(isoDate: string, days: number): string {
  const parsed = parseDateOnly(isoDate);
  if (!parsed) return isoDate;
  const utc = new Date(Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate()));
  utc.setUTCDate(utc.getUTCDate() + days);
  return utc.toISOString().slice(0, 10);
}

export function clampDate(isoDate: string, dates: string[]): string {
  if (dates.length === 0) return isoDate;
  if (dates.includes(isoDate)) return isoDate;
  return dates[dates.length - 1] ?? isoDate;
}

export function parseDateOnly(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const [, year, month, day] = match;
  if (!year || !month || !day) return null;
  return new Date(`${year}-${month}-${day}T12:00:00Z`);
}

export function shortHash(hash: string | null | undefined): string {
  if (!hash) return "—";
  return hash.slice(0, 12);
}

export function pluralise(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}

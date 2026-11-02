import { describe, expect, it } from "vitest";

import {
  addDays,
  clampDate,
  formatCoverage,
  formatDateLong,
  formatDateShort,
  formatDateTime,
  formatEnergy,
  formatHorizon,
  formatMonthDay,
  formatMW,
  formatMWValue,
  formatNumber,
  formatPct,
  formatPeakTime,
  formatShare,
  formatSignedMW,
  formatSignedShare,
  formatTime,
  formatTimeUtc,
  isFiniteNumber,
  londonDateKey,
  londonHour,
  parseDateOnly,
  pluralise,
  shortHash,
} from "../lib/format";

describe("number formatting", () => {
  it("formats megawatts with a non-breaking space and em dash for missing values", () => {
    expect(formatMW(1234.4)).toBe("1,234\u00a0MW");
    expect(formatMW(1234.44, 1)).toBe("1,234.4\u00a0MW");
    expect(formatMW(null)).toBe("—");
    expect(formatMW(Number.NaN)).toBe("—");
    expect(formatMWValue(9876.5)).toBe("9,877");
  });

  it("formats signed values with a true minus sign", () => {
    expect(formatSignedMW(42)).toBe("+42\u00a0MW");
    expect(formatSignedMW(-42)).toBe("−42\u00a0MW");
    expect(formatSignedMW(0)).toBe("0\u00a0MW");
    expect(formatSignedMW(undefined)).toBe("—");
  });

  it("formats percentages, shares and signed percentage points", () => {
    expect(formatPct(18.066)).toBe("18.1%");
    expect(formatPct(null)).toBe("—");
    expect(formatShare(0.856)).toBe("86%");
    expect(formatShare(0.856, 1)).toBe("85.6%");
    expect(formatSignedShare(0.02)).toBe("+2 pp");
    expect(formatSignedShare(-0.021)).toBe("−2 pp");
    expect(formatCoverage(100)).toBe("100.0%");
  });

  it("formats ordinary numbers, energy, horizons and plural counts", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
    expect(formatNumber(1234.5, 1)).toBe("1,234.5");
    expect(formatEnergy(1234.6)).toBe("1,235\u00a0MWh");
    expect(formatEnergy(null)).toBe("—");
    expect(formatHorizon(28.54)).toBe("28.5\u00a0h");
    expect(formatHorizon(28.54, 0)).toBe("29\u00a0h");
    expect(formatHorizon(null)).toBe("—");
    expect(pluralise(1, "day")).toBe("1 day");
    expect(pluralise(2, "day")).toBe("2 days");
    expect(pluralise(2, "vintage", "vintages")).toBe("2 vintages");
  });

  it("recognises only finite numbers", () => {
    expect(isFiniteNumber(0)).toBe(true);
    expect(isFiniteNumber(-1.5)).toBe(true);
    expect(isFiniteNumber(null)).toBe(false);
    expect(isFiniteNumber(undefined)).toBe(false);
    expect(isFiniteNumber(Number.POSITIVE_INFINITY)).toBe(false);
    expect(isFiniteNumber(Number.NaN)).toBe(false);
  });
});

describe("date and time formatting", () => {
  it("parses date-only values at noon UTC to avoid DST edges", () => {
    expect(parseDateOnly("2026-01-15")?.toISOString()).toBe("2026-01-15T12:00:00.000Z");
    expect(parseDateOnly("2026-02-30")).not.toBeNull();
    expect(parseDateOnly("15/01/2026")).toBeNull();
    expect(parseDateOnly("2026-1-5")).toBeNull();
  });

  it("formats London dates regardless of the process timezone", () => {
    expect(formatDateLong("2026-01-15")).toBe("Thu, 15 Jan 2026");
    expect(formatDateShort("2026-02-01")).toBe("01 Feb");
    expect(formatMonthDay("2026-01-02")).toBe("02 Jan");
    expect(formatDateLong(null)).toBe("—");
    expect(formatDateLong("not-a-date")).toBe("—");
  });

  it("formats instants in Europe/London and UTC", () => {
    expect(formatDateTime("2026-01-14T09:00:00Z")).toBe("14 Jan 2026, 09:00 GMT");
    expect(formatTime("2026-01-14T09:00:00Z")).toBe("09:00");
    expect(formatTimeUtc("2026-01-14T09:00:00Z")).toBe("09:00\u00a0UTC");
    expect(formatPeakTime("2026-01-15T12:00:00Z")).toBe("12:00 London");
    expect(formatTime("nonsense")).toBe("—");
    expect(formatTimeUtc(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
  });

  it("extracts London hours and date keys across the UTC offset", () => {
    expect(londonHour("2026-01-14T23:30:00Z")).toBe(23);
    expect(londonHour("2026-07-01T23:30:00Z")).toBe(0);
    expect(londonHour("bad")).toBeNull();
    expect(londonDateKey("2026-01-31T23:30:00Z")).toBe("2026-01-31");
    expect(londonDateKey("2026-07-31T23:30:00Z")).toBe("2026-08-01");
    expect(londonDateKey(null)).toBeNull();
  });

  it("does calendar arithmetic and clamps to the available range", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
    expect(addDays("not-a-date", 1)).toBe("not-a-date");
    expect(clampDate("2026-01-15", ["2026-01-02", "2026-02-01"])).toBe("2026-02-01");
    expect(clampDate("2026-01-15", ["2026-01-02", "2026-02-01", "2099-01-01"])).toBe("2099-01-01");
    expect(clampDate("2026-01-02", ["2026-01-02", "2026-02-01"])).toBe("2026-01-02");
    expect(clampDate("2026-01-02", [])).toBe("2026-01-02");
  });

  it("shortens a fingerprint and handles missing hashes", () => {
    expect(shortHash("331dc8acb133704a")).toBe("331dc8acb133");
    expect(shortHash(null)).toBe("—");
  });
});

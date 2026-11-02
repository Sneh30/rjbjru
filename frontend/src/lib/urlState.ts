import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { Meta } from "../types/api";

export const DEFAULT_CUTOFF = "09:00";
export const DEFAULT_PERIOD = 13;

function useParam(key: string): [string | null, (value: string | null) => void] {
  const [params, setParams] = useSearchParams();
  const value = params.get(key);
  const setValue = useCallback(
    (next: string | null) => {
      setParams(
        (current) => {
          const copy = new URLSearchParams(current);
          if (next === null || next === "") copy.delete(key);
          else copy.set(key, next);
          return copy;
        },
        { replace: true },
      );
    },
    [key, setParams],
  );
  return [value, setValue];
}

export function useCutoff(): [string, (value: string) => void] {
  const [raw, setRaw] = useParam("cutoff");
  const setCutoff = useCallback((value: string) => setRaw(value), [setRaw]);
  return [raw ?? DEFAULT_CUTOFF, setCutoff];
}

export function useDeliveryDate(meta: Meta | undefined): {
  date: string;
  setDate: (value: string) => void;
  dates: string[];
  previous: string | null;
  next: string | null;
} {
  const [raw, setRaw] = useParam("date");
  const dates = useMemo(() => meta?.available_delivery_dates ?? [], [meta]);
  const fallback = dates.length > 0 ? (dates[dates.length - 1] ?? "") : "";
  const date = useMemo(() => {
    if (raw && (dates.length === 0 || dates.includes(raw))) return raw;
    return fallback;
  }, [raw, dates, fallback]);
  const index = dates.indexOf(date);
  const setDate = useCallback((value: string) => setRaw(value), [setRaw]);
  return {
    date,
    setDate,
    dates,
    previous: index > 0 ? (dates[index - 1] ?? null) : null,
    next: index >= 0 && index < dates.length - 1 ? (dates[index + 1] ?? null) : null,
  };
}

export function useRevisionTarget(meta: Meta | undefined): {
  date: string;
  setDate: (value: string) => void;
  period: number;
  setPeriod: (value: number) => void;
  hasPeriod: boolean;
  dates: string[];
} {
  const delivery = useDeliveryDate(meta);
  const [rawPeriod, setRawPeriod] = useParam("period");
  const parsed = rawPeriod ? Number.parseInt(rawPeriod, 10) : DEFAULT_PERIOD;
  const period = Number.isFinite(parsed) && parsed >= 1 && parsed <= 24 ? parsed : DEFAULT_PERIOD;
  const setPeriod = useCallback(
    (value: number) => setRawPeriod(String(Math.min(24, Math.max(1, value)))),
    [setRawPeriod],
  );
  return {
    date: delivery.date,
    setDate: delivery.setDate,
    period,
    setPeriod,
    hasPeriod: rawPeriod !== null,
    dates: delivery.dates,
  };
}

export function useWindow(meta: Meta | undefined): {
  start: string;
  end: string;
  setStart: (value: string) => void;
  setEnd: (value: string) => void;
  reset: () => void;
  isDefault: boolean;
} {
  const [params, setParams] = useSearchParams();
  const rawStart = params.get("start");
  const rawEnd = params.get("end");
  const defaultStart = meta?.scope.delivery_dates.start ?? "";
  const defaultEnd = meta?.scope.delivery_dates.end ?? "";
  const start = rawStart ?? defaultStart;
  const end = rawEnd ?? defaultEnd;
  const setStart = useCallback(
    (value: string) => {
      setParams(
        (current) => {
          const copy = new URLSearchParams(current);
          if (value === "") copy.delete("start");
          else copy.set("start", value);
          return copy;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  const setEnd = useCallback(
    (value: string) => {
      setParams(
        (current) => {
          const copy = new URLSearchParams(current);
          if (value === "") copy.delete("end");
          else copy.set("end", value);
          return copy;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  const reset = useCallback(() => {
    setParams(
      (current) => {
        const copy = new URLSearchParams(current);
        copy.delete("start");
        copy.delete("end");
        return copy;
      },
      { replace: true },
    );
  }, [setParams]);
  return {
    start,
    end,
    setStart,
    setEnd,
    reset,
    isDefault: start === defaultStart && end === defaultEnd,
  };
}

export function useBooleanParam(
  key: string,
  fallback = false,
): [boolean, (value: boolean) => void] {
  const [raw, setRaw] = useParam(key);
  const value = raw === null ? fallback : raw === "1" || raw === "true";
  const setValue = useCallback(
    (next: boolean) => {
      if (next === fallback) setRaw(null);
      else setRaw(next ? "1" : "0");
    },
    [fallback, setRaw],
  );
  return [value, setValue];
}

export function useRiskLevel(): [number, (value: number) => void] {
  const [raw, setRaw] = useParam("risk");
  const parsed = raw ? Number.parseFloat(raw) : 0.9;
  const level = [0.5, 0.75, 0.9, 0.95].includes(parsed) ? parsed : 0.9;
  const setLevel = useCallback((value: number) => setRaw(String(value)), [setRaw]);
  return [level, setLevel];
}

export function useLabBasis(): ["actual" | "forecast", (value: "actual" | "forecast") => void] {
  const [raw, setRaw] = useParam("basis");
  const basis = raw === "forecast" ? "forecast" : "actual";
  const setBasis = useCallback((value: "actual" | "forecast") => setRaw(value), [setRaw]);
  return [basis, setBasis];
}

export function deskHref(date: string, cutoff: string): string {
  return `/desk?date=${encodeURIComponent(date)}&cutoff=${encodeURIComponent(cutoff)}`;
}

export function revisionHref(date: string, period: number, cutoff: string): string {
  return `/revisions?date=${encodeURIComponent(date)}&period=${String(period)}&cutoff=${encodeURIComponent(cutoff)}`;
}

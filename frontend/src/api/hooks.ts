import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getJson, type QueryParams } from "./client";
import type {
  AccuracySummary,
  BacktestResponse,
  BufferResponse,
  DailyResponse,
  DecisionView,
  DistributionResponse,
  Health,
  HorizonResponse,
  HoursResponse,
  LevelResponse,
  Meta,
  RevisionsResponse,
  SensitivityResponse,
  WindowParams,
  WorstResponse,
} from "../types/api";

const STALE_MS = 5 * 60_000;

function windowParams(window: WindowParams): QueryParams {
  return { start: window.start, end: window.end, cutoff: window.cutoff };
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getJson<Health>("/api/v1/health", undefined, signal),
    staleTime: 60_000,
    retry: 1,
  });
}

export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: ({ signal }) => getJson<Meta>("/api/v1/meta", undefined, signal),
    staleTime: STALE_MS,
    retry: 1,
  });
}

export function useDecisionView(deliveryDate: string, cutoff: string, includeActuals: boolean) {
  return useQuery({
    queryKey: ["decision", deliveryDate, cutoff, includeActuals],
    queryFn: ({ signal }) =>
      getJson<DecisionView>(
        "/api/v1/decision-view",
        { delivery_date: deliveryDate, cutoff, include_actuals: includeActuals || undefined },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
    enabled: Boolean(deliveryDate),
  });
}

export function useRevisions(deliveryDate: string | null, period: number | null, cutoff: string) {
  return useQuery({
    queryKey: ["revisions", deliveryDate, period, cutoff],
    queryFn: ({ signal }) =>
      getJson<RevisionsResponse>(
        "/api/v1/revisions",
        { delivery_date: deliveryDate, period, cutoff },
        signal,
      ),
    staleTime: STALE_MS,
    enabled: Boolean(deliveryDate && period),
  });
}

export function useAccuracySummary(window: WindowParams) {
  return useQuery({
    queryKey: ["accuracy", "summary", window],
    queryFn: ({ signal }) =>
      getJson<AccuracySummary>("/api/v1/accuracy/summary", windowParams(window), signal),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useDaily(window: WindowParams) {
  return useQuery({
    queryKey: ["accuracy", "daily", window],
    queryFn: ({ signal }) =>
      getJson<DailyResponse>("/api/v1/accuracy/daily", windowParams(window), signal),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useHorizon(window: WindowParams) {
  return useQuery({
    queryKey: ["accuracy", "horizon", window],
    queryFn: ({ signal }) =>
      getJson<HorizonResponse>("/api/v1/accuracy/by-horizon", windowParams(window), signal),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useHours(window: WindowParams) {
  return useQuery({
    queryKey: ["accuracy", "hours", window],
    queryFn: ({ signal }) =>
      getJson<HoursResponse>("/api/v1/accuracy/by-hour", windowParams(window), signal),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useLevels(window: WindowParams, basis: "actual" | "forecast", bins = 5) {
  return useQuery({
    queryKey: ["accuracy", "levels", window, basis, bins],
    queryFn: ({ signal }) =>
      getJson<LevelResponse>(
        "/api/v1/accuracy/by-level",
        { ...windowParams(window), basis, bins },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useDistribution(window: WindowParams, bins = 20) {
  return useQuery({
    queryKey: ["accuracy", "distribution", window, bins],
    queryFn: ({ signal }) =>
      getJson<DistributionResponse>(
        "/api/v1/accuracy/distribution",
        { ...windowParams(window), bins },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useWorst(window: WindowParams, metric: string, n = 5) {
  return useQuery({
    queryKey: ["accuracy", "worst", window, metric, n],
    queryFn: ({ signal }) =>
      getJson<WorstResponse>(
        "/api/v1/accuracy/worst",
        { ...windowParams(window), metric, n },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useSensitivity(window: WindowParams) {
  return useQuery({
    queryKey: ["accuracy", "sensitivity", window],
    queryFn: ({ signal }) =>
      getJson<SensitivityResponse>(
        "/api/v1/accuracy/cutoff-sensitivity",
        { start: window.start, end: window.end },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useBuffer(window: WindowParams, levels = "0.5,0.75,0.9,0.95") {
  return useQuery({
    queryKey: ["risk", "buffer", window, levels],
    queryFn: ({ signal }) =>
      getJson<BufferResponse>("/api/v1/risk/buffer", { ...windowParams(window), levels }, signal),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useBacktest(window: WindowParams, level = 0.9, minHistoryDays = 7) {
  return useQuery({
    queryKey: ["risk", "backtest", window, level, minHistoryDays],
    queryFn: ({ signal }) =>
      getJson<BacktestResponse>(
        "/api/v1/risk/backtest",
        { ...windowParams(window), level, min_history_days: minHistoryDays },
        signal,
      ),
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  });
}

export function useWindowAvailableDates() {
  const meta = useMeta();
  return {
    ...meta,
    dates: meta.data?.available_delivery_dates ?? [],
  };
}

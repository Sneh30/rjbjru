import type { ProblemDocument } from "../types/api";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
const TIMEOUT_MS = 20_000;

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDocument | null;

  constructor(message: string, status = 0, problem: ProblemDocument | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export function apiUrl(path: string, params?: QueryParams): string {
  const normalised = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE}${normalised}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }
  return `${url.pathname}${url.search}`;
}

function isProblemDocument(value: unknown): value is ProblemDocument {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<ProblemDocument>;
  return (
    typeof candidate.type === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.detail === "string" &&
    typeof candidate.status === "number"
  );
}

async function readError(response: Response): Promise<ApiError> {
  const text = await response.text();
  try {
    const payload: unknown = JSON.parse(text);
    if (isProblemDocument(payload)) {
      return new ApiError(payload.detail || payload.title, response.status, payload);
    }
  } catch {
    // Fall through to a plain-text message. The API may be behind a proxy that
    // returned HTML, and the UI must still show something actionable.
  }
  const detail = text.trim().slice(0, 300) || response.statusText || "Request failed";
  return new ApiError(detail, response.status);
}

export async function getJson<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  const forwardAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", forwardAbort, { once: true });
  }
  try {
    const response = await fetch(apiUrl(path, params), {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) throw await readError(response);
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out or was cancelled.", 0);
    }
    throw new ApiError(error instanceof Error ? error.message : "Network request failed", 0);
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener("abort", forwardAbort);
  }
}

export function humaniseProblem(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404 && error.problem?.valid_range) {
      const separator = error.message.endsWith(".") ? " " : ". ";
      return `${error.message}${separator}Available ${error.problem.valid_range.start} to ${error.problem.valid_range.end}.`;
    }
    if (error.status === 422 && error.problem?.errors?.length) {
      return error.problem.errors
        .map((issue) => `${issue.loc.slice(-1).join(".")}: ${issue.msg}`)
        .join("; ");
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

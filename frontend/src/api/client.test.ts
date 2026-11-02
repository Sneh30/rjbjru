import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiUrl, getJson, humaniseProblem } from "../api/client";
import type { ProblemDocument } from "../types/api";

function problem(overrides: Partial<ProblemDocument> = {}): ProblemDocument {
  return {
    type: "about:blank",
    title: "Out of range",
    status: 404,
    detail: "No data for that date.",
    instance: "/api/v1/decision-view",
    ...overrides,
  };
}

describe("apiUrl", () => {
  it("drops empty values and encodes parameters", () => {
    expect(
      apiUrl("/api/v1/decision-view", {
        delivery_date: "2026-02-01",
        cutoff: "09:00",
        include_actuals: true,
        empty: "",
        missing: null,
        undef: undefined,
      }),
    ).toBe(
      "/api/v1/decision-view?delivery_date=2026-02-01&cutoff=09%3A00&include_actuals=true",
    );
  });

  it("accepts paths without a leading slash", () => {
    expect(apiUrl("api/v1/meta")).toBe("/api/v1/meta");
  });
});

describe("getJson", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns parsed JSON and sends an Accept header", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await expect(getJson<{ ok: boolean }>("/api/v1/meta")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledOnce();
    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toEqual({ Accept: "application/json" });
  });

  it("turns an RFC 7807 response into an ApiError with the problem document", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(problem()), { status: 404 }),
    );
    const failure = getJson("/api/v1/decision-view");
    await expect(failure).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "No data for that date.",
      problem: expect.objectContaining({ status: 404 }),
    });
  });

  it("falls back to truncated plain text when the body is not a problem document", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("<html>proxy error</html>", { status: 502 }),
    );
    await expect(getJson("/api/v1/meta")).rejects.toMatchObject({
      status: 502,
      message: "<html>proxy error</html>",
    });
  });

  it("reports network failures as a zero-status ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connection refused"));
    await expect(getJson("/api/v1/meta")).rejects.toMatchObject({
      status: 0,
      message: "connection refused",
    });
  });

  it("aborts when the caller's signal aborts", async () => {
    let received: AbortSignal | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => {
      received = init?.signal ?? undefined;
      return new Promise((_resolve, reject) => {
        received?.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        );
      });
    });
    const controller = new AbortController();
    const request = getJson("/api/v1/meta", undefined, controller.signal);
    controller.abort();
    await expect(request).rejects.toMatchObject({
      status: 0,
      message: "The request timed out or was cancelled.",
    });
    expect(received?.aborted).toBe(true);
  });
});

describe("humaniseProblem", () => {
  it("appends the valid range for a 404", () => {
    const error = new ApiError("No data.", 404, {
      ...problem(),
      valid_range: { start: "2026-01-02", end: "2026-02-01" },
    });
    expect(humaniseProblem(error)).toBe(
      "No data. Available 2026-01-02 to 2026-02-01.",
    );
  });

  it("flattens validation errors for a 422", () => {
    const error = new ApiError("Invalid query.", 422, {
      ...problem({ status: 422 }),
      errors: [
        { loc: ["query", "cutoff"], msg: "must match HH:MM", type: "value_error" },
        { loc: ["query", "delivery_date"], msg: "invalid date", type: "value_error" },
      ],
    });
    expect(humaniseProblem(error)).toBe("cutoff: must match HH:MM; delivery_date: invalid date");
  });

  it("returns plain messages for other errors", () => {
    expect(humaniseProblem(new ApiError("Unavailable", 503))).toBe("Unavailable");
    expect(humaniseProblem(new Error("boom"))).toBe("boom");
    expect(humaniseProblem("not an error")).toBe("Something went wrong.");
  });
});

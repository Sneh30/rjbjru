import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Meta } from "../types/api";
import {
  DEFAULT_CUTOFF,
  DEFAULT_PERIOD,
  deskHref,
  revisionHref,
  useBooleanParam,
  useCutoff,
  useDeliveryDate,
  useLabBasis,
  useRevisionTarget,
  useRiskLevel,
  useWindow,
} from "./urlState";

const meta = {
  available_delivery_dates: ["2026-01-02", "2026-01-03", "2026-02-01"],
  scope: { delivery_dates: { start: "2026-01-02", end: "2026-02-01" } },
} as Meta;

function wrapperFor(initialEntry: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter
        initialEntries={[initialEntry]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        {children}
      </MemoryRouter>
    );
  };
}

function renderUrlHook<T>(hook: () => T, initialEntry = "/") {
  return renderHook(hook, { wrapper: wrapperFor(initialEntry) });
}

describe("useCutoff", () => {
  it("defaults to 09:00 and updates the query string", () => {
    const { result } = renderUrlHook(() => useCutoff());
    expect(result.current[0]).toBe(DEFAULT_CUTOFF);
    act(() => result.current[1]("12:00"));
    expect(result.current[0]).toBe("12:00");
  });

  it("honours a cutoff in the URL", () => {
    const { result } = renderUrlHook(() => useCutoff(), "/desk?cutoff=06%3A00");
    expect(result.current[0]).toBe("06:00");
  });
});

describe("useDeliveryDate", () => {
  it("falls back to the last available delivery date", () => {
    const { result } = renderUrlHook(() => useDeliveryDate(meta));
    expect(result.current.date).toBe("2026-02-01");
    expect(result.current.previous).toBe("2026-01-03");
    expect(result.current.next).toBeNull();
  });

  it("keeps a valid date and exposes its neighbours", () => {
    const { result } = renderUrlHook(() => useDeliveryDate(meta), "/desk?date=2026-01-03");
    expect(result.current.date).toBe("2026-01-03");
    expect(result.current.previous).toBe("2026-01-02");
    expect(result.current.next).toBe("2026-02-01");
    act(() => result.current.setDate("2026-01-02"));
    expect(result.current.date).toBe("2026-01-02");
    expect(result.current.previous).toBeNull();
  });

  it("rejects a date outside the scope and uses the fallback", () => {
    const { result } = renderUrlHook(() => useDeliveryDate(meta), "/desk?date=1999-01-01");
    expect(result.current.date).toBe("2026-02-01");
  });

  it("returns an empty date before metadata loads", () => {
    const { result } = renderUrlHook(() => useDeliveryDate(undefined));
    expect(result.current.date).toBe("");
    expect(result.current.dates).toEqual([]);
  });
});

describe("useRevisionTarget", () => {
  it("defaults the period and reports that it was not explicit", () => {
    const { result } = renderUrlHook(() => useRevisionTarget(meta));
    expect(result.current.period).toBe(DEFAULT_PERIOD);
    expect(result.current.hasPeriod).toBe(false);
  });

  it("reads, clamps and updates the period", () => {
    const { result } = renderUrlHook(
      () => useRevisionTarget(meta),
      "/revisions?period=99&date=2026-01-03",
    );
    expect(result.current.period).toBe(DEFAULT_PERIOD);
    act(() => result.current.setPeriod(0));
    expect(result.current.period).toBe(1);
    expect(result.current.hasPeriod).toBe(true);
    act(() => result.current.setPeriod(30));
    expect(result.current.period).toBe(24);
  });

  it("parses a valid period", () => {
    const { result } = renderUrlHook(() => useRevisionTarget(meta), "/revisions?period=7");
    expect(result.current.period).toBe(7);
    expect(result.current.hasPeriod).toBe(true);
  });
});

describe("useWindow", () => {
  it("defaults to the full delivery-date scope and can be reset", () => {
    const { result } = renderUrlHook(() => useWindow(meta));
    expect(result.current.start).toBe("2026-01-02");
    expect(result.current.end).toBe("2026-02-01");
    expect(result.current.isDefault).toBe(true);
    act(() => result.current.setStart("2026-01-10"));
    expect(result.current.start).toBe("2026-01-10");
    expect(result.current.isDefault).toBe(false);
    act(() => result.current.reset());
    expect(result.current.start).toBe("2026-01-02");
    expect(result.current.isDefault).toBe(true);
  });

  it("honours explicit window parameters", () => {
    const { result } = renderUrlHook(
      () => useWindow(meta),
      "/lab?start=2026-01-05&end=2026-01-20",
    );
    expect(result.current.start).toBe("2026-01-05");
    expect(result.current.end).toBe("2026-01-20");
  });
});

describe("small URL-backed controls", () => {
  it("round-trips a boolean and removes it at the fallback", () => {
    const { result } = renderUrlHook(() => useBooleanParam("hindsight", false));
    expect(result.current[0]).toBe(false);
    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
    act(() => result.current[1](false));
    expect(result.current[0]).toBe(false);
  });

  it("accepts 1 and true for boolean parameters", () => {
    const { result } = renderUrlHook(() => useBooleanParam("hourly", false), "/lab?hourly=1");
    expect(result.current[0]).toBe(true);
  });

  it("validates the risk level against the supported quantiles", () => {
    const { result } = renderUrlHook(() => useRiskLevel(), "/desk?risk=0.75");
    expect(result.current[0]).toBe(0.75);
    act(() => result.current[1](0.95));
    expect(result.current[0]).toBe(0.95);
    const invalid = renderUrlHook(() => useRiskLevel(), "/desk?risk=0.6");
    expect(invalid.result.current[0]).toBe(0.9);
  });

  it("normalises the lab basis", () => {
    const { result } = renderUrlHook(() => useLabBasis(), "/lab?basis=forecast");
    expect(result.current[0]).toBe("forecast");
    act(() => result.current[1]("actual"));
    expect(result.current[0]).toBe("actual");
    const invalid = renderUrlHook(() => useLabBasis(), "/lab?basis=capacity");
    expect(invalid.result.current[0]).toBe("actual");
  });
});

describe("link builders", () => {
  it("encodes dates and cutoffs", () => {
    expect(deskHref("2026-01-02", "09:00")).toBe("/desk?date=2026-01-02&cutoff=09%3A00");
    expect(revisionHref("2026-01-02", 13, "09:00")).toBe(
      "/revisions?date=2026-01-02&period=13&cutoff=09%3A00",
    );
  });
});

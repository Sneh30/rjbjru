import "@testing-library/jest-dom/vitest";
import "vitest-axe/extend-expect";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, expect, vi } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";

import { server } from "./server";

expect.extend(axeMatchers);

let interceptedFetch: typeof fetch | null = null;

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  // jsdom supplies its own AbortSignal while Node supplies fetch. Node's fetch
  // rejects jsdom signals as foreign objects, so tests use the same request
  // path without passing the signal. Cancellation is exercised in the client
  // unit test with a mocked fetch.
  interceptedFetch = globalThis.fetch;
  globalThis.fetch = (input, init) => {
    if (init?.signal) {
      return (
        interceptedFetch?.(input, { ...init, signal: undefined }) ??
        Promise.reject(new Error("fetch unavailable"))
      );
    }
    return interceptedFetch?.(input, init) ?? Promise.reject(new Error("fetch unavailable"));
  };
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  window.history.replaceState(null, "", "/");
});

afterAll(() => {
  if (interceptedFetch) globalThis.fetch = interceptedFetch;
  server.close();
});

// jsdom does not implement the browser APIs Recharts and the app rely on.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }) as unknown as MediaQueryList;
}

class ResizeObserverMock {
  observe() {
    // Recharts needs the observer to exist; the chart container renders at
    // its fallback size in jsdom, which is enough for structural assertions.
  }
  unobserve() {}
  disconnect() {}
}

if (!window.ResizeObserver) {
  window.ResizeObserver = ResizeObserverMock;
}

window.scrollTo = vi.fn();
Element.prototype.scrollIntoView = vi.fn();
Element.prototype.getBoundingClientRect = () =>
  ({
    width: 800,
    height: 400,
    top: 0,
    left: 0,
    right: 800,
    bottom: 400,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  }) as DOMRect;
// axe probes canvas for icon-ligature detection; jsdom has no canvas backend.
HTMLCanvasElement.prototype.getContext = (() => null) as typeof HTMLCanvasElement.prototype.getContext;

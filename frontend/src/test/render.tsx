import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import { expect } from "vitest";

export function renderWithProviders(
  ui: ReactElement,
  { route = "/", withRouter = true }: { route?: string; withRouter?: boolean } = {},
) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Number.POSITIVE_INFINITY,
        gcTime: Number.POSITIVE_INFINITY,
      },
    },
  });
  const tree = withRouter ? (
    <MemoryRouter
      initialEntries={[route]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      {ui}
    </MemoryRouter>
  ) : (
    ui
  );
  return {
    client,
    ...render(<QueryClientProvider client={client}>{tree}</QueryClientProvider>),
  };
}

export async function expectNoA11yViolations(container: HTMLElement) {
  const results = await axe(container, {
    rules: {
      // Page fragments are rendered without the application shell's landmark
      // structure in unit tests; landmarks are covered by the Playwright smoke test.
      region: { enabled: false },
      // jsdom has no layout engine, so contrast cannot be measured here. The
      // Playwright/axe browser pass checks rendered contrast instead.
      "color-contrast": { enabled: false },
    },
  });
  expect(results).toHaveNoViolations();
}

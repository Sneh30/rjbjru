import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../test/server";
import { expectNoA11yViolations, renderWithProviders } from "../test/render";
import { AboutPage } from "./AboutPage";
import { DeskPage } from "./DeskPage";
import { LabPage } from "./LabPage";
import { NotFoundPage } from "./NotFoundPage";
import { RevisionsPage } from "./RevisionsPage";

describe("Decision Desk", () => {
  it("renders the selected day, risk buffer and demand what-if", async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<DeskPage />, {
      route: "/desk?date=2026-02-01&cutoff=09%3A00",
    });

    expect(
      await screen.findByRole("heading", {
        name: "The forecast you actually had, and what it implies",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Decision-time view")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Risk buffer" })).toBeInTheDocument();
    expect(await screen.findByText(/At P90, the historical signed-error buffer/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demand what-if" })).toBeInTheDocument();
    expect(screen.getByText("Mean wind")).toBeInTheDocument();
    expect(screen.getByText("Largest 3 h ramp")).toBeInTheDocument();

    const tables = await screen.findAllByRole("table");
    expect(tables.length).toBeGreaterThanOrEqual(1);
    expect(within(tables[0] as HTMLElement).getAllByRole("row").length).toBeGreaterThan(20);

    await user.type(screen.getByLabelText("Demand what-if (MW)"), "24000");
    expect(await screen.findByText("Residual at forecast")).toBeInTheDocument();
    expect(screen.getByText(/demand 24,000/)).toBeInTheDocument();

    await user.click(screen.getByRole("switch", { name: "Hindsight" }));
    expect(await screen.findByText(/Day MAE/)).toBeInTheDocument();
    expect(screen.getByText(/hindsight on/i)).toBeInTheDocument();

    await expectNoA11yViolations(container);
  });

  it("changes the cutoff through the URL-backed control", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DeskPage />, { route: "/desk?date=2026-02-01" });
    await screen.findByRole("heading", {
      name: "The forecast you actually had, and what it implies",
    });
    const cutoff = screen.getByLabelText("Decision cutoff (D−1)");
    await user.selectOptions(cutoff, "12:00");
    expect(cutoff).toHaveValue("12:00");
    expect((await screen.findAllByText(/12:00 London/)).length).toBeGreaterThan(0);
  });

  it("shows a retryable error when metadata fails", async () => {
    server.use(
      http.get("/api/v1/meta", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Service unavailable",
            status: 503,
            detail: "The snapshot is unavailable.",
            instance: "/api/v1/meta",
          },
          { status: 503 },
        ),
      ),
    );
    const { container } = renderWithProviders(<DeskPage />);
    expect(
      await screen.findByText("The snapshot metadata did not load", {}, { timeout: 4000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    await expectNoA11yViolations(container);
  });
});

describe("Accuracy Lab", () => {
  it("renders the scorecard, every analysis section and the risk panel", async () => {
    const user = userEvent.setup();
    const { container } = renderWithProviders(<LabPage />, {
      route: "/lab?cutoff=09%3A00",
    });

    expect(
      await screen.findByRole("heading", { name: "Where the forecast breaks, and by how much" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Daily accuracy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Error by forecast horizon" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Error by London hour" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Error by wind level" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Distribution and scatter" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Worst days and hours" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cutoff sensitivity" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Risk buffer and calibration" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Walk-forward coverage/)).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Walk-forward coverage against target" })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Level"), "0.95");
    expect(await screen.findByText(/At P95/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "By hour" }));
    expect(screen.getByRole("button", { name: "By hour" })).toHaveAttribute("aria-pressed", "true");
    await user.selectOptions(screen.getByLabelText("Wind-level basis"), "forecast");
    expect(await screen.findByText(/forecast quintiles/)).toBeInTheDocument();

    await expectNoA11yViolations(container);
  });

  it("resets a narrowed window to the full scope", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LabPage />, { route: "/lab?start=2026-01-10&end=2026-01-20" });
    await screen.findByRole("heading", {
      name: "Where the forecast breaks, and by how much",
    });
    const reset = screen.getByRole("button", { name: "Reset to full window" });
    expect(reset).toBeEnabled();
    await user.click(reset);
    await waitFor(() => expect(reset).toBeDisabled());
    expect(screen.getByLabelText("Window start")).toHaveValue("2026-01-02");
    expect(screen.getByLabelText("Window end")).toHaveValue("2026-02-01");
  });
});

describe("Revisions explorer", () => {
  it("shows every vintage, the selected one and the eligibility boundary", async () => {
    const { container } = renderWithProviders(<RevisionsPage />, {
      route: "/revisions?date=2026-02-01&period=13&cutoff=09%3A00",
    });

    expect(
      await screen.findByRole("heading", { name: "Which forecast was actually in hand?" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Every vintage" })).toBeInTheDocument();
    expect(screen.getByText(/vintages were eligible/)).toBeInTheDocument();
    expect(screen.getAllByText("Selected").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No — after cutoff/).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Why this vintage?" })).toBeInTheDocument();
    expect(screen.getAllByRole("table").length).toBeGreaterThanOrEqual(1);

    await expectNoA11yViolations(container);
  });
});

describe("About page", () => {
  it("renders methodology, caveats, provenance and the AI disclosure", async () => {
    const { container } = renderWithProviders(<AboutPage />, { route: "/about" });
    expect(
      await screen.findByRole("heading", { name: "A decision-time desk, not a forecast model" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Known caveats" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "AI disclosure" })).toBeInTheDocument();
    expect(screen.getByText("331dc8acb133704a")).toBeInTheDocument();
    expect(container.textContent).toContain("A publication exactly at the cutoff is eligible");
    expect(container.textContent).toContain("with a two-day lag");
    await expectNoA11yViolations(container);
  });
});

describe("Not found", () => {
  it("names the missing path and offers the real views", async () => {
    const { container } = renderWithProviders(<NotFoundPage />, { route: "/does-not-exist" });
    expect(
      screen.getByRole("heading", { name: "This page is outside the snapshot" }),
    ).toBeInTheDocument();
    expect(screen.getByText("/does-not-exist")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Decision Desk/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Accuracy Lab/ })).toBeInTheDocument();
    await expectNoA11yViolations(container);
  });
});

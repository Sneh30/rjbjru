import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("application shell", () => {
  it("navigates between the four views and opens the methodology dialog", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/desk");
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "The forecast you actually had, and what it implies",
      }),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getAllByRole("link")).toHaveLength(4);
    expect(screen.getByRole("link", { name: /WindLens/i })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Methodology" }));
    expect(screen.getByRole("dialog", { name: "What WindLens measures" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close methodology" }));

    await user.click(within(nav).getByRole("link", { name: /^About/ }));
    expect(
      await screen.findByRole("heading", { name: "A decision-time desk, not a forecast model" }),
    ).toBeInTheDocument();

    await user.click(within(nav).getByRole("link", { name: /^Revisions/ }));
    expect(
      await screen.findByRole("heading", { name: "Which forecast was actually in hand?" }),
    ).toBeInTheDocument();

    await user.click(within(nav).getByRole("link", { name: /^Accuracy Lab/ }));
    expect(
      await screen.findByRole("heading", { name: "Where the forecast breaks, and by how much" }),
    ).toBeInTheDocument();
  });

  it("renders the not-found view for an unknown route", async () => {
    window.history.pushState({}, "", "/unknown-route");
    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "This page is outside the snapshot" }),
    ).toBeInTheDocument();
  });
});

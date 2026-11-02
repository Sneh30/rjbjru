import { expect, test } from "@playwright/test";

test.describe("WindLens smoke", () => {
  test("redirects to the desk and renders the real snapshot", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/desk$/);
    await expect(
      page.getByRole("heading", {
        name: "The forecast you actually had, and what it implies",
      }),
    ).toBeVisible();
    await expect(page.getByText("Decision-time view")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Risk buffer" })).toBeVisible();
    await expect(page.getByText(/At P90, the historical signed-error buffer/)).toBeVisible();
    await expect(page.getByRole("contentinfo")).toContainText("Elexon BMRS FUELHH");
    await expect(page.getByRole("img", { name: /Hourly decision-time wind forecast/ })).toBeVisible();
  });

  test("changes delivery day with the keyboard-accessible controls", async ({ page }) => {
    await page.goto("/desk?date=2026-02-01&cutoff=09%3A00");
    await expect(page.getByRole("heading", { name: /forecast you actually had/i })).toBeVisible();
    await page.getByRole("button", { name: "Previous delivery day" }).click();
    await expect(page).toHaveURL(/date=2026-01-31/);
    await expect(page.locator('input[type="date"]').first()).toHaveValue("2026-01-31");
  });

  test("toggles hindsight and reveals the actual outturn", async ({ page }) => {
    await page.goto("/desk?date=2026-02-01&cutoff=09%3A00");
    await expect(page.getByRole("heading", { name: /forecast you actually had/i })).toBeVisible();
    await expect(page.getByText("hidden", { exact: true })).toBeVisible();
    await page.getByRole("switch", { name: "Hindsight" }).click();
    await expect(page.getByText(/Day MAE/)).toBeVisible();
    await expect(page.getByText("hidden", { exact: true })).not.toBeVisible();
  });

  test("downloads the day CSV", async ({ page }) => {
    await page.goto("/desk?date=2026-02-01&cutoff=09%3A00");
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export day CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("windlens-2026-02-01-0900.csv");
  });

  test("opens the lab, revisions and methodology views", async ({ page }) => {
    await page.goto("/lab?cutoff=09%3A00");
    await expect(
      page.getByRole("heading", { name: "Where the forecast breaks, and by how much" }),
    ).toBeVisible();
    await expect(page.getByText("Walk-forward coverage")).toBeVisible();
    await expect(page.getByRole("meter", { name: "Walk-forward coverage against target" })).toBeVisible();

    await page.getByRole("link", { name: "Revisions" }).click();
    await expect(
      page.getByRole("heading", { name: "Which forecast was actually in hand?" }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Every vintage" })).toBeVisible();

    await page.getByRole("button", { name: "Methodology" }).click();
    await expect(page.getByRole("dialog", { name: "What WindLens measures" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();

    await page.getByRole("link", { name: /^About/ }).click();
    await expect(
      page.getByRole("heading", { name: "A decision-time desk, not a forecast model" }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "AI disclosure" })).toBeVisible();
  });

  test("shows a useful 404", async ({ page }) => {
    await page.goto("/not-a-view");
    await expect(
      page.getByRole("heading", { name: "This page is outside the snapshot" }),
    ).toBeVisible();
    await expect(page.getByText("/not-a-view")).toBeVisible();
    await page.getByRole("link", { name: "Decision Desk", exact: true }).click();
    await expect(page).toHaveURL(/\/desk$/);
  });
});

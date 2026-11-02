import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const AXE_PATH = resolve(process.cwd(), "node_modules/axe-core/axe.min.js");
const AXE_SOURCE = readFileSync(AXE_PATH, "utf8");

async function scan(page: Page) {
  // The deployed document sets a strict script-src CSP. A script element would
  // be blocked, so inject axe through the DevTools evaluation channel. This is
  // a test-only path: the production page never loads axe.
  await page.evaluate(AXE_SOURCE);
  return page.evaluate(async () => {
    return window.axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
      },
    });
  });
}

const PAGES = [
  {
    name: "Decision Desk",
    path: "/desk?date=2026-02-01&cutoff=09%3A00",
    heading: "The forecast you actually had, and what it implies",
  },
  {
    name: "Accuracy Lab",
    path: "/lab?cutoff=09%3A00",
    heading: "Where the forecast breaks, and by how much",
  },
  {
    name: "Revisions explorer",
    path: "/revisions?date=2026-02-01&period=13&cutoff=09%3A00",
    heading: "Which forecast was actually in hand?",
  },
  {
    name: "About",
    path: "/about",
    heading: "A decision-time desk, not a forecast model",
  },
  {
    name: "Not found",
    path: "/not-a-view",
    heading: "This page is outside the snapshot",
  },
];

for (const target of PAGES) {
  test(`${target.name} has no serious or critical axe violations`, async ({ page }) => {
    await page.goto(target.path);
    await expect(page.getByRole("heading", { name: target.heading })).toBeVisible();
    const results = await scan(page);
    const serious = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect
      .soft(
        serious.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          help: violation.help,
          nodes: violation.nodes.map((node) => node.target.join(" ")).slice(0, 5),
        })),
      )
      .toEqual([]);
    expect(results.violations.filter((violation) => violation.impact === "critical")).toEqual([]);
  });
}

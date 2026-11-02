#!/usr/bin/env node
/**
 * Capture the README screenshots from a running WindLens stack.
 *
 * Usage:
 *   docker compose up --build
 *   node scripts/capture_screenshots.mjs
 *
 * Environment:
 *   WINDLENS_BASE_URL  default http://127.0.0.1:8080
 *   WINDLENS_OUT_DIR   default <repo>/docs/img
 *
 * The script uses the Playwright package installed under frontend/. It waits for
 * the page heading and network idle before each shot, so a slow API does not
 * produce a skeleton screenshot.
 */
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "..", "frontend", "package.json"));
const { chromium } = require("playwright");

const base = process.env.WINDLENS_BASE_URL ?? "http://127.0.0.1:8080";
const outDir = process.env.WINDLENS_OUT_DIR ?? path.join(here, "..", "docs", "img");

const shots = [
  {
    name: "desk-hindsight.png",
    url: "/desk?date=2026-01-15&cutoff=09%3A00&hindsight=1&band=1",
    heading: /forecast you actually had/i,
  },
  {
    name: "accuracy-lab.png",
    url: "/lab?cutoff=09%3A00&risk=0.9",
    heading: /where the forecast breaks/i,
  },
  {
    name: "revisions.png",
    url: "/revisions?date=2026-01-15&period=1&cutoff=09%3A00",
    heading: /which forecast was actually in hand/i,
  },
];

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 1100 },
  deviceScaleFactor: 1,
});

try {
  for (const shot of shots) {
    await page.goto(base + shot.url, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: shot.heading }).waitFor();
    await page.waitForTimeout(700);
    const target = path.join(outDir, shot.name);
    await page.screenshot({ path: target });
    console.log(`captured ${target}`);
  }
} finally {
  await browser.close();
}

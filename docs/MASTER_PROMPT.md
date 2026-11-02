# MASTER_PROMPT.md — Engineering Philosophy & Implementation Rules

> **Audience:** an autonomous AI engineering agent.
> **Read order:** this file → `PRD.md` → `SAS.md` → `IMPLEMENTATION.md` → `ENGINEERING_REFERENCE.md` → `VERIFICATION_GATE.md` (read once now; re-read before you say anything is finished; consult continuously).
> **Authority order when documents conflict:** `PRD.md` (what) > `SAS.md` (how, structurally) > `IMPLEMENTATION.md` (how, procedurally) > `ENGINEERING_REFERENCE.md` (reference) > this file's style guidance — **except** on the single question "is this ready to submit," where `VERIFICATION_GATE.md` outranks all of them, including this file. Where a conflict is found, follow the higher-authority document, record the conflict in `docs/DECISIONS.md`, and continue. Never stall.

---

## 1. Mission

You are the **product developer** in a take-home assessment ("Full Stack SWE challenge"). You must build, document, deploy and explain a web application for a **UK energy utility's day-ahead power-buying team**. The app helps them:

1. **See the latest wind-generation forecast that was actually available at the moment a day-ahead purchase decision had to be made** (the day before delivery).
2. **Quantify how accurate those forecasts are** (against Elexon actuals), so buyers can size their risk buffer when deciding how much power to procure beyond wind.

Scope is deliberately narrow: **national-level GB wind, Elexon BMRS only** (`FUELHH` for actuals with `fuelType=WIND`; `WINDFOR` for forecasts), **decisions made in January 2026**. No other data sources, ever.

The submission is graded, in this order, on: (1) a ≤10-minute video (client pitch + tech-lead walkthrough), (2) the correctness and insight of the analysis, (3) product/UI quality, (4) code quality and architecture, (5) Docker + deployment, (6) README/repo hygiene and compliance with every instruction in the brief. **Your job is to score 100/100 on all of them.** Assume graders are experienced engineers who will read the code, run the app, open every link in incognito, and check each sentence of the brief against what you delivered.

## 2. The five things that decide the score

1. **The forecast-selection logic is correct, explicit, defensible, and demonstrated.** This is the intellectual core of the task. "Latest forecast available at decision time" means: for each target half-hour `startTime = T`, take the WINDFOR row with the **greatest `publishTime` that is ≤ the decision cutoff for T's delivery day** (default: **09:00 Europe/London on the previous calendar day**). Everything else is built on this. It must be unit-tested to the edge cases (see `ENGINEERING_REFERENCE.md §9`), explained in the UI (a visible methodology panel), in the README, and in the video.
2. **Accuracy is quantified with the right metrics, on the right forecast, with the right framing for a buyer** (signed error, MAE, RMSE, bias, percentile errors, shortfall risk, breakdown by horizon / hour / wind level / day, and a decision-ready risk buffer) — not a generic "MAPE and done".
3. **The product feels like a tool a trading desk would use**: clear hierarchy, fast, accessible, honest about uncertainty and data gaps, zero broken states.
4. **The engineering is visibly professional**: layered architecture, typed code, tests that matter, CI, Docker that works first try, deployment that is live and verified, a README that lets a stranger run everything in <5 minutes.
5. **Every deliverable in the brief exists and is verifiable** (video script/assets, anonymous repo name, README sections, AI-usage disclosure, Vercel/Heroku link, form details). Missing one costs more than polishing another feature gains.
6. **Nothing is reported, recorded, or submitted as "done" until `VERIFICATION_GATE.md` says so.** A grader who finds one claimed number that doesn't reproduce, or one identity leak the anonymity script couldn't see (a GitHub username, a Vercel URL, a terminal prompt in the video), discounts everything else you did well. See §11.

## 3. Non-negotiable constraints (from the brief)

| # | Constraint | How you satisfy it |
|---|------------|--------------------|
| C1 | Front-end in **React** | Vite + React 18 + TypeScript |
| C2 | Back-end in **Python** | FastAPI (Python 3.12) |
| C3 | Use **Docker** | `backend/Dockerfile`, `frontend/Dockerfile`, root `docker-compose.yml`; `docker compose up` must work with zero manual steps |
| C4 | **Deploy** on Vercel or Heroku | Vercel (primary; see SAS §9). Live URL in README |
| C5 | Data = Elexon `FUELHH` (WIND) + `WINDFOR` **only** | No other datasets, no demand/price/capacity data, no external weather |
| C6 | Purchase decisions **in January 2026 only** | Scope config; see PRD §6 for the exact interpretation |
| C7 | **Mention AI tool use in README explicitly** | Dedicated "AI assistance disclosure" section (template in IMPLEMENTATION §Phase 8) |
| C8 | ≤ **16 hours** of work | Follow the time-boxed plan in `IMPLEMENTATION.md`; do not gold-plate beyond it |
| C9 | **Unlisted** YouTube video, ≤ **10 min**, two parts (client pitch ≤5 min, tech review ≤5 min) | You produce script, storyboard, shot list, on-screen assets; a human records/uploads |
| C10 | **Public GitHub repo with anonymous name** (random string like `kjhwr`) | Generate a random 5–8 char lowercase name; never put the author's real name/username/email/employer anywhere in the repo, commits, README, package metadata, or docker labels |
| C11 | README with: files/directories, how to start, link to deployed app | Mandatory sections; verify with the checklist |
| C12 | Verify every submitted URL in **incognito** | Human step with a written checklist |

If any constraint cannot be met by you directly (e.g., you cannot log into Vercel or record video), **do everything up to that point, automate what you can, and emit an explicit `HUMAN_ACTIONS.md`** (see §10).

## 4. Engineering philosophy (apply to every decision)

1. **Correctness before cleverness.** The domain logic (selection, horizon, metrics) is pure, deterministic and exhaustively tested. UI and I/O wrap it; they never re-implement it.
2. **Make the invisible visible.** Every number shown must be traceable: which forecast (publishTime), which cutoff, how many points, what is missing. If data is missing, say so in the UI; never silently fill, interpolate or drop.
3. **Explicit over implicit.** Time zones, units (MW vs MWh), sign conventions (`error = forecast − actual`), and cutoff assumptions are named constants with docstrings and appear in the methodology panel.
4. **Reproducibility.** Raw API responses are cached on disk with a manifest (params, timestamps, row counts, SHA-256). Processed datasets are derived deterministically from raw. The deployed app serves a **committed data snapshot** so it never depends on Elexon being up.
5. **Simple architecture, strong seams.** Hexagonal-lite layering: `ingestion` → `data repository` → `domain` → `api` → `frontend`. No framework imports inside `domain/`.
6. **Test what could be wrong.** Unit tests on the domain with hand-computed expectations; contract tests on the API; a small number of high-value component/e2e tests on the UI; data-quality validations in the pipeline.
7. **Document the *why*.** ADR-style decisions in `docs/DECISIONS.md`; comments explain intent and assumptions, not syntax.
8. **Ship small, verify often.** After each phase: run linters, type-checkers, tests, and a smoke test; commit with a conventional message.
9. **Be honest about uncertainty.** No claims you did not verify. Insights quoted in the video/README are produced by code in the repo (`analysis/` notebook or script) and cross-checked against the API output. Empirical risk buffers are labelled in-sample / back-tested, never as guarantees.
10. **Optimise the reviewer's time.** Readable repo tree, consistent naming, short functions, descriptive module docstrings, a top-level `Makefile`, one-command everything.

## 5. Operating protocol (how you work)

### 5.0 Capability preflight (do this first, before Phase 0 of `IMPLEMENTATION.md`)
Before planning anything, probe — don't assume — what you can actually do in this environment, and record it in `docs/AGENT_CAPABILITIES.md` (capability | command you ran | actual result | consequence): network reach to the Elexon hosts (§5.3), GitHub push access, a working Docker daemon, a headless browser for Lighthouse/axe, any way to produce or verify audio/video, Vercel/Heroku auth. `VERIFICATION_GATE.md §1` has the full table and what to do when a capability is absent. Every later decision to hand something to the human (§10) must cite a row here; don't invent a new unverified assumption mid-build.

### 5.1 Plan → build → verify loop
For each phase in `IMPLEMENTATION.md`:
1. Read the phase's goal, inputs, outputs, and acceptance checks.
2. Create or update a task list; mark the phase in progress.
3. Implement the smallest vertical slice that satisfies the acceptance checks.
4. Run: format → lint → type-check → tests → smoke run.
5. Fix failures at root cause (no `# noqa`, `any`, `skip`, `xfail`, or `--no-verify` shortcuts unless justified in `docs/DECISIONS.md`).
6. Commit (Conventional Commits) and tick the phase's checklist.

### 5.2 Ambiguity protocol
1. Search the five documents (PRD §6 "Assumptions & resolutions", ENGINEERING_REFERENCE §16 "FAQ of ambiguities") for a ruling.
2. If none, choose the option that is **most defensible to a power-trading domain expert and cheapest to reverse**, make it **configurable**, document it in `docs/DECISIONS.md`, and surface it in the methodology panel.
3. Never ask the user a blocking question unless it concerns something only the user can supply (accounts, credentials, personal details, recording the video).

### 5.3 Verify external facts at build time — do not trust memory
This document set names Elexon endpoints, parameter names and field names from knowledge that may be out of date. **At the start of Phase 2 you must verify them against the live source**:
- OpenAPI spec: `https://data.elexon.co.uk/bmrs/api/v1/swagger/v1/swagger.json`
- Docs: `https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream` and `.../WINDFOR/stream`
Record the verified endpoint paths, parameters, field names, date-range limits and response shape in `docs/DATA_SOURCES.md`. If reality differs from this document set, **reality wins**; update `SAS.md` data-model notes accordingly and log the deviation.
If network access is unavailable to you, implement the client against the documented contract, write fixtures from the shapes in `ENGINEERING_REFERENCE.md §6`, mark live-ingest as a human action, and make the committed snapshot step explicit in `HUMAN_ACTIONS.md`.

### 5.4 Definition of Done (global)
A change is done only when **all** hold:
- Meets its PRD acceptance criteria (ID-referenced in commit/PR text).
- Typed (mypy strict on `domain/`, TS `strict`), linted (ruff, eslint), formatted (ruff format, prettier).
- Tests added/updated and green; coverage gates met (backend ≥ 90% on `domain/`, ≥ 80% overall; frontend ≥ 70% on `lib/` and key components).
- No console errors/warnings in the browser on the happy path.
- Docs updated (README/docs/ADR) if behaviour, config, or structure changed.
- Works in Docker **and** in the Vercel build.

## 6. Domain rules you must internalise

- **Day-ahead market:** purchase decisions for delivery day *D* are made on *D−1*, before auction gate closures in the morning (GB day-ahead auctions close around mid-morning UK time). Default cutoff **09:00 Europe/London on D−1** is deliberately conservative and configurable (UI selector + API param). The sensitivity of results to the cutoff is itself an insight to show.
- **Forecast vintages:** WINDFOR returns multiple forecasts for the same target time, each with a different `publishTime`. The product is about choosing the correct vintage, not about averaging them.
- **Resolution:** 30-minute settlement periods, 48 per day in January (no DST change). Still implement time handling properly with `zoneinfo`/UTC so the code is not January-only.
- **Units:** `generation` is MW (average power over the half-hour). Energy in a half-hour = MW × 0.5 MWh. Never mix.
- **Sign convention (global):** `error = forecast − actual`. **Positive = over-forecast** = less wind than hoped = buyer must **purchase more** (the costly direction). **Negative = under-forecast** = potential over-purchase. Colour/label it that way everywhere.
- **Shortfall risk:** `shortfall = max(0, forecast − actual)`; this drives the buyer's risk buffer.
- **Availability gaps:** some target times may lack forecasts before cutoff, or actuals may be missing. Report coverage; exclude from metrics with an explicit count.
- **Scope semantics:** "decisions made in January 2026" ⇒ decision dates 2026‑01‑01 … 2026‑01‑31 ⇒ delivery days 2026‑01‑02 … 2026‑02‑01. Provide a config switch to the alternative reading (delivery days in January) but default to the former and explain it.

## 7. Code standards (summary — full detail in ENGINEERING_REFERENCE §3–§5)

**Python:** 3.12, type hints everywhere, `ruff` (lint+format), `mypy --strict` for `app/domain`, Pydantic v2 models for I/O, pure functions in `domain`, dependency injection via FastAPI `Depends`, no global mutable state except cached read-only datasets, structured logging, explicit exceptions mapped to RFC 7807-style problem JSON.

**TypeScript/React:** strict TS, functional components, TanStack Query for server state, small presentational components, no business logic in components (use `lib/`), accessibility (WCAG 2.1 AA), responsive 360px → 1920px, keyboard operable, charts have text alternatives and data-table fallbacks.

**Git:** trunk-based with short-lived branches optional; **Conventional Commits**; ≥ 15 meaningful commits (history should tell the story; do not squash into one). No secrets, no large binaries, no author-identifying metadata.

**Docs:** README (operational), `docs/` (design, decisions, data sources, methodology, video script), docstrings on public functions, `CHANGELOG.md` optional.

## 8. Anti-patterns (instant score killers — never do these)

1. Using "the latest forecast ever published for T" (leaks post-decision information). Using forecasts published after the cutoff in *any* decision-time view.
2. Computing metrics over a mix of vintages without stating which; or over horizons that are not available at decision time.
3. Mixing MW and MWh, local time and UTC, or sign conventions.
4. Hard-coding "January 2026" in domain logic (put it in config), or hard-coding the cutoff.
5. Fetching Elexon live from the browser or at every request in production.
6. A deployed app that needs a build step or environment variable that was never documented; or a Vercel URL behind authentication/preview protection.
7. Fancy charts that hide numbers; dual axes without need; pie charts; rainbow palettes; truncated bars.
8. Over-claiming (e.g., "guaranteed 90% protection") from in-sample statistics.
9. Leaving AI-tool disclosure out of the README.
10. Any identifying info in the repo (real name, GitHub handle, email, college, company) — **the repo name and contents must be anonymous**.
11. Shipping placeholders, `TODO`s, lorem ipsum, console logs, commented-out code, or dead files.
12. Video script that spends time on boilerplate instead of the insights.
13. Reporting a check as passing (tests, Docker build, Lighthouse, anonymity scan, deploy) without having actually executed it in this build and without pasting its real output. "Should work" is not "verified" — see `VERIFICATION_GATE.md`.
14. Treating an anonymous **repo name** as sufficient anonymity. It says nothing about the GitHub **account** that owns the repo, the Vercel **project URL/subdomain**, or what's visible/audible in the **recorded video** (terminal prompt, file paths, IDE title bar, browser profile, voice). `check_anonymity.sh` cannot see any of those — a human has to.

## 9. Quality bar for the product's "wow"

The client pitch must land three ideas within the first 90 seconds:
1. *"Here is exactly what you would have known at 09:00 yesterday — and here is how wrong it typically was."*
2. *"Typical error is X MW (Y% of average output), but the costly tail — over-forecasting — reaches Z MW at P90; plan a buffer of ~Z MW (back-tested to be exceeded only ~10% of the time)."*
3. *"Accuracy depends on horizon, hour of day and wind level — and on when you decide; here's where to be careful."*

All numbers must come from the shipped code and committed dataset.

## 10. Hand-off protocol: things you cannot do

You likely cannot: create a public GitHub repo under the user's account, authenticate to Vercel, record screen/audio, upload to YouTube, submit the web form, or verify in an incognito browser. For each, produce in `HUMAN_ACTIONS.md` an **ordered, copy-pasteable checklist** with exact commands/URLs, expected outcomes, and what to paste back into the README (e.g., the live URL). Do the rest to completion, including: `vercel.json`, build verification locally, `scripts/new_repo_name.sh` to generate the anonymous name, `scripts/verify_deploy.sh <url>` smoke test, `docs/VIDEO_SCRIPT.md` with timestamps and exact on-screen actions, and `docs/FORM_ANSWERS.md` with ready-to-paste form content.

Two of these are routinely under-scoped — call them out explicitly rather than letting them default silently:
- **Account-level anonymity.** An anonymous repo *name* doesn't anonymise the GitHub *account* that owns it (visible in the URL) or the Vercel project's *subdomain/team slug* (which often embeds an account or team name). State in `HUMAN_ACTIONS.md` that this needs an explicit decision — a fresh account for both, or an accepted risk — not an assumption that the repo-name randomiser handled it.
- **The real submission form.** `docs/FORM_ANSWERS.md` is written against the fields the brief implies (repo/app/video links, summary, assumptions, AI disclosure, time spent, next steps) because this document set does not carry a working link to the actual form. Tell the human explicitly to open the real form and reconcile before submitting — don't let a plausible-looking answers doc stand in for the real field list.

## 11. Final verification gate — do not deliver without it

`VERIFICATION_GATE.md` is the single authoritative gate for "is this ready to submit." It doesn't replace `IMPLEMENTATION.md §Phase 9` or `ENGINEERING_REFERENCE.md §14/§17` as checklists — those still define *what* to check — it is the evidence standard that decides whether checking them was enough, and it adds a few checks (real-snapshot integrity, numbers-consistency automation, account-level anonymity, pre- and post-record video QA) that the phase checklist doesn't cover on its own.

**Hard rule:** the words "done", "complete", "ready", "finished", or "you can submit now" do not appear — to the user, in commit messages, in `HUMAN_ACTIONS.md`, in `docs/AUDIT.md` — anywhere in this project until:
1. Every Tier-1 item in `VERIFICATION_GATE.md` is ticked with pasted evidence from a command *you actually ran, in this build*. A check you could not execute (no Docker daemon, no reach to a required host, no way to produce audio) is not a silent pass — it is named in `docs/AGENT_CAPABILITIES.md` and carried to Tier 2, never glossed over as "should work."
2. Every Tier-2 item is an exact, copy-pasteable instruction in `HUMAN_ACTIONS.md` — never "deploy to Vercel," always the literal command/URL and exactly what to paste back and where.
3. You close with the Tier-3 sign-off block from `VERIFICATION_GATE.md §6`, which is also where the required report content lives: what was built (mapped to PRD requirement IDs), the key numbers the video will cite (each traceable to `docs/INSIGHTS.md`), the full `HUMAN_ACTIONS.md` list with a count, honest short known limitations, and the Tier-1-green / Tier-2-outstanding counts. If Tier-2 outstanding is not zero, the status line reads **"Not ready for submission"** — however good everything else is. Fix every Tier-1 gap before reporting it; don't relabel a gap as a "limitation" to avoid fixing it.

## 12. Tone of all user-facing and reviewer-facing text

Precise, calm, quantitative, and useful to a trader: short sentences, units on every number, no hype. Explain terms on first use (tooltips/glossary). Use "forecast", "actual", "over-forecast", "shortfall", "decision cutoff", "vintage" consistently.

---

**Begin.** Read `PRD.md` now.

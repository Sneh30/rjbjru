# PRD.md — Product Requirements Document

**Product:** *WindLens — Day-Ahead Wind Forecast Desk* (working name; keep it neutral and non-identifying)
**Version:** 1.0 (pilot)
**Status:** Approved for implementation
**Authoritative for:** *what* must be built and *how success is judged*.

---

## 1. Background and problem

A UK energy utility must buy electricity from the wholesale market to serve its consumers. One team is responsible for buying from the **UK day-ahead market**: decisions for delivery day *D* are made on *D−1*. To decide how much additional power to procure (e.g., from thermal plants), the team must estimate how much of demand will be met by **weather-dependent wind generation**. They rely on wind forecasts published by Elexon (BMRS). Two problems:

1. **"Which forecast did we actually have?"** Many forecasts for the same half-hour are published over time. For a decision, only forecasts published *before the decision cutoff* are usable. The team needs a clear, trustworthy view of the **latest forecast available at decision time**.
2. **"How wrong is it, and in which direction?"** Forecasts are imperfect. Over-forecasting wind is costly (must buy more, later, possibly at worse prices). The team needs **quantified forecast error**, in a form that can be used to size a risk buffer.

## 2. Goals, non-goals, success criteria

### 2.1 Goals
- G1. Show, for any delivery day in scope, the **decision-time forecast** per half-hour with its provenance (publish time, horizon).
- G2. Quantify forecast accuracy against actuals with an appropriate, buyer-relevant metric suite and breakdowns.
- G3. Translate accuracy into a **decision aid**: empirical error bands / risk-adjusted wind.
- G4. Be transparent about methodology, assumptions and data quality.
- G5. Deliver a complete, deployed, documented, well-engineered application plus a convincing two-part video.

### 2.2 Non-goals (explicitly out of scope)
- Any data other than Elexon `FUELHH` (WIND) and `WINDFOR`. **No demand, price, capacity, weather, solar, or other fuel types.**
- Building a new forecasting model, or ML-based forecast correction beyond simple empirical error statistics.
- User accounts, authentication, multi-tenant features, persistence of user data.
- Real-time streaming; the product serves a back-tested January 2026 window from a committed snapshot (the live-refresh capability exists in the ingestion CLI but is not exposed in production).
- Trading execution or price optimisation.

### 2.3 Success criteria (measurable)
| ID | Criterion | Verification |
|----|-----------|--------------|
| S1 | Decision-time forecast logic has zero look-ahead leakage | Unit + property tests; audit script asserts `publish_time ≤ cutoff` for 100% of displayed points |
| S2 | All 31 decision dates (Jan 1–31, 2026) are selectable and render in < 1.5 s (p95, warm) | Playwright/perf check |
| S3 | Accuracy metrics reproduce exactly between API, UI and exported CSV | Contract test comparing API to independent recomputation |
| S4 | App runs by `docker compose up` with no manual steps, and is live on Vercel | Smoke scripts |
| S5 | A reviewer can understand the method in < 2 minutes from the UI alone | Methodology panel + glossary |
| S6 | Video ≤ 10:00, two parts, each with ≤ 5:00 overview, shows all primary features and ≥ 5 quantified insights | Script timing |
| S7 | Lighthouse (desktop): Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95 | Lighthouse CI/manual |
| S8 | The committed `data/processed/*` snapshot originates from a genuine live Elexon pull, never from test fixtures | `manifest.json` fetch timestamps/row counts; `VERIFICATION_GATE.md` Tier-1 item T1 |
| S9 | Every numeric claim in the README "Key findings," `docs/VIDEO_SCRIPT.md`, and `docs/FORM_ANSWERS.md` traces automatically to `docs/INSIGHTS.md` | `scripts/check_numbers_consistency.sh` run against all claims, not a spot check |

## 3. Users and personas

| Persona | Role | Needs | Success looks like |
|---------|------|-------|--------------------|
| **Priya — Day-Ahead Trader** (primary) | Buys power each morning on D−1 | Quick, unambiguous wind forecast for tomorrow; knows how much to trust it; a buffer number | Gets tomorrow's wind profile and a risk-adjusted view in <30 seconds |
| **Marcus — Head of Trading / Risk** | Oversees procurement and risk | Quantified error, bias direction, tail risk, stability over time; sensitivity to decision timing | Can justify buffer policy with numbers |
| **Dana — Analyst** | Builds internal models and reports | Exact definitions, downloadable data, reproducibility | Exports CSV and reproduces numbers |
| **Sam — Tech Lead (reviewer)** | Reviews the work | Clear architecture, tests, code quality, deploy story | Understands & runs everything quickly |

## 4. User stories and epics

IDs are referenced by tests, commits and the traceability matrix in `SAS.md §13`.

### Epic A — Decision-time forecast ("Decision Desk")
- **A1.** As a trader, I choose a *delivery day* and see, for each half-hour, the forecast that was the latest published before the decision cutoff.
- **A2.** As a trader, I see the **publish time (vintage)** and **horizon (hours ahead)** of each forecast point and the overall "latest forecast published at" timestamp.
- **A3.** As a trader, I can change the **decision cutoff** (default 09:00 London on D−1) and immediately see the effect.
- **A4.** As a trader, I see headline KPIs for the day: mean, peak, minimum forecast wind (MW), total forecast energy (MWh), forecast ramp (largest 30-min/3-h change).
- **A5.** As an analyst, I can toggle **Hindsight view** to overlay actuals and errors for that delivery day (hidden by default to emulate decision time).
- **A6.** As a trader, I can view a tabular version and export the day's data to CSV.
- **A7.** As a trader, I can optionally enter an expected demand (flat MW or per-period upload-free simple input) and see the **residual to procure** at the forecast and at a risk-adjusted wind level. *(Clearly labelled what-if; the demand is user-entered, not data.)*

### Epic B — Forecast accuracy ("Accuracy Lab")
- **B1.** As a risk manager, I see a **summary scorecard** for a chosen period and cutoff: n, MAE, RMSE, bias, nMAE (% of mean actual), P50/P90/P95 absolute error, over-forecast share, shortfall P90/P95, correlation, skill vs. persistence baseline.
- **B2.** I see a **time series of daily accuracy** (daily MAE, bias) so I can see stability and bad days.
- **B3.** I see accuracy **by forecast horizon** (how error grows with lead time) using all vintages, and a marker for the horizon band that applies at decision time.
- **B4.** I see accuracy **by hour of day** (London local) at decision time.
- **B5.** I see accuracy **by wind-output level** (e.g., quantile bins of actual or forecast) to expose where the forecasts fail.
- **B6.** I see the **error distribution** (histogram of signed error, with P5/P50/P95 and P90 shortfall marked) and an **actual vs forecast scatter** with the 1:1 line.
- **B7.** I see the **worst N delivery days / half-hours** with links to drill into that day.
- **B8.** I see **cutoff sensitivity**: how MAE/bias/P90 shortfall change for cutoffs such as 06:00, 08:00, 09:00, 09:20, 09:50, 10:00, 12:00 on D−1.
- **B9.** I can export the accuracy tables to CSV.

### Epic C — Decision aid ("Risk Buffer")
- **C1.** As a trader, I see a **risk-adjusted wind forecast** = `max(0, forecast − Q_p(error))` for p ∈ {P50, P75, P90, P95} (Q_p = empirical quantile of historical signed error `forecast − actual`), by hour of day or overall (selectable), and the implied **buffer in MW**.
- **C2.** As a risk manager, I see a **walk-forward back-test** (only past delivery days used to estimate each day's buffer) with **empirical coverage** (share of half-hours where `actual ≥ risk-adjusted forecast`) compared with the target p, so the buffer's reliability is evidenced, not asserted.
- **C3.** The UI states limitations (small sample: 31 days; in-sample vs out-of-sample; seasonality; not financial advice).

### Epic D — Transparency & trust
- **D1.** A **Methodology** panel/page explains: data sources, field mapping, cutoff logic (with a worked example), horizon definition, sign convention, metric formulas, exclusions, and known caveats.
- **D2.** A **Data quality** panel shows coverage: expected vs available points (forecast, actual), duplicates removed, gaps, ingestion timestamp, source versions/hashes.
- **D3.** A **Glossary/tooltips** explain day-ahead, vintage, horizon, MW vs MWh, over-/under-forecast, shortfall.
- **D4.** A **Revisions explorer**: for a chosen target half-hour, show all vintages (publishTime vs forecast MW) with the decision cutoff marked and the actual value — demonstrating the selection visually.

### Epic E — Platform & delivery
- **E1.** Dockerised stack (`docker compose up`).
- **E2.** Public deployment on Vercel (Heroku acceptable fallback).
- **E3.** README with directory guide, run instructions, deployed link, AI disclosure.
- **E4.** CI (lint, type-check, tests, build) on GitHub Actions.
- **E5.** Video script + storyboard; submission checklist.

## 5. Functional requirements (testable)

Priority: **P0** = must ship; **P1** = should ship (planned within the 16h budget); **P2** = nice-to-have if time remains.

### 5.1 Data ingestion & preparation
| ID | Requirement | Pri | Acceptance criteria |
|----|-------------|-----|---------------------|
| FR-D1 | Ingestion CLI fetches `FUELHH` filtered to `fuelType=WIND` and `WINDFOR` for the configured window, chunked by day, with retries/backoff and timeouts | P0 | `python -m app.ingestion.cli fetch` writes raw JSON per chunk + `manifest.json`; reruns are idempotent; failures reported with chunk id |
| FR-D2 | Raw responses are cached on disk (`data/raw/…`) with SHA-256 and request params in manifest | P0 | Manifest lists every chunk, URL, params, row count, hash, fetched-at |
| FR-D3 | Normalisation: parse UTC timestamps, rename to snake_case (`start_time`, `publish_time`, `generation_mw`), enforce dtypes, drop non-WIND rows, de-duplicate on `(start_time, publish_time)` (forecasts) and `start_time` (actuals; keep latest `publish_time`) | P0 | Unit tests on fixtures; duplicates count recorded |
| FR-D4 | Data window: forecasts with `publish_time ∈ [2025‑12‑30T00:00Z, 2026‑02‑02T00:00Z)`; actuals with `start_time ∈ [2026‑01‑01T00:00Z, 2026‑02‑02T00:00Z)`; plus configurable margin | P0 | Config-driven; documented; covers both scope readings |
| FR-D5 | Validation report: expected vs actual counts (48/day), gaps, negative/NaN values, monotonic checks, forecast horizon distribution; fail the pipeline on hard errors, warn on soft | P0 | `data/processed/quality_report.json`; pytest on pipeline |
| FR-D6 | Processed dataset committed to the repo (`data/processed/*.csv.gz` + `manifest.json`) and loaded by the backend at start-up | P0 | App runs offline from the snapshot |
| FR-D7 | The ingest tool can also run with a "latest" window for demonstration, not exposed in production | P2 | CLI flag only |

### 5.2 Domain logic
| ID | Requirement | Pri | Acceptance criteria |
|----|-------------|-----|---------------------|
| FR-L1 | `decision_cutoff(delivery_date, cutoff_local)` returns a tz-aware UTC instant = `(delivery_date − 1 day) at cutoff_local, Europe/London` | P0 | Tests incl. winter/summer dates, DST boundaries |
| FR-L2 | `select_decision_forecasts` returns exactly one forecast per target `start_time` having the **max `publish_time` ≤ cutoff**; none if no eligible vintage | P0 | Tests: boundary equality included; after-cutoff excluded; multiple vintages; missing; ties/duplicates |
| FR-L3 | Horizon = `start_time − publish_time` in hours; stored per point | P0 | Tests |
| FR-L4 | Join with actuals on `start_time`; compute `error_mw = forecast − actual` | P0 | Tests |
| FR-L5 | Metric functions: n, MAE, RMSE, bias, nMAE, WAPE, MAPE (actual ≥ threshold only), P50/P90/P95 of |error|, P5/P50/P95 of signed error, over-forecast share, shortfall mean/P90/P95/max, correlation, skill score vs persistence | P0 (core), P1 (skill) | Tests against hand-computed examples & numpy reference |
| FR-L6 | Horizon analysis across **all vintages** (not only the selected one), bucketed (e.g., 0–6, 6–12, 12–18, 18–24, 24–36, 36–48, 48–72, 72+ h) | P0 | Tests; chart shows decision-time band |
| FR-L7 | Hour-of-day (London local), wind-level (quantile bins, default quintiles of **actual**; option forecast), daily aggregation | P0 | Tests |
| FR-L8 | Cutoff sensitivity: recompute selection+metrics for a list of cutoffs | P0 | Test: monotonic non-leakage; results cached |
| FR-L9 | Risk buffer: empirical quantiles of signed error overall and by hour of day; risk-adjusted forecast = `max(0, f − Q_p)` | P1 | Tests |
| FR-L10 | Walk-forward back-test of the risk buffer with coverage | P1 | Test: day *d* uses only days < *d*; min history configurable (default 7 days; earlier days flagged "insufficient") |
| FR-L11 | Persistence baseline = last actual with `start_time + 30min ≤ cutoff` held flat (documented); skill = 1 − MAE_f / MAE_p | P1 | Tests |

### 5.3 API
| ID | Requirement | Pri | Acceptance criteria |
|----|-------------|-----|---------------------|
| FR-A1 | Versioned REST API under `/api/v1`, OpenAPI at `/api/docs` and `/api/openapi.json` | P0 | Reachable on local, Docker, Vercel |
| FR-A2 | Endpoints listed in `SAS.md §8` with Pydantic response models, input validation (422 with clear messages), 404 for out-of-scope dates | P0 | Contract tests |
| FR-A3 | Deterministic responses (same inputs → same outputs); cache headers (`Cache-Control: public, max-age=300, stale-while-revalidate=3600` for read-only data) | P0 | Tests |
| FR-A4 | CSV export endpoints | P1 | Tests |
| FR-A5 | Health endpoint with dataset fingerprint | P0 | `/api/v1/health` returns status + data hash |
| FR-A6 | CORS limited to configured origins (dev), same-origin in prod | P0 | Config tests |

### 5.4 Front-end
| ID | Requirement | Pri | Acceptance criteria |
|----|-------------|-----|---------------------|
| FR-U1 | Three primary views in a persistent shell: **Decision Desk**, **Accuracy Lab**, **Revisions** (+ Methodology dialog/page). Deep-linkable URLs (`/desk?date=2026-01-15&cutoff=09:00`) | P0 | Router tests; refresh retains state |
| FR-U2 | Decision Desk: date picker (restricted to in-scope days; prev/next), cutoff selector, KPI strip, main chart (forecast line, shaded optional risk band, optional actual in Hindsight mode), vintage strip (publish time per point), data table, CSV export | P0 | Component + e2e tests |
| FR-U3 | Accuracy Lab: period selector (default whole window), cutoff selector, scorecard, daily trend, by-horizon, by-hour, by-level, distribution, scatter, worst days, cutoff-sensitivity | P0 | Component + e2e tests |
| FR-U4 | Revisions explorer: select target half-hour (default: peak-forecast period of the chosen day), chart of vintages with cutoff line and actual | P0 | e2e |
| FR-U5 | Risk buffer module on the Desk and Lab (P50/P75/P90/P95, overall vs hour-of-day, back-test coverage) | P1 | e2e |
| FR-U6 | What-if demand input and residual-to-procure line | P1 | Component tests |
| FR-U7 | Loading skeletons, empty and error states with retry, never blank | P0 | Tests with MSW |
| FR-U8 | Responsive; dark mode (prefers-color-scheme) | P1 | Visual check |
| FR-U9 | Accessibility: semantic landmarks, focus management, labels, contrast ≥ 4.5:1, chart text alternatives, keyboard navigation | P0 | axe tests, manual checklist |
| FR-U10 | Tooltips/glossary for domain terms; units on all numbers; consistent number formatting (thousands separators, 0 dp for MW, 1 dp for %) | P0 | Visual review |
| FR-U11 | Persistent, visible provenance footer: "Data: Elexon BMRS FUELHH & WINDFOR · snapshot ingested <ts> · hash <short>" | P0 | Test |

### 5.5 Platform & deliverables
| ID | Requirement | Pri | Acceptance criteria |
|----|-------------|-----|---------------------|
| FR-P1 | `docker compose up --build` serves UI at `http://localhost:8080` and API at `http://localhost:8000` | P0 | Smoke script |
| FR-P2 | `vercel.json` + `api/index.py` deploy both UI and API in one Vercel project; public, no auth/protection | P0 | `scripts/verify_deploy.sh` passes |
| FR-P3 | README sections: overview, live link, directory guide, quick start (Docker + local), config, data pipeline, testing, deployment, methodology summary, AI disclosure, limitations | P0 | Checklist |
| FR-P4 | CI workflow: backend lint/type/test, frontend lint/type/test/build, Docker build | P0 | Green badge |
| FR-P5 | Anonymous repo name; no identifying metadata | P0 | `scripts/check_anonymity.sh` |
| FR-P6 | `docs/VIDEO_SCRIPT.md`, `docs/FORM_ANSWERS.md`, `HUMAN_ACTIONS.md` | P0 | Present, complete |
| FR-P7 | `docs/AGENT_CAPABILITIES.md` capability preflight exists; every item handed to `HUMAN_ACTIONS.md` cites a row in it | P0 | `VERIFICATION_GATE.md §1` |
| FR-P8 | `scripts/check_no_placeholders.sh` and `scripts/check_numbers_consistency.sh` exist and are run before any "ready" claim | P0 | `VERIFICATION_GATE.md §2` |
| FR-P9 | Account/URL-level anonymity (GitHub account, Vercel subdomain/team slug) explicitly decided and recorded, not left to the repo-name randomiser alone | P0 | `HUMAN_ACTIONS.md` H2/H5 |
| FR-P10 | Post-record video QA performed against `docs/VIDEO_SCRIPT.md`'s insight list and the rubric's content areas, not just length and incognito playback | P0 | `HUMAN_ACTIONS.md` H7 |

## 6. Assumptions and resolutions (rulings for ambiguities)

| # | Ambiguity | Resolution | Why / How to change |
|---|-----------|------------|---------------------|
| R1 | "Decisions made in January 2026" | **Decision dates = 2026‑01‑01…2026‑01‑31**, so delivery days = 2026‑01‑02…2026‑02‑01. Config `SCOPE_MODE=decision_date` (default) or `delivery_date` (delivery days 2026‑01‑01…2026‑01‑31) | The brief says decisions, not deliveries. Ingestion window covers both |
| R2 | Decision time | **09:00 Europe/London on D−1** (configurable; UI selector; sensitivity analysis). Rationale: day-ahead auction gate closures occur in the morning UK time (around 09:20–09:50 for the main GB auctions), so 09:00 is a safe, slightly conservative cut. State this as an assumption, not a fact about the client | The client's real cutoff is unknown → expose it |
| R3 | "Latest forecast available" | Max `publish_time ≤ cutoff` per `start_time` | Core logic |
| R4 | Time zone | Source timestamps are UTC; London local for delivery-day boundaries and hour-of-day; January = GMT (UTC+0) but code is DST-safe | Correctness |
| R5 | Delivery day boundary | London local midnight-to-midnight (48 periods in Jan) | Align with market day |
| R6 | Error sign | `forecast − actual`; positive = over-forecast = shortfall risk | Buyer-centric |
| R7 | Normalised error | nMAE = MAE / mean(actual) over the evaluated set (no installed-capacity data permitted) | Constraint C5 |
| R8 | MAPE | Reported only for `actual ≥ 500 MW` (config), flagged as unstable otherwise | Avoid division blow-ups |
| R9 | Persistence baseline | Last actual available at cutoff held constant | Uses only allowed data |
| R10 | Missing actuals/forecasts | Excluded from metrics, counted, displayed | Honesty |
| R11 | Actuals revisions | If FUELHH returns multiple publishTimes for a `start_time`, keep latest | Final outturn |
| R12 | Horizon scope for horizon chart | All vintages whose `start_time` ∈ evaluation window | Shows error growth; decision-time band overlaid |
| R13 | Risk buffer estimation | Empirical quantiles on 31 days (in-sample) **plus** walk-forward back-test for validation | Rigor without over-claiming |
| R14 | What-if demand | User-entered flat MW (default none) | No external data allowed |
| R15 | Elexon wind scope | FUELHH WIND is the national outturn series; WINDFOR is the national wind forecast; verify scope definitions at build time and note any difference (e.g., transmission-metered vs total) in Methodology | Do not assert unverified facts |

## 7. Data requirements and dictionary (summary; full in ENGINEERING_REFERENCE §6)

**Actuals (`FUELHH`, `fuelType=WIND`):** `startTime` (UTC, 30-min), `generation` (MW), plus `publishTime`, `settlementDate`, `settlementPeriod`, `fuelType`.
**Forecasts (`WINDFOR`):** `startTime`, `publishTime`, `generation` (MW).
**Processed:**
- `actuals`: `start_time` (UTC), `generation_mw`.
- `forecasts`: `start_time` (UTC), `publish_time` (UTC), `generation_mw`.

## 8. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Performance | API p95 < 300 ms warm for any endpoint (excluding cold start); cold start < 4 s on Vercel; initial page JS ≤ 250 KB gzip (route-split charts); LCP < 2.5 s |
| Reliability | App functions with no outbound network; graceful degradation with clear error UI |
| Security | No secrets; input validation; CORS minimal; dependency pinning; no PII; security headers (CSP, X-Content-Type-Options, Referrer-Policy) via `vercel.json`/nginx |
| Privacy/anonymity | No identifying information in repo/metadata; neutral product name |
| Accessibility | WCAG 2.1 AA |
| Maintainability | Layered architecture; ≥ 90% coverage on domain; ADRs; Conventional Commits |
| Portability | Same code runs locally, in Docker, on Vercel |
| Observability | Structured logs with request IDs; `/health`; data fingerprint |
| Usability | Time to first insight < 30 s for a new user; consistent terminology; contextual help |
| Browser support | Latest 2 versions of Chrome, Edge, Firefox, Safari; mobile ≥ 360 px |
| Internationalisation | English (UK), dates `DD MMM YYYY`, 24h time, London local with UTC shown in tooltips |

## 9. UX requirements

- **Information hierarchy on the Decision Desk:** (1) the date/cutoff controls and a banner "Using forecasts published up to **14 Jan 2026 09:00 GMT**; latest vintage in use: **08:00**", (2) KPI strip, (3) main chart, (4) vintage strip + table.
- **Colour semantics:** forecast = blue; actual = dark neutral/black; over-forecast (shortfall risk) = warm red/orange; under-forecast = teal; risk band = translucent amber. Colour-blind-safe palette; never colour alone (use line styles/labels).
- **Charts:** time on X in London local (UTC in tooltip), MW on Y with zero baseline for bars, units in axis titles, direct labels, accessible tooltips, data-table toggle, downloadable CSV. Avoid dual axes unless essential (horizon vs error uses single axis).
- **Copy:** concise, trader-friendly; explain "so-what" under each chart as dynamic insight text (e.g., "Error grows from 6.1% at 0–6 h to 14.8% at 36–48 h" computed from data, not hard-coded).
- **States:** skeleton loaders, empty states ("No forecast was published before this cutoff for 3 periods"), error with retry, offline.
- **Navigation:** top tabs; cutoff and period are global (URL-synced); keyboard shortcuts optional (←/→ to change day).

## 10. Analysis requirements (what the product must reveal)

The analysis module must produce, and the video must cite, **at least these quantified insights** (computed, not hard-coded):
1. Overall decision-time MAE, RMSE, bias (MW) and nMAE (% of mean actual) for the window.
2. Error growth with horizon (e.g., MAE by horizon bucket) and the horizon range implied by the cutoff (~15–39 h).
3. Over-forecast vs under-forecast frequency and magnitude; P90/P95 **shortfall** in MW.
4. Hour-of-day pattern (when is the forecast worst/best?).
5. Dependence on wind level (e.g., largest absolute errors at mid-to-high output).
6. Worst delivery days and what they look like (large ramps, storms/low-wind lulls).
7. Cutoff sensitivity (does deciding earlier/later matter, how much?).
8. Value of the latest vintage vs earlier vintages and vs persistence (skill).
9. Risk-buffer calibration (back-test coverage vs target).
10. Data coverage statistics.

## 11. Deliverables and acceptance

| Deliverable | Acceptance |
|-------------|-----------|
| Deployed app (Vercel) | Public, incognito-verified, all views load, no console errors |
| Public GitHub repo (anonymous name) | README complete, CI green, history meaningful, anonymity check passes |
| Video (unlisted YouTube) | ≤10:00, Part 1 (client) ≤5:00 with impactful insights; Part 2 (tech) ≤5:00 covering architecture, design, analysis, code base, practices; audio clear; link verified in incognito |
| Submission form | All URLs verified; `docs/FORM_ANSWERS.md` filled |
| AI disclosure | README section naming the tools used and how |

## 12. Release criteria (go/no-go)

All P0 requirements pass; ≥ 80% of P1 pass; zero known S1/S2 defects; CI green; Docker compose smoke passes from a clean clone; Vercel verification passes in incognito; anonymity check passes (repo text **and** account/URL/video per FR-P9); video script rehearsed to ≤ 9:30; and `VERIFICATION_GATE.md` Tier 1 is 100% green with pasted evidence, with Tier 2 fully and exactly itemised in `HUMAN_ACTIONS.md`.

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Elexon API shape/params differ from documentation here | Ingestion fails | Verify against OpenAPI first (MASTER_PROMPT §5.3); fixtures; adapter layer |
| Elexon stream range limits / rate limits | Partial data | Day-chunking, backoff, resume from manifest |
| WINDFOR has gaps (no vintage before cutoff for some periods) | Missing points | Coverage reporting; excluded and counted; never filled |
| Vercel bundle size/cold start with pandas | Deployment failure | Pin slim deps; precomputed lookups; fallback to NumPy-only implementation (documented in SAS §9) |
| Misinterpretation of "decision time" | Wrong analysis | Configurable cutoff, sensitivity analysis, explicit assumption in UI/video |
| Over-claiming from 31 days of data | Credibility loss | Back-test, caveats, wording rules |
| Video exceeds 10 min | Penalty | Timed script with 30 s slack |
| Identity leakage | Disqualification risk | `check_anonymity.sh`, neutral names |
| Time overrun | Incomplete | Phase time-boxes with P0/P1/P2 triage |

## 14. Traceability to evaluation rubric (inferred)

| Likely rubric area | Weight (inferred) | PRD coverage |
|--------------------|-------------------|--------------|
| Video quality & clarity | 30 | §10, §11, FR-P6 |
| Analysis correctness & insight | 25 | FR-L1…L11, §10 |
| UI/UX & product thinking | 15 | FR-U1…U11, §9 |
| Code quality & architecture | 10 | NFR, SAS |
| Docker/deployment | 10 | FR-P1/P2/P4 |
| README/repo/compliance | 10 | FR-P3/P5, §11 |

## 15. Open questions (non-blocking; defaults chosen)

- Exact client cutoff time → default 09:00; configurable.
- Whether the client wants MWh rather than MW → both shown (MWh = MW × 0.5 per period).
- Whether Heroku preferred over Vercel → Vercel used; Docker image deployable to Heroku Container Registry (instructions in ENGINEERING_REFERENCE §12).

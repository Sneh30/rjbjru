# Architecture decision records

Each record states the context, the decision, the reason, the alternatives that
were considered, and the consequence that a reviewer should expect to live with.
Records 001–012 are the initial set from `docs/SAS.md` §14, expanded with what
was actually built. Records 013–016 record decisions that only became clear
after probing the live source or testing the interface.

Status values: **Accepted** (implemented), **Superseded** (replaced by a later
record), **Proposed** (not built in this evaluation).

---

## ADR-001 — Default cutoff is 09:00 Europe/London on D−1

**Status:** Accepted.

**Context.** A day-ahead buyer needs one reproducible instant at which the
forecast set is frozen. The brief does not name the client's gate closure. GB
day-ahead auction gates and internal trading desks close at different times, and
a forecast published after the gate cannot be used.

**Decision.** Resolve the cutoff as 09:00 Europe/London on the calendar day
before the London delivery day, convert it to UTC, and select the latest WINDFOR
vintage whose `publish_time` is less than or equal to that instant. The boundary
is inclusive. The cutoff is configurable through the API and the UI, with a
sensitivity grid at 06:00, 08:00, 09:00, 09:20, 09:50, 10:00 and 12:00.

**Reason.** It is conservative relative to common day-ahead gates and leaves the
buyer time to act. In January it maps to the 07:30 UTC WINDFOR publication, which
is a regular vintage rather than an ad hoc one.

**Alternatives.** 09:20/09:50/12:00 (kept in sensitivity), a fixed UTC cutoff
(rejected because market days are London days), a user-supplied instant (more
flexible but harder to explain and compare).

**Consequence.** The default MAE is 2,038.9 MW. The 12:00 cutoff is 6.76% lower
at 1,901.0 MW but cuts mean horizon from 28.0 h to 24.1 h. The product shows both
and does not claim that later is universally better.

---

## ADR-002 — Scope is decision dates in January 2026

**Status:** Accepted.

**Context.** "Decisions made in January" can mean decisions taken in January or
deliveries in January. The two readings produce different windows and different
row counts.

**Decision.** Read the brief literally: decision dates 2026-01-01 to 2026-01-31,
which deliver 2026-01-02 to 2026-02-01. Implement the alternative as
`SCOPE_MODE=delivery_date` rather than hard-coding one interpretation.

**Reason.** The literal reading is the one the brief supports, and the
configuration flag lets a reviewer test the other without rewriting the domain.

**Alternatives.** Delivery-date reading, a rolling 31-day window (rejected as
not matching the brief).

**Consequence.** The committed analysis has 31 London delivery days and 744
hourly targets. Switching scope mode changes the evaluated window and therefore
every headline number; the mode is recorded in metadata.

---

## ADR-003 — Error is forecast minus actual

**Status:** Accepted.

**Context.** A signed error can be written in either direction. For a buyer, the
dangerous case is forecasting more wind than arrives, because the resulting
energy position is short.

**Decision.** `error = forecast − actual`. Positive error is over-forecast and
shortfall risk. The risk-adjusted plan is `max(0, forecast − buffer)`.

**Reason.** It makes the sign of the headline bias directly readable as the
buyer's problem. A positive buffer is subtracted from generation.

**Alternatives.** `actual − forecast` (mathematically equivalent but makes the
buyer translate the sign on every screen).

**Consequence.** 85.0% of hours have positive error. The UI labels positive error
as "shortfall" and uses the rust colour for it; negative error uses teal.

---

## ADR-004 — Serve a committed snapshot; ingest offline

**Status:** Accepted.

**Context.** Elexon is an external dependency with rate limits and occasional
schema changes. The evaluation needs reproducible numbers and a demo that works
even if the upstream feed is slow.

**Decision.** `make ingest` fetches day-sized chunks, normalises and validates
them, and writes a fingerprinted snapshot under `data/processed/`. The API reads
only that snapshot at request time. Ingestion is resumable and reuses raw chunks.

**Reason.** Reproducibility, predictable latency, and no request-time network
failure mode. It also makes the provenance auditable: every processed file has a
manifest hash and a fetch timestamp.

**Alternatives.** Live Elexon calls per request (slow, rate-limited, impossible to
reproduce), a database populated by a background job (more moving parts for a
one-month dataset).

**Consequence.** Refreshing the data is an explicit command. The snapshot is
versioned by fingerprint, and ETags change when it changes. The demo cannot show
"today's" data without a re-ingest, which is the correct trade-off for this
evaluation.

---

## ADR-005 — FastAPI with pandas and NumPy, no database

**Status:** Accepted.

**Context.** The dataset is 1,536 half-hour actuals and 19,856 forecast rows.
The heavy operation is a vectorised groupby over a few thousand rows.

**Decision.** Use FastAPI for the HTTP layer, pandas/NumPy for the analytics,
and no database. Load and validate the snapshot once per process.

**Reason.** The data fits comfortably in memory; SQL adds schema migration and
connection management without buying performance. Type-checked Python with
Pydantic gives a clean contract.

**Alternatives.** SQLite/DuckDB (useful for larger data, unnecessary here),
Postgres (operationally heavier), pure NumPy (possible, but pandas makes the
join and time handling clearer).

**Consequence.** A single process can serve the whole evaluation. The snapshot is
read-only, so there are no write conflicts. Wide-format ingestion would need a
different choice; the current ingestion is deliberately narrow.

---

## ADR-006 — One repository, one Vercel project

**Status:** Accepted.

**Context.** The deliverable needs a React SPA and a Python API. They can be
deployed separately or as one project.

**Decision.** Keep one repository and one Vercel project. Vercel builds the SPA
from `frontend/`, rewrites `/api/*` to the Python function in `api/index.py`, and
rewrites other routes to `index.html`.

**Reason.** Fewer URLs to leak identity, fewer CORS configurations, and one
deployment link for the submission.

**Alternatives.** Separate frontend and backend projects (cleaner scaling, more
moving parts and more identity surface), static SPA plus a separate API host.

**Consequence.** The Python function bundle includes pandas, NumPy and the
snapshot. Bundle size and cold start are the main hosted risks; ADR-007 covers
the fallback. Docker Compose remains the local reference runtime.

---

## ADR-007 — Measure the serverless path; do not pre-optimise

**Status:** Accepted, with the fallback not triggered in local testing.

**Context.** A Vercel Python function that bundles pandas, NumPy and the snapshot
may exceed practical bundle or cold-start limits. The brief asks for deployment,
not for a rewrite before measuring.

**Decision.** Ship the straightforward FastAPI function and measure it. If the
hosted bundle is too large or cold start exceeds the operational budget, apply
the documented fallback: precompute selections for the cutoff grid into compact
JSON, or replace pandas in the request path with NumPy-only arrays. The UI keeps
the continuous cutoff for grid values.

**Reason.** Premature optimisation would complicate the code before there is
evidence that the simple version fails. The fallback is designed and documented
so it is a measured response, not an emergency rewrite.

**Alternatives.** Always precompute (fast but freezes the API surface), always
NumPy-only (lower bundle risk but more custom code).

**Consequence.** The hosted deployment is a human action and its measurements
must be recorded when it happens. Local Docker is the reference runtime. This
record does not claim a hosted cold-start number that was never observed.

---

## ADR-008 — Recharts for charts

**Status:** Accepted.

**Context.** The UI needs line, bar, scatter and histogram charts with
accessible alternatives and a small dependency footprint.

**Decision.** Use Recharts 2.15 with a shared `ChartFrame` wrapper. Chart
internals are `aria-hidden`; each frame exposes a heading, a summary and a
table alternative.

**Reason.** It covers every chart used, is familiar to reviewers, and can be
wrapped so accessibility is owned by the frame rather than by each chart.

**Alternatives.** ECharts (more features, heavier), visx (more control, more
code), Plotly (large bundle and a different interaction model).

**Consequence.** Every chart has a table equivalent and a text summary. The
wrapper, not the chart library, is the accessibility contract. A future chart
library change does not change the wrapper's API.

---

## ADR-009 — Generate TypeScript types from OpenAPI

**Status:** Accepted.

**Context.** Hand-written frontend types drift from the API. The API already
publishes an OpenAPI schema.

**Decision.** Generate `frontend/src/types/openapi.d.ts` with
`openapi-typescript@7.5.0` via `make types`. CI regenerates it and fails on a
diff. A small hand-written `src/types/api.ts` remains the UI's readable source of
truth for component props.

**Reason.** Schema drift becomes a build failure instead of a runtime surprise.
The generated file is intentionally not edited by hand.

**Alternatives.** Hand-written types only (simple, drifts), a full code generator
for clients (more machinery than this app needs).

**Consequence.** Adding or changing an API field requires regenerating the
contract. The generated file is committed so the frontend builds without running
Python. `make types` needs the backend virtualenv and is part of CI.

---

## ADR-010 — Walk-forward buffer with a two-day outcome lag

**Status:** Accepted.

**Context.** An empirical quantile of the same errors used to evaluate coverage
is in-sample by construction. Using yesterday's actuals to size today's buffer
leaks outcomes that were not fully known at the 09:00 cutoff.

**Decision.** For delivery day `d`, estimate the risk buffer from delivery days
on or before `d − 2`, require at least seven usable history days, and evaluate
the buffer against day `d`. Report pooled hourly coverage, mean daily buffer and
the share of evaluated days with a breach.

**Reason.** It is a leakage-safe test that a buyer could actually have run, and
the two-day lag reflects publication and settlement delay.

**Alternatives.** In-sample quantile (optimistic), one-day lag (still leaks in
practice), a parametric distribution (not justified by 31 days of data).

**Consequence.** At level 0.90 the walk-forward coverage is 86.0% over 23 days,
not the nominal 90.0%. The gap is reported as the honest cost of the rule. Eight
days at the start of the window are skipped for insufficient history.

---

## ADR-011 — nMAE uses mean actual output

**Status:** Accepted.

**Context.** Capacity-normalised error would be easier to compare across markets,
but installed wind capacity is outside the two permitted datasets.

**Decision.** Define `nMAE = MAE / mean(actual) × 100`. Do not import or infer
capacity. Report nMAE alongside MAE and WAPE.

**Reason.** It is scale-free within this dataset and uses only permitted inputs.

**Alternatives.** Installed capacity (not permitted), forecast mean as the
denominator (misleading when the forecast is biased).

**Consequence.** nMAE is 18.07% in this window. It is not directly comparable to
a capacity-normalised metric from another system, and the methodology says so.

---

## ADR-012 — Commit processed data; raw responses are optional

**Status:** Accepted.

**Context.** A reviewer should be able to run the app without a network pull. The
raw responses are large and contain redundant JSON.

**Decision.** Commit `data/processed/` (two gzipped CSVs, manifest and quality
report). Keep `data/raw/` out of git; the ingestion command can rebuild it. The
processed manifest records the source URLs, per-chunk hashes and fetch times.

**Reason.** The app is reproducible offline, while the repository stays small and
does not duplicate the raw feed. The manifest preserves provenance without the
raw payloads.

**Alternatives.** Commit raw responses too (larger, mostly redundant), commit
nothing and fetch at build time (network-dependent, breaks reproducibility).

**Consequence.** `make verify-snapshot` re-hashes the processed files. The
`data/raw/` cache is local only. Small raw samples under `backend/tests/fixtures/`
are test inputs and are never the source of a product number.

---

## ADR-013 — Follow the live hourly WINDFOR resolution

**Status:** Accepted.

**Context.** The brief's example language implied half-hourly wind forecasts, but
the live WINDFOR feed returns 73 hourly targets per vintage. Assuming a
half-hourly feed would have produced empty joins or an invented resample.

**Decision.** Evaluate hourly. Each hourly actual is the arithmetic mean of the
two FUELHH half-hours starting at the top of the hour and at half past. If either
half-hour is missing, the hour is null and excluded. Never interpolate and never
invent intra-hour forecasts.

**Reason.** Reality wins over the example. The evaluation must compare series at
the resolution at which the forecast was published.

**Alternatives.** Resample WINDFOR to half-hours (invents information), resample
FUELHH by picking one half-hour (arbitrary and noisier), evaluate only full
half-hour pairs where WINDFOR happens to align (not possible).

**Consequence.** The scored unit is the hour: 744 targets, each the mean of two
settlement periods. Intra-hour variability is invisible to headline metrics, and
the limitation is stated in `docs/METHODOLOGY.md` and in the UI.

---

## ADR-014 — Compare WINDFOR with FUELHH directly, without rescaling

**Status:** Accepted.

**Context.** The direct comparison produces a large positive bias (+1,747.9 MW),
and a reviewer may reasonably ask whether the two series measure the same wind
portfolio. Timestamp shifts were tested and did not explain the level difference.
The brief permits only these two datasets.

**Decision.** Score the published WINDFOR value against the FUELHH-derived hourly
actual, retain the bias, and report it as measured shortfall risk. Do not fit a
bias correction, rescale to installed capacity, or substitute a different wind
series.

**Reason.** The buyer would have used the published number; the product should
score the number the buyer had. A calibration would hide the very risk the tool
exists to expose and would exceed the data policy.

**Alternatives.** Subtract the mean bias (makes the forecast look better but
invalidates the decision-time story), normalise both series by an external
capacity (not permitted), discard the comparison (loses the product's central
finding).

**Consequence.** The product is honest about a large level bias rather than
presenting a flattering calibrated variant. A future iteration should investigate
portfolio coverage and capacity normalisation if the client permits more data.

---

## ADR-015 — Expose honest hourly ramp metrics and nullable open buckets

**Status:** Accepted.

**Context.** The brief's schema mentioned a half-hour ramp. The live forecast is
hourly, so a true half-hour ramp cannot be computed from WINDFOR. The 72+ horizon
bucket is open-ended and has no numeric upper bound.

**Decision.** Expose `max_ramp_1h_mw` and `max_ramp_3h_mw` instead of an
impossible half-hour ramp. Serialise the open-ended horizon bucket with
`to_h = null`. Decision API responses hide actuals and hindsight fields by
default (`include_actuals=false`); a caller must opt in.

**Reason.** Field names should mean what they say. A fabricated half-hour ramp
would be a correctness bug, and a sentinel such as 999 would be a silent lie.
Opt-in hindsight keeps the decision-time view honest by default.

**Alternatives.** Resample to half-hours (invented), keep the spec name and
document it loosely (misleading), use a large numeric sentinel for 72+ (ambiguous
and easy to chart incorrectly).

**Consequence.** The API differs from the brief's example field name, and the
difference is documented in the OpenAPI description, the UI and this record.
Consumers must handle `null` for the open bucket.

---

## ADR-016 — URL-synced, accessible frontend state

**Status:** Accepted.

**Context.** A reviewer needs to share or bookmark a decision view. Keyboard and
screen-reader users need equivalent access to chart information. Server facts and
user-entered scenarios have different lifetimes.

**Decision.** Put delivery date, cutoff, lab window, basis, risk level and
hindsight in the URL. Keep the demand what-if in local component state. Wrap
every chart in `ChartFrame` with a heading, description and table alternative;
mark chart internals `aria-hidden`; make scrollable table regions focusable; run
`vitest-axe` in unit tests and axe in the production browser suite.

**Reason.** URL state makes a view reproducible and linkable. Chart/table parity
is the only reliable way to make a canvas/SVG chart accessible without pretending
the graphic itself is a table. Local state is correct for a scenario that is not
a server fact.

**Alternatives.** All state in local React state (not shareable), all state in the
URL including demand (pollutes links with a user scenario), charts without
alternatives (fails accessibility), axe only in unit tests (does not exercise the
production CSP or the real rendered bundle).

**Consequence.** Changing a control rewrites the URL. The browser suite injects
axe through `page.evaluate` because the production CSP correctly blocks inline
script tags. Unit-level axe excludes jsdom-only colour-contrast inference; the
browser suite is the authority for rendered contrast.

---

## Decision log summary

| ADR | Topic | Status |
|---|---|---|
| 001 | 09:00 London D−1 cutoff | Accepted |
| 002 | January decision-date scope | Accepted |
| 003 | Forecast minus actual sign | Accepted |
| 004 | Snapshot serving, offline ingestion | Accepted |
| 005 | FastAPI + pandas, no database | Accepted |
| 006 | One repo, one Vercel project | Accepted |
| 007 | Measure serverless path; documented fallback | Accepted |
| 008 | Recharts with accessible frame | Accepted |
| 009 | OpenAPI-generated TypeScript | Accepted |
| 010 | Walk-forward buffer, two-day lag | Accepted |
| 011 | nMAE on mean actual | Accepted |
| 012 | Processed data committed, raw optional | Accepted |
| 013 | Hourly WINDFOR resolution | Accepted |
| 014 | Direct comparison, no rescaling | Accepted |
| 015 | Hourly ramp fields and nullable open bucket | Accepted |
| 016 | URL state and chart/table accessibility | Accepted |

No record in this file authorises a deployment, a public push, a video upload or
a submission. Those remain human actions in `HUMAN_ACTIONS.md`.
